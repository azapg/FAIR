from typing import Optional, Dict, Any, List

from pydantic import BaseModel


class Submitter(BaseModel):
    id: str
    name: str
    email: str


class Assignment(BaseModel):
    id: str
    title: str
    description: str
    deadline: str
    max_score: float


class Artifact(BaseModel):
    id: Optional[str] = None
    title: str
    artifact_type: str
    mime: str
    storage_path: Optional[str] = None
    storage_type: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class Rubric(BaseModel):
    id: Optional[str] = None
    name: str
    content: Dict[str, Any]


class Submission(BaseModel):
    id: str
    submitter: Submitter
    submitted_at: str
    assignment: Assignment
    artifacts: List[Artifact]
    meta: Optional[Dict[str, Any]] = None
