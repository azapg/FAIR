"""Add registration admission and AI weighted-credit controls.

Revision ID: 20260823_0035
Revises: 20260812_0034
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import sqlalchemy as sa
from alembic import op


revision: str = "20260823_0035"
down_revision: str = "20260812_0034"
branch_labels = None
depends_on = None


def _normalize_email(value: str) -> str:
    address = value.strip()
    local, separator, domain = address.rpartition("@")
    if not separator or not local or not domain:
        raise ValueError("invalid email address")
    return f"{local.casefold()}@{domain.encode('idna').decode('ascii').casefold()}"


def _preflight_user_emails(connection) -> list[tuple[Any, str]]:
    users = sa.table(
        "users",
        sa.column("id", sa.UUID()),
        sa.column("email", sa.String()),
    )
    normalized_rows: list[tuple[Any, str]] = []
    invalid: list[str] = []
    collisions: defaultdict[str, list[str]] = defaultdict(list)
    for row in connection.execute(sa.select(users.c.id, users.c.email)).mappings():
        try:
            normalized = _normalize_email(str(row["email"]))
        except (ValueError, UnicodeError):
            invalid.append(str(row["id"]))
            continue
        normalized_rows.append((row["id"], normalized))
        collisions[normalized].append(str(row["id"]))

    duplicate_groups = {email: ids for email, ids in collisions.items() if len(ids) > 1}
    if invalid or duplicate_groups:
        problems = []
        if invalid:
            preview = ", ".join(invalid[:10])
            problems.append(f"invalid email rows: {preview}")
        if duplicate_groups:
            preview = "; ".join(
                f"{email}: {', '.join(ids)}"
                for email, ids in list(duplicate_groups.items())[:10]
            )
            problems.append(f"normalized email collisions: {preview}")
        raise RuntimeError(
            "Cannot enable canonical user identities. Resolve "
            + " | ".join(problems)
            + " and rerun the migration; FAIR will not merge or delete accounts automatically."
        )
    return normalized_rows


def upgrade() -> None:
    connection = op.get_bind()
    normalized_rows = _preflight_user_emails(connection)

    op.add_column("users", sa.Column("normalized_email", sa.String(320), nullable=True))
    users = sa.table(
        "users",
        sa.column("id", sa.UUID()),
        sa.column("normalized_email", sa.String(320)),
    )
    for user_id, normalized in normalized_rows:
        connection.execute(
            users.update()
            .where(users.c.id == user_id)
            .values(normalized_email=normalized)
        )
    with op.batch_alter_table("users") as batch:
        batch.alter_column(
            "normalized_email",
            existing_type=sa.String(320),
            nullable=False,
        )
        batch.create_unique_constraint(
            "uq_users_normalized_email", ["normalized_email"]
        )

    op.create_table(
        "platform_policies",
        sa.Column("id", sa.SmallInteger(), nullable=False),
        sa.Column(
            "admission_mode", sa.String(32), nullable=False, server_default="open"
        ),
        sa.Column(
            "ai_controls_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_by_user_id", sa.UUID(), nullable=True),
        sa.CheckConstraint("id = 1", name="ck_platform_policy_singleton"),
        sa.CheckConstraint(
            "admission_mode IN ('open', 'allowlist', 'invite_only')",
            name="ck_platform_policy_admission_mode",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "admission_rules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("normalized_value", sa.String(320), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "kind IN ('email', 'domain')", name="ck_admission_rule_kind"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kind", "normalized_value", name="uq_admission_rule_value"),
    )
    op.create_index(
        "ix_admission_rules_kind_value",
        "admission_rules",
        ["kind", "normalized_value"],
    )
    op.create_table(
        "registration_invites",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("normalized_email", sa.String(320), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("redeemed_by_user_id", sa.UUID(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["redeemed_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_registration_invites_token_hash"),
    )
    op.create_index(
        "ix_registration_invites_email",
        "registration_invites",
        ["normalized_email", "expires_at"],
    )
    op.create_table(
        "ai_capability_policies",
        sa.Column("capability_definition_id", sa.UUID(), nullable=False),
        sa.Column("classification", sa.String(16), nullable=False),
        sa.Column("cost_units", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_by_user_id", sa.UUID(), nullable=False),
        sa.CheckConstraint("cost_units >= 0", name="ck_ai_capability_cost_nonnegative"),
        sa.CheckConstraint(
            "(classification = 'unmetered' AND cost_units = 0) OR "
            "(classification = 'ai' AND cost_units > 0)",
            name="ck_ai_capability_classification_cost",
        ),
        sa.CheckConstraint(
            "classification IN ('unmetered', 'ai')",
            name="ck_ai_capability_classification",
        ),
        sa.ForeignKeyConstraint(
            ["capability_definition_id"],
            ["capability_definitions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("capability_definition_id"),
    )
    op.create_table(
        "ai_entitlements",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False, server_default="disabled"),
        sa.Column("monthly_limit_units", sa.Integer(), nullable=True),
        sa.Column("used_units", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_by_user_id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "used_units >= 0", name="ck_ai_entitlement_used_nonnegative"
        ),
        sa.CheckConstraint(
            "monthly_limit_units IS NULL OR monthly_limit_units > 0",
            name="ck_ai_entitlement_limit_positive",
        ),
        sa.CheckConstraint(
            "(state = 'limited' AND monthly_limit_units IS NOT NULL) OR "
            "(state != 'limited' AND monthly_limit_units IS NULL)",
            name="ck_ai_entitlement_state_limit",
        ),
        sa.CheckConstraint(
            "state IN ('disabled', 'limited', 'unlimited')",
            name="ck_ai_entitlement_state",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "ai_usage_charges",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("execution_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("capability_definition_id", sa.UUID(), nullable=False),
        sa.Column("units", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("units > 0", name="ck_ai_usage_charge_units_positive"),
        sa.ForeignKeyConstraint(
            ["capability_definition_id"],
            ["capability_definitions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["execution_id"], ["executions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("execution_id", name="uq_ai_usage_charges_execution_id"),
    )
    op.create_index(
        "ix_ai_usage_user_period",
        "ai_usage_charges",
        ["user_id", "period_start", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_usage_user_period", table_name="ai_usage_charges")
    op.drop_table("ai_usage_charges")
    op.drop_table("ai_entitlements")
    op.drop_table("ai_capability_policies")
    op.drop_index("ix_registration_invites_email", table_name="registration_invites")
    op.drop_table("registration_invites")
    op.drop_index("ix_admission_rules_kind_value", table_name="admission_rules")
    op.drop_table("admission_rules")
    op.drop_table("platform_policies")
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("uq_users_normalized_email", type_="unique")
        batch.drop_column("normalized_email")
