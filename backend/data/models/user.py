from enum import Enum
from sqlalchemy import Integer, String, Enum as SAEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class UserRole(str, Enum):
    professor = "professor"
    student = "student"
    admin = "admin"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, name="user_role"), nullable=False, default=UserRole.student)
    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role}>"
