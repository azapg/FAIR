"""Add normalized LMS foundation primitives.

Revision ID: 20260812_0029
Revises: 20260727_0028
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260812_0029"
down_revision: str = "20260727_0028"
branch_labels = None
depends_on = None


def _json_document() -> sa.JSON:
    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def _create_activity_event_guards() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            sa.text(
                """
                CREATE FUNCTION fair_reject_activity_event_mutation()
                RETURNS trigger AS $$ BEGIN
                  RAISE EXCEPTION 'ActivityEvent % is append-only', OLD.id;
                END; $$ LANGUAGE plpgsql;
                """
            )
        )
        op.execute(
            sa.text(
                """
                CREATE TRIGGER fair_activity_event_append_only
                BEFORE UPDATE OR DELETE ON activity_events
                FOR EACH ROW EXECUTE FUNCTION fair_reject_activity_event_mutation()
                """
            )
        )
    else:
        op.execute(
            sa.text(
                "CREATE TRIGGER fair_activity_event_append_only_update "
                "BEFORE UPDATE ON activity_events BEGIN SELECT RAISE(ABORT, "
                "'ActivityEvent is append-only'); END"
            )
        )
        op.execute(
            sa.text(
                "CREATE TRIGGER fair_activity_event_append_only_delete "
                "BEFORE DELETE ON activity_events BEGIN SELECT RAISE(ABORT, "
                "'ActivityEvent is append-only'); END"
            )
        )


def _drop_activity_event_guards() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            sa.text("DROP TRIGGER fair_activity_event_append_only ON activity_events")
        )
        op.execute(sa.text("DROP FUNCTION fair_reject_activity_event_mutation()"))
    else:
        op.execute(sa.text("DROP TRIGGER fair_activity_event_append_only_delete"))
        op.execute(sa.text("DROP TRIGGER fair_activity_event_append_only_update"))


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("attributes", _json_document(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    with op.batch_alter_table("courses") as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.UUID(), nullable=True))
        batch_op.create_foreign_key(
            "fk_courses_organization_id_organizations",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_unique_constraint(
            "uq_courses_id_organization", ["id", "organization_id"]
        )

    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "role IN ('owner', 'admin', 'member')",
            name="ck_organization_memberships_role",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive')",
            name="ck_organization_memberships_status",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "user_id",
            name="uq_organization_memberships_organization_user",
        ),
    )
    op.create_index(
        "ix_organization_memberships_user_status",
        "organization_memberships",
        ["user_id", "status"],
    )

    op.create_table(
        "cohorts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "name", name="uq_cohorts_organization_name"
        ),
        sa.UniqueConstraint("id", "organization_id", name="uq_cohorts_id_organization"),
    )

    op.create_table(
        "course_sections",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("copied_from_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "position >= 0", name="ck_course_sections_position_non_negative"
        ),
        sa.CheckConstraint(
            "visibility IN ('draft', 'published', 'hidden')",
            name="ck_course_sections_visibility",
        ),
        sa.ForeignKeyConstraint(
            ["copied_from_id"], ["course_sections.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "course_id", "position", name="uq_course_sections_course_position"
        ),
        sa.UniqueConstraint("id", "course_id", name="uq_course_sections_id_course"),
    )
    op.create_index(
        "ix_course_sections_course_visibility",
        "course_sections",
        ["course_id", "visibility"],
    )

    op.create_table(
        "course_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("section_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=True),
        sa.Column("resource_id", sa.UUID(), nullable=True),
        sa.Column("copied_from_id", sa.UUID(), nullable=True),
        sa.Column("payload_schema_uri", sa.String(length=2048), nullable=True),
        sa.Column("payload", _json_document(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "position >= 0", name="ck_course_items_position_non_negative"
        ),
        sa.CheckConstraint(
            "(resource_type IS NULL AND resource_id IS NULL) OR "
            "(resource_type IS NOT NULL AND resource_id IS NOT NULL)",
            name="ck_course_items_resource_pair",
        ),
        sa.CheckConstraint(
            "visibility IN ('draft', 'published', 'hidden')",
            name="ck_course_items_visibility",
        ),
        sa.ForeignKeyConstraint(
            ["copied_from_id"], ["course_items.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["section_id", "course_id"],
            ["course_sections.id", "course_sections.course_id"],
            name="fk_course_items_section_course",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "section_id", "position", name="uq_course_items_section_position"
        ),
        sa.UniqueConstraint("id", "course_id", name="uq_course_items_id_course"),
        sa.UniqueConstraint(
            "course_id",
            "resource_type",
            "resource_id",
            name="uq_course_items_course_resource",
        ),
    )
    op.create_index(
        "ix_course_items_course_kind", "course_items", ["course_id", "kind"]
    )
    op.create_index(
        "ix_course_items_resource",
        "course_items",
        ["resource_type", "resource_id"],
    )

    op.create_table(
        "completion_rules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("course_item_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("rule_type", sa.String(length=64), nullable=False),
        sa.Column("config", _json_document(), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "position >= 0", name="ck_completion_rules_position_non_negative"
        ),
        sa.ForeignKeyConstraint(
            ["course_item_id", "course_id"],
            ["course_items.id", "course_items.course_id"],
            name="fk_completion_rules_item_course",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "course_item_id", "position", name="uq_completion_rules_item_position"
        ),
    )
    op.create_index(
        "ix_completion_rules_course_type",
        "completion_rules",
        ["course_id", "rule_type"],
    )

    op.create_table(
        "availability_rules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("course_item_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("rule_type", sa.String(length=64), nullable=False),
        sa.Column("config", _json_document(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "position >= 0", name="ck_availability_rules_position_non_negative"
        ),
        sa.ForeignKeyConstraint(
            ["course_item_id", "course_id"],
            ["course_items.id", "course_items.course_id"],
            name="fk_availability_rules_item_course",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "course_item_id", "position", name="uq_availability_rules_item_position"
        ),
    )
    op.create_index(
        "ix_availability_rules_course_type",
        "availability_rules",
        ["course_id", "rule_type"],
    )

    op.create_table(
        "user_item_completions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("course_item_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=True),
        sa.Column("source_id", sa.UUID(), nullable=True),
        sa.Column("evidence", _json_document(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(source_type IS NULL AND source_id IS NULL) OR "
            "(source_type IS NOT NULL AND source_id IS NOT NULL)",
            name="ck_user_item_completions_source_pair",
        ),
        sa.CheckConstraint(
            "(status = 'completed' AND completed_at IS NOT NULL) OR "
            "(status != 'completed' AND completed_at IS NULL)",
            name="ck_user_item_completions_timestamp",
        ),
        sa.CheckConstraint(
            "status IN ('not_started', 'in_progress', 'completed')",
            name="ck_user_item_completions_status",
        ),
        sa.ForeignKeyConstraint(
            ["course_item_id", "course_id"],
            ["course_items.id", "course_items.course_id"],
            name="fk_user_item_completions_item_course",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id", "course_id"],
            ["enrollments.user_id", "enrollments.course_id"],
            name="fk_user_item_completions_enrollment",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "course_item_id",
            "user_id",
            name="uq_user_item_completions_item_user",
        ),
    )
    op.create_index(
        "ix_user_item_completions_course_status",
        "user_item_completions",
        ["course_id", "status"],
    )
    op.create_index(
        "ix_user_item_completions_course_user",
        "user_item_completions",
        ["course_id", "user_id"],
    )

    op.create_table(
        "grade_categories",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("parent_category_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("aggregation_strategy", sa.String(length=32), nullable=False),
        sa.Column("weight", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("calculation_policy", _json_document(), nullable=False),
        sa.Column("copied_from_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "aggregation_strategy IN "
            "('sum', 'weighted_mean', 'simple_mean', 'highest')",
            name="ck_grade_categories_aggregation_strategy",
        ),
        sa.CheckConstraint(
            "position >= 0", name="ck_grade_categories_position_non_negative"
        ),
        sa.CheckConstraint(
            "weight IS NULL OR weight >= 0", name="ck_grade_categories_weight"
        ),
        sa.ForeignKeyConstraint(
            ["copied_from_id"], ["grade_categories.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["parent_category_id", "course_id"],
            ["grade_categories.id", "grade_categories.course_id"],
            name="fk_grade_categories_parent_course",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "course_id", "position", name="uq_grade_categories_course_position"
        ),
        sa.UniqueConstraint("id", "course_id", name="uq_grade_categories_id_course"),
    )
    op.create_index(
        "ix_grade_categories_course_parent",
        "grade_categories",
        ["course_id", "parent_category_id"],
    )

    op.create_table(
        "grade_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("category_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("max_points", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("weight", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("calculation_policy", _json_document(), nullable=False),
        sa.Column("release_policy", _json_document(), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=True),
        sa.Column("source_id", sa.UUID(), nullable=True),
        sa.Column("copied_from_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("max_points > 0", name="ck_grade_items_max_points_positive"),
        sa.CheckConstraint(
            "position >= 0", name="ck_grade_items_position_non_negative"
        ),
        sa.CheckConstraint(
            "(source_type IS NULL AND source_id IS NULL) OR "
            "(source_type IS NOT NULL AND source_id IS NOT NULL)",
            name="ck_grade_items_source_pair",
        ),
        sa.CheckConstraint(
            "weight IS NULL OR weight >= 0", name="ck_grade_items_weight"
        ),
        sa.ForeignKeyConstraint(
            ["category_id", "course_id"],
            ["grade_categories.id", "grade_categories.course_id"],
            name="fk_grade_items_category_course",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["copied_from_id"], ["grade_items.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "course_id", "position", name="uq_grade_items_course_position"
        ),
        sa.UniqueConstraint("id", "course_id", name="uq_grade_items_id_course"),
        sa.UniqueConstraint(
            "course_id",
            "source_type",
            "source_id",
            name="uq_grade_items_course_source",
        ),
    )
    op.create_index(
        "ix_grade_items_course_category",
        "grade_items",
        ["course_id", "category_id"],
    )
    op.create_index(
        "ix_grade_items_source", "grade_items", ["source_type", "source_id"]
    )

    op.create_table(
        "grade_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("grade_item_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("points_earned", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("release_state", sa.String(length=32), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=True),
        sa.Column("source_id", sa.UUID(), nullable=True),
        sa.Column("source_version", sa.String(length=128), nullable=True),
        sa.Column("recorded_by_user_id", sa.UUID(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "points_earned IS NULL OR points_earned >= 0",
            name="ck_grade_entries_points_non_negative",
        ),
        sa.CheckConstraint(
            "release_state IN ('unreleased', 'released')",
            name="ck_grade_entries_release_state",
        ),
        sa.CheckConstraint(
            "(release_state = 'unreleased' AND released_at IS NULL) OR "
            "(release_state = 'released' AND released_at IS NOT NULL)",
            name="ck_grade_entries_release_timestamp",
        ),
        sa.CheckConstraint(
            "(source_type IS NULL AND source_id IS NULL) OR "
            "(source_type IS NOT NULL AND source_id IS NOT NULL)",
            name="ck_grade_entries_source_pair",
        ),
        sa.CheckConstraint(
            "(status = 'graded' AND points_earned IS NOT NULL) OR "
            "(status IN ('missing', 'excused') AND points_earned IS NULL)",
            name="ck_grade_entries_status_points",
        ),
        sa.ForeignKeyConstraint(
            ["grade_item_id", "course_id"],
            ["grade_items.id", "grade_items.course_id"],
            name="fk_grade_entries_item_course",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["user_id", "course_id"],
            ["enrollments.user_id", "enrollments.course_id"],
            name="fk_grade_entries_enrollment",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "grade_item_id", "user_id", name="uq_grade_entries_item_user"
        ),
    )
    op.create_index(
        "ix_grade_entries_course_user",
        "grade_entries",
        ["course_id", "user_id"],
    )
    op.create_index(
        "ix_grade_entries_release",
        "grade_entries",
        ["course_id", "release_state"],
    )
    op.create_index(
        "ix_grade_entries_source", "grade_entries", ["source_type", "source_id"]
    )

    op.create_table(
        "course_groups",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_id", "name", name="uq_course_groups_course_name"),
        sa.UniqueConstraint("id", "course_id", name="uq_course_groups_id_course"),
    )

    op.create_table(
        "course_group_memberships",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("group_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "role IN ('member', 'leader')",
            name="ck_course_group_memberships_role",
        ),
        sa.ForeignKeyConstraint(
            ["group_id", "course_id"],
            ["course_groups.id", "course_groups.course_id"],
            name="fk_course_group_memberships_group_course",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id", "course_id"],
            ["enrollments.user_id", "enrollments.course_id"],
            name="fk_course_group_memberships_enrollment",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "group_id", "user_id", name="uq_course_group_memberships_group_user"
        ),
    )
    op.create_index(
        "ix_course_group_memberships_course_user",
        "course_group_memberships",
        ["course_id", "user_id"],
    )

    op.create_table(
        "cohort_memberships",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("cohort_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'inactive')",
            name="ck_cohort_memberships_status",
        ),
        sa.ForeignKeyConstraint(
            ["cohort_id", "organization_id"],
            ["cohorts.id", "cohorts.organization_id"],
            name="fk_cohort_memberships_cohort_organization",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "user_id"],
            [
                "organization_memberships.organization_id",
                "organization_memberships.user_id",
            ],
            name="fk_cohort_memberships_organization_user",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "cohort_id", "user_id", name="uq_cohort_memberships_cohort_user"
        ),
    )
    op.create_index(
        "ix_cohort_memberships_user_status",
        "cohort_memberships",
        ["user_id", "status"],
    )

    op.create_table(
        "external_identifiers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("system", sa.String(length=128), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("course_id", sa.UUID(), nullable=True),
        sa.Column("cohort_id", sa.UUID(), nullable=True),
        sa.Column("attributes", _json_document(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(subject_type = 'user' AND user_id IS NOT NULL "
            "AND course_id IS NULL AND cohort_id IS NULL) OR "
            "(subject_type = 'course' AND course_id IS NOT NULL "
            "AND user_id IS NULL AND cohort_id IS NULL) OR "
            "(subject_type = 'cohort' AND cohort_id IS NOT NULL "
            "AND user_id IS NULL AND course_id IS NULL)",
            name="ck_external_identifiers_subject",
        ),
        sa.ForeignKeyConstraint(
            ["cohort_id", "organization_id"],
            ["cohorts.id", "cohorts.organization_id"],
            name="fk_external_identifiers_cohort_organization",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["course_id", "organization_id"],
            ["courses.id", "courses.organization_id"],
            name="fk_external_identifiers_course_organization",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "user_id"],
            [
                "organization_memberships.organization_id",
                "organization_memberships.user_id",
            ],
            name="fk_external_identifiers_organization_user",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "system",
            "cohort_id",
            name="uq_external_identifiers_cohort",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "system",
            "course_id",
            name="uq_external_identifiers_course",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "system",
            "subject_type",
            "external_id",
            name="uq_external_identifiers_external",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "system",
            "user_id",
            name="uq_external_identifiers_user",
        ),
    )
    op.create_index(
        "ix_external_identifiers_lookup",
        "external_identifiers",
        ["system", "external_id"],
    )

    op.create_table(
        "calendar_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=True),
        sa.Column("owner_user_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("all_day", sa.Boolean(), nullable=False),
        sa.Column("timezone_name", sa.String(length=128), nullable=True),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=True),
        sa.Column("source_id", sa.UUID(), nullable=True),
        sa.Column("copied_from_id", sa.UUID(), nullable=True),
        sa.Column("recurrence", _json_document(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "visibility != 'course' OR course_id IS NOT NULL",
            name="ck_calendar_events_course_visibility_scope",
        ),
        sa.CheckConstraint(
            "(source_type IS NULL AND source_id IS NULL) OR "
            "(source_type IS NOT NULL AND source_id IS NOT NULL)",
            name="ck_calendar_events_source_pair",
        ),
        sa.CheckConstraint(
            "ends_at IS NULL OR ends_at > starts_at",
            name="ck_calendar_events_time_order",
        ),
        sa.CheckConstraint(
            "visibility IN ('private', 'course')",
            name="ck_calendar_events_visibility",
        ),
        sa.ForeignKeyConstraint(
            ["copied_from_id"], ["calendar_events.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_calendar_events_course_start",
        "calendar_events",
        ["course_id", "starts_at"],
    )
    op.create_index(
        "ix_calendar_events_owner_start",
        "calendar_events",
        ["owner_user_id", "starts_at"],
    )
    op.create_index(
        "ix_calendar_events_source",
        "calendar_events",
        ["source_type", "source_id"],
    )

    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("delivery_mode", sa.String(length=32), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=True),
        sa.Column("source_id", sa.UUID(), nullable=True),
        sa.Column("config", _json_document(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "channel IN ('web', 'email', 'push')",
            name="ck_notification_preferences_channel",
        ),
        sa.CheckConstraint(
            "delivery_mode IN ('immediate', 'digest', 'off')",
            name="ck_notification_preferences_delivery_mode",
        ),
        sa.CheckConstraint(
            "(source_type IS NULL AND source_id IS NULL) OR "
            "(source_type IS NOT NULL AND source_id IS NOT NULL)",
            name="ck_notification_preferences_source_pair",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "channel",
            "event_type",
            name="uq_notification_preferences_user_channel_event",
        ),
    )
    op.create_index(
        "ix_notification_preferences_source",
        "notification_preferences",
        ["source_type", "source_id"],
    )
    op.create_index(
        "ix_notification_preferences_user_mode",
        "notification_preferences",
        ["user_id", "delivery_mode"],
    )

    op.create_table(
        "activity_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("schema_uri", sa.String(length=2048), nullable=True),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column("course_id", sa.UUID(), nullable=True),
        sa.Column("organization_id", sa.UUID(), nullable=True),
        sa.Column("object_type", sa.String(length=64), nullable=True),
        sa.Column("object_id", sa.UUID(), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=True),
        sa.Column("source_id", sa.UUID(), nullable=True),
        sa.Column("payload", _json_document(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(object_type IS NULL AND object_id IS NULL) OR "
            "(object_type IS NOT NULL AND object_id IS NOT NULL)",
            name="ck_activity_events_object_pair",
        ),
        sa.CheckConstraint(
            "(source_type IS NULL AND source_id IS NULL) OR "
            "(source_type IS NOT NULL AND source_id IS NOT NULL)",
            name="ck_activity_events_source_pair",
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_activity_events_actor_occurred",
        "activity_events",
        ["actor_user_id", "occurred_at"],
    )
    op.create_index(
        "ix_activity_events_course_occurred",
        "activity_events",
        ["course_id", "occurred_at"],
    )
    op.create_index(
        "ix_activity_events_object",
        "activity_events",
        ["object_type", "object_id"],
    )
    op.create_index(
        "ix_activity_events_organization_occurred",
        "activity_events",
        ["organization_id", "occurred_at"],
    )
    op.create_index(
        "ix_activity_events_source",
        "activity_events",
        ["source_type", "source_id"],
    )
    _create_activity_event_guards()


def downgrade() -> None:
    _drop_activity_event_guards()
    op.drop_table("activity_events")
    op.drop_table("notification_preferences")
    op.drop_table("calendar_events")
    op.drop_table("external_identifiers")
    op.drop_table("cohort_memberships")
    op.drop_table("course_group_memberships")
    op.drop_table("course_groups")
    op.drop_table("grade_entries")
    op.drop_table("grade_items")
    op.drop_table("grade_categories")
    op.drop_table("user_item_completions")
    op.drop_table("availability_rules")
    op.drop_table("completion_rules")
    op.drop_table("course_items")
    op.drop_table("course_sections")
    op.drop_table("cohorts")
    op.drop_table("organization_memberships")
    with op.batch_alter_table("courses") as batch_op:
        batch_op.drop_constraint("uq_courses_id_organization", type_="unique")
        batch_op.drop_constraint(
            "fk_courses_organization_id_organizations", type_="foreignkey"
        )
        batch_op.drop_column("organization_id")
    op.drop_table("organizations")
