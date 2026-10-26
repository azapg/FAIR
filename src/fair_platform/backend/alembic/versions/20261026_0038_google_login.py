"""Add external login identities and short-lived OIDC transactions."""

import sqlalchemy as sa
from alembic import op

revision = "20261026_0038"
down_revision = "20261025_0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "external_identities",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("connection_key", sa.String(128), nullable=False),
        sa.Column("issuer", sa.String(512), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("issuer", "subject", name="uq_external_identity_subject"),
        sa.UniqueConstraint(
            "user_id", "connection_key", name="uq_external_identity_user_connection"
        ),
    )
    op.create_index(
        "ix_external_identities_user_id", "external_identities", ["user_id"]
    )
    op.create_table(
        "oidc_transactions",
        sa.Column("state_hash", sa.String(64), primary_key=True),
        sa.Column("browser_hash", sa.String(64), nullable=False),
        sa.Column("connection_key", sa.String(128), nullable=False),
        sa.Column("purpose", sa.String(16), nullable=False),
        sa.Column("nonce", sa.String(128), nullable=False),
        sa.Column("code_verifier", sa.String(128), nullable=False),
        sa.Column("remember_me", sa.Boolean(), nullable=False),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("invite_hash", sa.String(64)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "purpose IN ('login', 'link')", name="ck_oidc_transaction_purpose"
        ),
        sa.CheckConstraint(
            "(purpose = 'login' AND user_id IS NULL) OR (purpose = 'link' AND user_id IS NOT NULL)",
            name="ck_oidc_transaction_user",
        ),
    )
    op.create_index(
        "ix_oidc_transactions_expires_at", "oidc_transactions", ["expires_at"]
    )


def downgrade() -> None:
    op.drop_table("oidc_transactions")
    op.drop_table("external_identities")
