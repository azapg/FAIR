from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from fair_platform.backend.data.migrations import (
    run_migrations_to_head,
    run_migrations_to_revision,
)


def test_google_login_migration_preserves_users_and_enforces_identity_uniqueness(
    tmp_path,
):
    url = f"sqlite:///{tmp_path / 'google.sqlite'}"
    run_migrations_to_revision("20261025_0037", url)
    user_id = uuid4().hex
    engine = create_engine(url)
    with engine.begin() as db:
        db.execute(
            text(
                "INSERT INTO users (id, name, email, normalized_email, role, password_hash, is_verified, settings) "
                "VALUES (:id, 'Existing', 'existing@example.edu', 'existing@example.edu', 'instructor', 'kept', 1, '{}')"
            ),
            {"id": user_id},
        )
    run_migrations_to_head(url)
    run_migrations_to_head(url)
    with engine.connect() as db:
        assert {"external_identities", "oidc_transactions"} <= set(
            inspect(db).get_table_names()
        )
        assert db.execute(text("SELECT id, role, password_hash FROM users")).one() == (
            user_id,
            "instructor",
            "kept",
        )
    insert = text(
        "INSERT INTO external_identities (id, user_id, connection_key, issuer, subject, created_at, last_login_at) "
        "VALUES (:id, :user, 'google', 'https://accounts.google.com', 'subject', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
    )
    with engine.begin() as db:
        db.execute(insert, {"id": uuid4().hex, "user": user_id})
    with pytest.raises(IntegrityError), engine.begin() as db:
        db.execute(insert, {"id": uuid4().hex, "user": user_id})
    engine.dispose()
