from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UUID as SAUUID,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .types import json_document_type


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OrganizationMembershipRole(str, Enum):
    owner = "owner"
    admin = "admin"
    member = "member"


class MembershipStatus(str, Enum):
    active = "active"
    inactive = "inactive"


class CourseGroupMembershipRole(str, Enum):
    member = "member"
    leader = "leader"


class ExternalIdentifierSubjectType(str, Enum):
    user = "user"
    course = "course"
    cohort = "cohort"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(
        json_document_type(), nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now
    )

    memberships: Mapped[list["OrganizationMembership"]] = relationship(
        "OrganizationMembership",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    cohorts: Mapped[list["Cohort"]] = relationship(
        "Cohort", back_populates="organization", cascade="all, delete-orphan"
    )
    courses = relationship("Course", back_populates="organization")


class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "user_id",
            name="uq_organization_memberships_organization_user",
        ),
        CheckConstraint(
            "role IN ('owner', 'admin', 'member')",
            name="ck_organization_memberships_role",
        ),
        CheckConstraint(
            "status IN ('active', 'inactive')",
            name="ck_organization_memberships_status",
        ),
        Index("ix_organization_memberships_user_status", "user_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    role: Mapped[OrganizationMembershipRole] = mapped_column(
        String(32), nullable=False, default=OrganizationMembershipRole.member
    )
    status: Mapped[MembershipStatus] = mapped_column(
        String(32), nullable=False, default=MembershipStatus.active
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now
    )

    organization: Mapped[Organization] = relationship(
        "Organization", back_populates="memberships"
    )


class Cohort(Base):
    __tablename__ = "cohorts"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "name", name="uq_cohorts_organization_name"
        ),
        UniqueConstraint("id", "organization_id", name="uq_cohorts_id_organization"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now
    )

    organization: Mapped[Organization] = relationship(
        "Organization", back_populates="cohorts"
    )
    memberships: Mapped[list["CohortMembership"]] = relationship(
        "CohortMembership", back_populates="cohort", cascade="all, delete-orphan"
    )


class CohortMembership(Base):
    __tablename__ = "cohort_memberships"
    __table_args__ = (
        ForeignKeyConstraint(
            ["cohort_id", "organization_id"],
            ["cohorts.id", "cohorts.organization_id"],
            name="fk_cohort_memberships_cohort_organization",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["organization_id", "user_id"],
            [
                "organization_memberships.organization_id",
                "organization_memberships.user_id",
            ],
            name="fk_cohort_memberships_organization_user",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "cohort_id", "user_id", name="uq_cohort_memberships_cohort_user"
        ),
        CheckConstraint(
            "status IN ('active', 'inactive')",
            name="ck_cohort_memberships_status",
        ),
        Index("ix_cohort_memberships_user_status", "user_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    cohort_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    user_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    status: Mapped[MembershipStatus] = mapped_column(
        String(32), nullable=False, default=MembershipStatus.active
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now
    )

    cohort: Mapped[Cohort] = relationship("Cohort", back_populates="memberships")


class CourseGroup(Base):
    __tablename__ = "course_groups"
    __table_args__ = (
        UniqueConstraint("course_id", "name", name="uq_course_groups_course_name"),
        UniqueConstraint("id", "course_id", name="uq_course_groups_id_course"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now
    )

    course = relationship("Course", back_populates="groups")
    memberships: Mapped[list["CourseGroupMembership"]] = relationship(
        "CourseGroupMembership",
        back_populates="group",
        cascade="all, delete-orphan",
    )


class CourseGroupMembership(Base):
    __tablename__ = "course_group_memberships"
    __table_args__ = (
        ForeignKeyConstraint(
            ["group_id", "course_id"],
            ["course_groups.id", "course_groups.course_id"],
            name="fk_course_group_memberships_group_course",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["user_id", "course_id"],
            ["enrollments.user_id", "enrollments.course_id"],
            name="fk_course_group_memberships_enrollment",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "group_id", "user_id", name="uq_course_group_memberships_group_user"
        ),
        CheckConstraint(
            "role IN ('member', 'leader')",
            name="ck_course_group_memberships_role",
        ),
        Index("ix_course_group_memberships_course_user", "course_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    group_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    user_id: Mapped[UUID] = mapped_column(SAUUID, nullable=False)
    role: Mapped[CourseGroupMembershipRole] = mapped_column(
        String(32), nullable=False, default=CourseGroupMembershipRole.member
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )

    group: Mapped[CourseGroup] = relationship(
        "CourseGroup", back_populates="memberships"
    )


class ExternalIdentifier(Base):
    """A scoped mapping from an institutional identifier to one FAIR resource."""

    __tablename__ = "external_identifiers"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "user_id"],
            [
                "organization_memberships.organization_id",
                "organization_memberships.user_id",
            ],
            name="fk_external_identifiers_organization_user",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["course_id", "organization_id"],
            ["courses.id", "courses.organization_id"],
            name="fk_external_identifiers_course_organization",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["cohort_id", "organization_id"],
            ["cohorts.id", "cohorts.organization_id"],
            name="fk_external_identifiers_cohort_organization",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "organization_id",
            "system",
            "subject_type",
            "external_id",
            name="uq_external_identifiers_external",
        ),
        UniqueConstraint(
            "organization_id",
            "system",
            "user_id",
            name="uq_external_identifiers_user",
        ),
        UniqueConstraint(
            "organization_id",
            "system",
            "course_id",
            name="uq_external_identifiers_course",
        ),
        UniqueConstraint(
            "organization_id",
            "system",
            "cohort_id",
            name="uq_external_identifiers_cohort",
        ),
        CheckConstraint(
            "(subject_type = 'user' AND user_id IS NOT NULL "
            "AND course_id IS NULL AND cohort_id IS NULL) OR "
            "(subject_type = 'course' AND course_id IS NOT NULL "
            "AND user_id IS NULL AND cohort_id IS NULL) OR "
            "(subject_type = 'cohort' AND cohort_id IS NOT NULL "
            "AND user_id IS NULL AND course_id IS NULL)",
            name="ck_external_identifiers_subject",
        ),
        Index("ix_external_identifiers_lookup", "system", "external_id"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    system: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_type: Mapped[ExternalIdentifierSubjectType] = mapped_column(
        String(32), nullable=False
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[Optional[UUID]] = mapped_column(SAUUID, nullable=True)
    course_id: Mapped[Optional[UUID]] = mapped_column(SAUUID, nullable=True)
    cohort_id: Mapped[Optional[UUID]] = mapped_column(SAUUID, nullable=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(
        json_document_type(), nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now
    )


__all__ = [
    "Cohort",
    "CohortMembership",
    "CourseGroup",
    "CourseGroupMembership",
    "CourseGroupMembershipRole",
    "ExternalIdentifier",
    "ExternalIdentifierSubjectType",
    "MembershipStatus",
    "Organization",
    "OrganizationMembership",
    "OrganizationMembershipRole",
]
