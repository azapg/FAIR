"""Add submitters table and auth system redesign

Revision ID: 20251101_0003
Revises: 20250823_0002
Create Date: 2025-11-01
"""

from __future__ import annotations

from alembic import op  # type: ignore
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251101_0003"
down_revision = "20250823_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Apply auth system redesign changes:
    1. Add password_hash to users table
    2. Create submitters table
    3. Add created_by_id to submissions table
    4. Update submissions.submitter_id FK to point to submitters
    
    Note: This is a clean migration for pre-production. No data migration needed.
    Users will need to recreate their databases.
    """
    
    # 1. Add password_hash to users table (nullable for now to allow migration)
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("password_hash", sa.String(), nullable=True))
    
    # 2. Create submitters table
    op.create_table(
        "submitters",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_submitters_user_id"),
    )
    op.create_index("ix_submitters_id", "submitters", ["id"], unique=False)
    op.create_index("ix_submitters_user_id", "submitters", ["user_id"], unique=False)
    
    # 3. Update submissions table schema
    # Note: For a clean migration approach, we're dropping and recreating the submissions table
    # since there's no production data to preserve yet
    
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if "submissions" in inspector.get_table_names():
        # Get existing data (if any) - but we expect none in alpha
        try:
            existing_submissions = conn.execute(
                sa.text("SELECT * FROM submissions")
            ).fetchall()
            
            if existing_submissions:
                # If there's data, we need to handle it, but this shouldn't happen in alpha
                print("Warning: Existing submissions found. Manual migration may be required.")
        except Exception:
            existing_submissions = []
        
        # Drop old foreign keys and indices if they exist
        with op.batch_alter_table("submissions", schema=None) as batch_op:
            try:
                batch_op.drop_constraint("fk_submissions_submitter_id", type_="foreignkey")
            except Exception:
                pass  # Constraint might not exist
            try:
                batch_op.drop_index("ix_submissions_submitter_id")
            except Exception:
                pass  # Index might not exist
        
        # Add new columns
        with op.batch_alter_table("submissions", schema=None) as batch_op:
            # Add created_by_id column
            batch_op.add_column(
                sa.Column("created_by_id", sa.UUID(), nullable=True)  # Nullable initially
            )
        
        # For alpha/pre-production: Set a default creator if submissions exist
        # In production, this would need proper data migration
        if existing_submissions:
            # Get first user as default creator
            first_user = conn.execute(sa.text("SELECT id FROM users LIMIT 1")).fetchone()
            if first_user:
                conn.execute(
                    sa.text("UPDATE submissions SET created_by_id = :user_id"),
                    {"user_id": str(first_user[0])}
                )
        
        # Now make created_by_id non-nullable and update FK
        with op.batch_alter_table("submissions", schema=None) as batch_op:
            # Recreate FK to submitters instead of users (already dropped above)
            batch_op.create_foreign_key(
                "fk_submissions_submitter_id",
                "submitters",
                ["submitter_id"],
                ["id"]
            )
            
            # Add FK for created_by_id
            batch_op.create_foreign_key(
                "fk_submissions_created_by_id",
                "users",
                ["created_by_id"],
                ["id"]
            )
            
            # Make created_by_id non-nullable
            batch_op.alter_column("created_by_id", nullable=False)
        
        # Recreate index
        op.create_index("ix_submissions_submitter_id", "submissions", ["submitter_id"], unique=False)
        op.create_index("ix_submissions_created_by_id", "submissions", ["created_by_id"], unique=False)


def downgrade() -> None:
    """
    Rollback auth system redesign changes.
    
    Warning: This will lose submitter data and created_by tracking.
    """
    
    # Drop new indices
    with op.batch_alter_table("submissions", schema=None) as batch_op:
        try:
            batch_op.drop_index("ix_submissions_created_by_id")
        except Exception:
            # Index may not exist if migration was partially applied; safe to ignore
            pass
        
        # Drop new FK constraints
        try:
            batch_op.drop_constraint("fk_submissions_created_by_id", type_="foreignkey")
        except Exception:
            # Constraint may not exist if migration was partially applied; safe to ignore
            pass
        
        try:
            batch_op.drop_constraint("fk_submissions_submitter_id", type_="foreignkey")
        except Exception:
            # Constraint may not exist if migration was partially applied; safe to ignore
            pass
        
        # Drop created_by_id column
        try:
            batch_op.drop_column("created_by_id")
        except Exception:
            # Column may not exist if migration was partially applied; safe to ignore
            pass
        
        # Recreate old FK to users
        batch_op.create_foreign_key(
            "fk_submissions_submitter_id",
            "users",
            ["submitter_id"],
            ["id"]
        )
    
    # Drop submitters table
    op.drop_index("ix_submitters_user_id", table_name="submitters")
    op.drop_index("ix_submitters_id", table_name="submitters")
    op.drop_table("submitters")
    
    # Remove password_hash from users
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("password_hash")
