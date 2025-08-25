from uuid import UUID
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import Text, JSON, UUID as SAUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .assignment import Assignment
    from .submission import Submission

class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_type: Mapped[str] = mapped_column("type", Text, nullable=False)
    mime: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    storage_type: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    assignments: Mapped[List["Assignment"]] = relationship(
        "Assignment",
        secondary="assignment_artifacts",
        back_populates="artifacts",
        viewonly=False,
    )

    submissions: Mapped[List["Submission"]] = relationship(
        "Submission",
        secondary="submission_artifacts",
        back_populates="artifacts",
        viewonly=False,
    )

    def __repr__(self) -> str:
        return (
            f"<Artifact id={self.id} title={self.title!r} "
            f"type={self.artifact_type!r} mime={self.mime!r}>"
        )
