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
    title: str
    artifact_type: str
    mime: str
    storage_path: str
    storage_type: str
    meta: Optional[Dict[str, Any]] = None


class Submission(BaseModel):
    id: str
    submitter: Submitter
    submitted_at: str
    assignment: Assignment
    artifacts: List[Artifact]
    meta: Optional[Dict[str, Any]] = None
