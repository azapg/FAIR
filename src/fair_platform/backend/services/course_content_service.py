from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from fair_platform.backend.data.models.artifact import (
    AccessLevel,
    Artifact,
    ArtifactStatus,
)
from fair_platform.backend.data.models.assignment import Assignment, AssignmentStatus
from fair_platform.backend.data.models.lms_content import (
    CourseContentVisibility,
    CourseItem,
    CourseSection,
)
from fair_platform.backend.data.models.lms_quiz import Quiz, QuizAttempt, QuizStatus


COURSE_ITEM_KINDS = {"heading", "page", "link", "file", "assignment", "quiz"}
RESOURCE_TYPES = {"file": "artifact", "assignment": "assignment", "quiz": "quiz"}
PAYLOAD_SCHEMAS = {
    "heading": "urn:fair:lms:course-item:heading:v1",
    "page": "urn:fair:lms:course-item:page:v1",
    "link": "urn:fair:lms:course-item:link:v1",
    "file": "urn:fair:lms:course-item:file:v1",
    "assignment": "urn:fair:lms:course-item:assignment:v1",
    "quiz": "urn:fair:lms:course-item:quiz:v1",
}


class CourseContentError(ValueError):
    pass


class CourseContentNotFound(CourseContentError):
    pass


class CourseContentConflict(CourseContentError):
    pass


def _enum_value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


class CourseContentService:
    def __init__(self, db: Session):
        self.db = db

    def list_sections(
        self, course_id: UUID, *, staff_view: bool
    ) -> list[tuple[CourseSection, list[CourseItem]]]:
        sections = self.db.scalars(
            select(CourseSection)
            .where(CourseSection.course_id == course_id)
            .options(selectinload(CourseSection.items))
            .order_by(CourseSection.position, CourseSection.id)
        ).all()

        if staff_view:
            return [
                (
                    section,
                    sorted(section.items, key=lambda item: (item.position, item.id)),
                )
                for section in sections
            ]

        published_sections = [
            section
            for section in sections
            if _enum_value(section.visibility)
            == CourseContentVisibility.published.value
        ]
        assignment_ids = {
            item.resource_id
            for section in published_sections
            for item in section.items
            if item.kind == "assignment" and item.resource_id is not None
        }
        published_assignments = set(
            self.db.scalars(
                select(Assignment.id).where(
                    Assignment.id.in_(assignment_ids),
                    Assignment.course_id == course_id,
                    Assignment.status == AssignmentStatus.published,
                )
            ).all()
            if assignment_ids
            else []
        )
        quiz_ids = {
            item.resource_id
            for section in published_sections
            for item in section.items
            if item.kind == "quiz" and item.resource_id is not None
        }
        published_quizzes = set(
            self.db.scalars(
                select(Quiz.id).where(
                    Quiz.id.in_(quiz_ids),
                    Quiz.course_id == course_id,
                    Quiz.status.in_([QuizStatus.published, QuizStatus.closed]),
                )
            ).all()
            if quiz_ids
            else []
        )

        result: list[tuple[CourseSection, list[CourseItem]]] = []
        for section in published_sections:
            visible_items = []
            for item in sorted(
                section.items, key=lambda value: (value.position, value.id)
            ):
                if (
                    _enum_value(item.visibility)
                    != CourseContentVisibility.published.value
                ):
                    continue
                if (
                    item.kind == "assignment"
                    and item.resource_id not in published_assignments
                ):
                    continue
                if item.kind == "quiz" and item.resource_id not in published_quizzes:
                    continue
                visible_items.append(item)
            result.append((section, visible_items))
        return result

    def create_section(
        self,
        course_id: UUID,
        *,
        title: str,
        summary: str | None,
        visibility: CourseContentVisibility,
    ) -> CourseSection:
        position = self.db.scalar(
            select(func.max(CourseSection.position)).where(
                CourseSection.course_id == course_id
            )
        )
        section = CourseSection(
            course_id=course_id,
            title=self._required_text(title, "Section title"),
            summary=self._optional_text(summary),
            position=(position + 1) if position is not None else 0,
            visibility=visibility,
        )
        self.db.add(section)
        self.db.flush()
        return section

    def update_section(
        self, course_id: UUID, section_id: UUID, changes: dict[str, Any]
    ) -> CourseSection:
        section = self._section(course_id, section_id)
        if "title" in changes:
            section.title = self._required_text(changes["title"], "Section title")
        if "summary" in changes:
            section.summary = self._optional_text(changes["summary"])
        if "visibility" in changes:
            section.visibility = changes["visibility"]
        self.db.flush()
        return section

    def delete_section(self, course_id: UUID, section_id: UUID) -> None:
        section = self._section(course_id, section_id)
        item_ids = list(
            self.db.scalars(
                select(CourseItem.id)
                .where(
                    CourseItem.course_id == course_id,
                    CourseItem.section_id == section_id,
                )
                .order_by(CourseItem.position, CourseItem.id)
                .with_for_update()
            ).all()
        )
        # Route every child through its resource-specific guard. In particular,
        # published or attempted quizzes must not be orphaned by a section-level
        # cascade, while draft quizzes are deleted with their content item.
        for item_id in reversed(item_ids):
            self.delete_item(course_id, item_id)
        self.db.delete(section)
        self.db.flush()
        self._compact_sections(course_id)

    def reorder_sections(
        self, course_id: UUID, ordered_ids: list[UUID]
    ) -> list[CourseSection]:
        sections = self.db.scalars(
            select(CourseSection)
            .where(CourseSection.course_id == course_id)
            .order_by(CourseSection.position)
            .with_for_update()
        ).all()
        self._validate_exact_order(
            ordered_ids,
            [section.id for section in sections],
            "section",
        )
        by_id = {section.id: section for section in sections}
        ordered = [by_id[section_id] for section_id in ordered_ids]
        self._assign_positions(ordered)
        return ordered

    def create_item(
        self,
        course_id: UUID,
        section_id: UUID,
        *,
        title: str,
        kind: str,
        visibility: CourseContentVisibility,
        resource_id: UUID | None,
        payload: dict[str, Any],
    ) -> CourseItem:
        self._section(course_id, section_id)
        resource_type, normalized_payload = self._validate_definition(
            course_id=course_id,
            kind=kind,
            resource_id=resource_id,
            payload=payload,
        )
        if resource_type is not None and resource_id is not None:
            linked = self.db.scalar(
                select(CourseItem.id).where(
                    CourseItem.course_id == course_id,
                    CourseItem.resource_type == resource_type,
                    CourseItem.resource_id == resource_id,
                )
            )
            if linked is not None:
                raise CourseContentConflict(
                    "This resource is already linked in the course content"
                )
        position = self.db.scalar(
            select(func.max(CourseItem.position)).where(
                CourseItem.section_id == section_id
            )
        )
        item = CourseItem(
            course_id=course_id,
            section_id=section_id,
            title=self._required_text(title, "Item title"),
            position=(position + 1) if position is not None else 0,
            kind=kind,
            visibility=visibility,
            resource_type=resource_type,
            resource_id=resource_id,
            payload_schema_uri=PAYLOAD_SCHEMAS[kind],
            payload=normalized_payload,
        )
        self.db.add(item)
        self.db.flush()
        return item

    def update_item(
        self, course_id: UUID, item_id: UUID, changes: dict[str, Any]
    ) -> CourseItem:
        item = self._item(course_id, item_id)
        if "title" in changes:
            item.title = self._required_text(changes["title"], "Item title")
        if "visibility" in changes:
            item.visibility = changes["visibility"]
        if "payload" in changes:
            _, item.payload = self._validate_definition(
                course_id=course_id,
                kind=item.kind,
                resource_id=item.resource_id,
                payload=changes["payload"],
            )
        self.db.flush()
        return item

    def delete_item(self, course_id: UUID, item_id: UUID) -> None:
        item = self._item(course_id, item_id)
        section_id = item.section_id
        if item.kind == "quiz" and item.resource_id is not None:
            quiz = self.db.get(Quiz, item.resource_id)
            has_attempts = self.db.scalar(
                select(QuizAttempt.id).where(QuizAttempt.quiz_id == item.resource_id)
            )
            if (
                quiz is None
                or _enum_value(quiz.status) != QuizStatus.draft.value
                or has_attempts is not None
            ):
                raise CourseContentConflict(
                    "Published quizzes cannot be removed from course content; close the quiz instead"
                )
            self.db.delete(item)
            self.db.flush()
            self.db.delete(quiz)
            self.db.flush()
            self._compact_items(section_id)
            return
        self.db.delete(item)
        self.db.flush()
        self._compact_items(section_id)

    def remove_resource_links(self, resource_type: str, resource_id: UUID) -> int:
        """Remove outline links to a deleted resource and repair item ordering."""
        items = self.db.scalars(
            select(CourseItem)
            .where(
                CourseItem.resource_type == resource_type,
                CourseItem.resource_id == resource_id,
            )
            .with_for_update()
        ).all()
        item_ids = [item.id for item in items]
        if item_ids:
            copied_items = self.db.scalars(
                select(CourseItem)
                .where(CourseItem.copied_from_id.in_(item_ids))
                .with_for_update()
            ).all()
            for copied_item in copied_items:
                copied_item.copied_from_id = None
        section_ids = {item.section_id for item in items}
        for item in items:
            self.db.delete(item)
        self.db.flush()
        for section_id in sorted(section_ids, key=str):
            self._compact_items(section_id)
        return len(items)

    def reorder_items(
        self, course_id: UUID, section_id: UUID, ordered_ids: list[UUID]
    ) -> list[CourseItem]:
        self._section(course_id, section_id)
        items = self.db.scalars(
            select(CourseItem)
            .where(
                CourseItem.course_id == course_id,
                CourseItem.section_id == section_id,
            )
            .order_by(CourseItem.position)
            .with_for_update()
        ).all()
        self._validate_exact_order(
            ordered_ids,
            [item.id for item in items],
            "item",
        )
        by_id = {item.id: item for item in items}
        ordered = [by_id[item_id] for item_id in ordered_ids]
        self._assign_positions(ordered)
        return ordered

    def _section(self, course_id: UUID, section_id: UUID) -> CourseSection:
        section = self.db.scalar(
            select(CourseSection).where(
                CourseSection.id == section_id,
                CourseSection.course_id == course_id,
            )
        )
        if section is None:
            raise CourseContentNotFound("Course section not found")
        return section

    def _item(self, course_id: UUID, item_id: UUID) -> CourseItem:
        item = self.db.scalar(
            select(CourseItem).where(
                CourseItem.id == item_id,
                CourseItem.course_id == course_id,
            )
        )
        if item is None:
            raise CourseContentNotFound("Course item not found")
        return item

    def _validate_definition(
        self,
        *,
        course_id: UUID,
        kind: str,
        resource_id: UUID | None,
        payload: dict[str, Any] | None,
    ) -> tuple[str | None, dict[str, Any]]:
        if kind not in COURSE_ITEM_KINDS:
            raise CourseContentError(f"Unsupported course item kind: {kind}")
        if not isinstance(payload, dict):
            raise CourseContentError("Item payload must be an object")

        if kind == "page":
            if resource_id is not None or set(payload) != {"body"}:
                raise CourseContentError("Page items require only a body payload")
            body = payload.get("body")
            if not isinstance(body, str) or not body.strip():
                raise CourseContentError("Page body is required")
            return None, {"body": body.strip()}

        if kind == "link":
            if resource_id is not None or set(payload) != {"url"}:
                raise CourseContentError("Link items require only a URL payload")
            raw_url = payload.get("url")
            if not isinstance(raw_url, str):
                raise CourseContentError("Link URL is required")
            url = raw_url.strip()
            parsed = urlsplit(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise CourseContentError("Link URL must use http or https")
            return None, {"url": url}

        if kind == "heading":
            if resource_id is not None or payload:
                raise CourseContentError(
                    "Heading items cannot link a resource or payload"
                )
            return None, {}

        if payload:
            raise CourseContentError(f"{kind.title()} items cannot have a payload")
        if resource_id is None:
            raise CourseContentError(f"{kind.title()} resource is required")

        if kind == "assignment":
            assignment = self.db.get(Assignment, resource_id)
            if assignment is None or assignment.course_id != course_id:
                raise CourseContentError(
                    "Assignment items must link an assignment from this course"
                )
        elif kind == "quiz":
            quiz = self.db.get(Quiz, resource_id)
            if quiz is None or quiz.course_id != course_id:
                raise CourseContentError("Quiz items must link a quiz from this course")
        elif kind == "file":
            artifact = self.db.get(Artifact, resource_id)
            if (
                artifact is None
                or artifact.course_id != course_id
                or _enum_value(artifact.status) == ArtifactStatus.archived.value
                or _enum_value(artifact.access_level)
                not in {AccessLevel.course.value, AccessLevel.public.value}
            ):
                raise CourseContentError(
                    "File items must link an active course-visible artifact from this course"
                )
        return RESOURCE_TYPES[kind], {}

    def _compact_sections(self, course_id: UUID) -> None:
        sections = self.db.scalars(
            select(CourseSection)
            .where(CourseSection.course_id == course_id)
            .order_by(CourseSection.position, CourseSection.id)
            .with_for_update()
        ).all()
        self._assign_positions(sections)

    def _compact_items(self, section_id: UUID) -> None:
        items = self.db.scalars(
            select(CourseItem)
            .where(CourseItem.section_id == section_id)
            .order_by(CourseItem.position, CourseItem.id)
            .with_for_update()
        ).all()
        self._assign_positions(items)

    def _assign_positions(
        self, ordered: list[CourseSection] | list[CourseItem]
    ) -> None:
        if not ordered:
            return
        temporary_start = max(item.position for item in ordered) + len(ordered) + 1
        for index, item in enumerate(ordered):
            item.position = temporary_start + index
        self.db.flush()
        for index, item in enumerate(ordered):
            item.position = index
        self.db.flush()

    @staticmethod
    def _validate_exact_order(
        requested: list[UUID], existing: list[UUID], entity: str
    ) -> None:
        if len(requested) != len(set(requested)):
            raise CourseContentConflict(f"Ordered {entity} IDs contain duplicates")
        if set(requested) != set(existing):
            raise CourseContentConflict(
                f"Ordered {entity} IDs must exactly match current membership"
            )

    @staticmethod
    def _required_text(value: object, label: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise CourseContentError(f"{label} is required")
        return value.strip()

    @staticmethod
    def _optional_text(value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise CourseContentError("Summary must be text")
        stripped = value.strip()
        return stripped or None


__all__ = [
    "CourseContentConflict",
    "CourseContentError",
    "CourseContentNotFound",
    "CourseContentService",
]
