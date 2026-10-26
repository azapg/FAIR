from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from fair_platform.backend.data.models import ExternalIdentity, RegistrationInvite, User
from fair_platform.backend.data.models.external_identity import OIDCTransaction
from fair_platform.backend.data.models.user import normalize_email_address
from fair_platform.backend.services.access_control import (
    AccessPolicyError,
    authorize_registration_with_invite_hash,
)


class IdentityConflict(ValueError):
    pass


def resolve_identity(
    db: Session,
    claims: dict,
    transaction: OIDCTransaction,
    *,
    linking_user: User | None = None,
) -> User:
    """Resolve an already-verified provider subject. Email alone never links accounts."""
    identity = db.scalar(
        select(ExternalIdentity).where(
            ExternalIdentity.issuer == claims["issuer"],
            ExternalIdentity.subject == claims["subject"],
        )
    )
    email = normalize_email_address(claims["email"])
    now = datetime.now(timezone.utc)
    if transaction.purpose == "link":
        if (
            linking_user is None
            or linking_user.id != transaction.user_id
            or linking_user.normalized_email != email
            or db.scalar(
                select(ExternalIdentity.id).where(
                    ExternalIdentity.user_id == linking_user.id,
                    ExternalIdentity.connection_key == transaction.connection_key,
                )
            )
            is not None
            or identity is not None
        ):
            raise IdentityConflict("Google account cannot be connected")
        user = linking_user
        user.is_verified = True
    elif identity:
        identity.last_login_at = now
        return db.get(User, identity.user_id)
    else:
        if db.scalar(select(User.id).where(User.normalized_email == email)) is not None:
            raise IdentityConflict("Sign in and connect Google in Profile")
        invitation = authorize_registration_with_invite_hash(
            db,
            normalized_email=email,
            invite_hash=transaction.invite_hash,
        )
        user = User(
            id=uuid4(),
            email=claims["email"],
            name=claims["name"],
            role="user",
            password_hash=None,
            is_verified=True,
        )
        db.add(user)
        db.flush()
        if invitation:
            redeemed = db.execute(
                update(RegistrationInvite)
                .where(
                    RegistrationInvite.id == invitation.id,
                    RegistrationInvite.redeemed_at.is_(None),
                    RegistrationInvite.revoked_at.is_(None),
                    RegistrationInvite.expires_at > now,
                )
                .values(redeemed_at=now, redeemed_by_user_id=user.id)
                .execution_options(synchronize_session=False)
            )
            if redeemed.rowcount != 1:
                raise AccessPolicyError(
                    status_code=403,
                    code="registration_not_permitted",
                    detail="A valid registration invitation is required.",
                )
    db.add(
        ExternalIdentity(
            user_id=user.id,
            connection_key=transaction.connection_key,
            issuer=claims["issuer"],
            subject=claims["subject"],
            last_login_at=now,
        )
    )
    db.flush()
    return user
