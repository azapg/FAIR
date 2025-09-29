# Artifacts System Analysis & Improvement Proposals

## Current State Analysis

### Overview
The current artifacts system in the Fair Platform has several architectural issues that make it unsafe, difficult to use, and prone to orphaned resources. This document analyzes the current implementation and proposes solutions for a more robust, secure, and user-friendly artifacts system.

### Current Models & Relationships

#### 1. Artifact Model (`src/fair_platform/backend/data/models/artifact.py`)
```python
class Artifact(Base):
    __tablename__ = "artifacts"
    
    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_type: Mapped[str] = mapped_column("type", Text, nullable=False)
    mime: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    storage_type: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Many-to-many relationships
    assignments: Mapped[List["Assignment"]] = relationship(...)
    submissions: Mapped[List["Submission"]] = relationship(...)
```

**MISSING CRITICAL FIELDS:**
- `creator_id` - No ownership tracking
- `created_at` / `updated_at` - No timestamp tracking
- `status` - No lifecycle management
- `course_id` / `assignment_id` - No direct context relationship
- `access_level` - No permission scoping

#### 2. Current Relationships

**Assignment ↔ Artifact** (Many-to-Many via `assignment_artifacts`)
```python
assignment_artifacts = Table(
    "assignment_artifacts",
    Column("id", SAUUID, primary_key=True),
    Column("assignment_id", SAUUID, ForeignKey("assignments.id", ondelete="CASCADE")),
    Column("artifact_id", SAUUID, ForeignKey("artifacts.id", ondelete="CASCADE")),
    Column("role", Text, nullable=False),  # e.g., "template", "resource"
)
```

**Submission ↔ Artifact** (Many-to-Many via `submission_artifacts`)
```python
submission_artifacts = Table(
    "submission_artifacts",
    Column("id", SAUUID, primary_key=True),
    Column("submission_id", SAUUID, ForeignKey("submissions.id", ondelete="CASCADE")),
    Column("artifact_id", SAUUID, ForeignKey("artifacts.id", ondelete="CASCADE")),
)
```

### Current API Endpoints & Problems

#### Artifacts Router (`src/fair_platform/backend/api/routers/artifacts.py`)

1. **POST /api/artifacts** - Upload files
   - ✅ Creates artifacts from uploaded files
   - ❌ No owner/creator tracking
   - ❌ Creates orphaned artifacts immediately
   - ❌ No context (course/assignment) association
   - ❌ No cleanup mechanism for failed operations

2. **GET /api/artifacts** - List all artifacts
   - ✅ Returns all artifacts
   - ❌ No permission filtering (users can see artifacts they shouldn't)
   - ❌ No filtering by context (course/assignment)
   - ❌ No owner-based filtering

3. **GET /api/artifacts/{id}** - Get specific artifact
   - ✅ Returns artifact details
   - ❌ No access control (anyone can access any artifact)
   - ❌ No file download functionality

4. **PUT /api/artifacts/{id}** - Update artifact
   - ✅ Updates artifact metadata
   - ❌ No ownership verification
   - ❌ No audit trail

5. **DELETE /api/artifacts/{id}** - Delete artifact
   - ✅ Deletes artifact
   - ❌ No ownership verification
   - ❌ No file system cleanup
   - ❌ No validation if artifact is still in use

#### Submissions Router Problems

**POST /api/submissions** - Creates submission with artifacts
```python
class SyntheticSubmission(BaseModel):
    assignment_id: UUID
    submitter: str
    artifacts_ids: Optional[List[UUID]] = None  # BRITTLE DESIGN
```

**CRITICAL PROBLEMS:**
- Requires pre-existing artifacts (uploaded separately)
- If submission creation fails, artifacts become orphaned
- No atomic operation (upload + create submission)
- No cleanup mechanism for failed submissions
- Creates "synthetic users" instead of proper user management

### Current Frontend Implementation

#### TypeScript Types (`frontend-dev/src/hooks/use-artifacts.ts`)
```typescript
export type Artifact = {
  id: Id
  title: string
  artifact_type: string
  mime: string
  storage_path: string
  storage_type: string
  meta?: Record<string, unknown> | null
}
```

**MISSING FIELDS:**
- No creator information
- No status information
- No timestamps
- No access permissions

#### API Calls
- Standard CRUD operations
- No file upload handling
- No permission checks
- No context filtering

## Key Problems Identified

### 1. **Orphaned Artifacts Crisis**
- Artifacts created independently of their context
- Failed operations leave artifacts without cleanup
- No lifecycle management or garbage collection
- Security risk: abandoned files consuming storage

### 2. **No Ownership Model**
- Artifacts have no creator/owner tracking
- Anyone can modify/delete any artifact
- No permission system
- No audit trail

### 3. **Brittle API Design**
- Multi-step operations with failure points
- Pre-creation of artifacts required
- No atomic operations
- Complex client-side coordination needed

### 4. **Security Vulnerabilities**
- No access control on artifact access
- No permission validation
- Users can access artifacts from other courses
- No file download restrictions

### 5. **Poor User Experience**
- Complex upload flows
- No error recovery
- No progress tracking
- No file management interface

## Proposed Solutions

### Solution 1: Enhanced Artifact Model with Lifecycle Management

#### New Artifact Model
```python
class ArtifactStatus(str, Enum):
    pending = "pending"          # Just uploaded, not attached
    attached = "attached"        # Linked to assignment/submission
    orphaned = "orphaned"        # Parent deleted but artifact remains
    archived = "archived"        # Soft deleted
    deleted = "deleted"          # Marked for permanent deletion

class Artifact(Base):
    __tablename__ = "artifacts"
    
    # Current fields
    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_type: Mapped[str] = mapped_column("type", Text, nullable=False)
    mime: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    storage_type: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # NEW CRITICAL FIELDS
    creator_id: Mapped[UUID] = mapped_column(SAUUID, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, default=datetime.now, onupdate=datetime.now)
    status: Mapped[ArtifactStatus] = mapped_column(String, nullable=False, default=ArtifactStatus.pending)
    
    # Context relationships
    course_id: Mapped[Optional[UUID]] = mapped_column(SAUUID, ForeignKey("courses.id"), nullable=True)
    assignment_id: Mapped[Optional[UUID]] = mapped_column(SAUUID, ForeignKey("assignments.id"), nullable=True)
    
    # Access control
    access_level: Mapped[str] = mapped_column(String, nullable=False, default="private")  # private, course, public
    
    # Relationships
    creator: Mapped["User"] = relationship("User", back_populates="created_artifacts")
    course: Mapped[Optional["Course"]] = relationship("Course", back_populates="artifacts")
    assignment: Mapped[Optional["Assignment"]] = relationship("Assignment", back_populates="artifacts")
```

### Solution 2: Atomic Operations API

#### New Upload + Attach Endpoints

**POST /api/assignments/{id}/artifacts** - Upload directly to assignment
```python
@router.post("/assignments/{assignment_id}/artifacts", response_model=List[ArtifactRead])
def upload_assignment_artifacts(
    assignment_id: UUID,
    files: List[UploadFile],
    role: str = "resource",  # template, resource, rubric
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user)
):
    # Atomic operation: create artifacts + link to assignment
    # If any step fails, rollback everything
```

**POST /api/submissions/{id}/artifacts** - Upload directly to submission
```python
@router.post("/submissions/{submission_id}/artifacts", response_model=List[ArtifactRead])
def upload_submission_artifacts(
    submission_id: UUID,
    files: List[UploadFile],
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user)
):
    # Atomic operation: create artifacts + link to submission
```

**POST /api/submissions/create-with-files** - Atomic submission creation
```python
class SubmissionCreateWithFiles(BaseModel):
    assignment_id: UUID
    submitter_id: UUID
    # Files handled as multipart upload, not pre-existing IDs

@router.post("/submissions/create-with-files", response_model=SubmissionRead)
def create_submission_with_files(
    submission_data: SubmissionCreateWithFiles,
    files: List[UploadFile],
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user)
):
    # Single atomic operation:
    # 1. Validate assignment exists and user has permission
    # 2. Create submission
    # 3. Upload files as artifacts
    # 4. Link artifacts to submission
    # 5. If ANY step fails, rollback ALL changes
```

### Solution 3: Enhanced Permission System

#### Permission Matrix
```python
class ArtifactPermission:
    def can_view(self, user: User, artifact: Artifact) -> bool:
        # Creator can always view
        if artifact.creator_id == user.id:
            return True
            
        # Course instructors can view course artifacts
        if artifact.course_id and user.role == UserRole.professor:
            # Check if user is instructor of the course
            return artifact.course.instructor_id == user.id
            
        # Students can view their own submission artifacts
        if artifact.assignment_id:
            for submission in artifact.submissions:
                if submission.submitter_id == user.id:
                    return True
                    
        # Public artifacts
        if artifact.access_level == "public":
            return True
            
        return user.role == UserRole.admin
    
    def can_edit(self, user: User, artifact: Artifact) -> bool:
        # Only creator and course instructors can edit
        if artifact.creator_id == user.id:
            return True
            
        if artifact.course_id and user.role == UserRole.professor:
            return artifact.course.instructor_id == user.id
            
        return user.role == UserRole.admin
    
    def can_delete(self, user: User, artifact: Artifact) -> bool:
        # Similar to edit, but with additional checks
        if not self.can_edit(user, artifact):
            return False
            
        # Don't allow deletion if artifact is attached to active submissions
        if artifact.status == ArtifactStatus.attached:
            active_submissions = [s for s in artifact.submissions if s.status != SubmissionStatus.graded]
            if active_submissions and artifact.creator_id != user.id:
                return False
                
        return True
```

### Solution 4: Lifecycle Management & Cleanup

#### Artifact Lifecycle Events
```python
class ArtifactLifecycleManager:
    def mark_orphaned(self, artifact_id: UUID):
        """Mark artifact as orphaned when parent is deleted"""
        artifact = db.get(Artifact, artifact_id)
        if artifact and not (artifact.assignments or artifact.submissions):
            artifact.status = ArtifactStatus.orphaned
            # Schedule for cleanup after grace period
            
    def cleanup_orphaned(self, older_than_days: int = 7):
        """Clean up orphaned artifacts older than specified days"""
        cutoff = datetime.now() - timedelta(days=older_than_days)
        orphaned_artifacts = db.query(Artifact).filter(
            Artifact.status == ArtifactStatus.orphaned,
            Artifact.updated_at < cutoff
        ).all()
        
        for artifact in orphaned_artifacts:
            self.permanent_delete(artifact)
            
    def permanent_delete(self, artifact: Artifact):
        """Permanently delete artifact and associated files"""
        # Delete file from storage
        storage_path = Path(artifact.storage_path)
        if storage_path.exists():
            storage_path.unlink()
            
        # Delete from database
        db.delete(artifact)
        db.commit()
```

#### Background Cleanup Job
```python
@router.post("/admin/artifacts/cleanup")
def cleanup_artifacts(
    older_than_days: int = 7,
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403)
        
    lifecycle_manager = ArtifactLifecycleManager()
    cleanup_count = lifecycle_manager.cleanup_orphaned(older_than_days)
    return {"cleaned_up": cleanup_count}
```

### Solution 5: Enhanced Frontend Implementation

#### New TypeScript Types
```typescript
export type ArtifactStatus = 'pending' | 'attached' | 'orphaned' | 'archived' | 'deleted'
export type AccessLevel = 'private' | 'course' | 'public'

export type Artifact = {
  id: Id
  title: string
  artifact_type: string
  mime: string
  storage_path: string
  storage_type: string
  meta?: Record<string, unknown> | null
  
  // New fields
  creator_id: Id
  created_at: string
  updated_at: string
  status: ArtifactStatus
  course_id?: Id
  assignment_id?: Id
  access_level: AccessLevel
  
  // Computed fields
  creator?: User
  course?: Course
  assignment?: Assignment
  download_url?: string
  can_edit?: boolean
  can_delete?: boolean
}
```

#### Enhanced Hooks
```typescript
// Upload with context
export function useUploadArtifactsToAssignment() {
  return useMutation({
    mutationFn: ({ assignmentId, files, role }: { 
      assignmentId: Id, 
      files: FileList, 
      role: string 
    }) => {
      const formData = new FormData()
      Array.from(files).forEach(file => formData.append('files', file))
      formData.append('role', role)
      
      return api.post(`/assignments/${assignmentId}/artifacts`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    }
  })
}

// Create submission with files atomically
export function useCreateSubmissionWithFiles() {
  return useMutation({
    mutationFn: ({ submissionData, files }: {
      submissionData: SubmissionCreateData,
      files: FileList
    }) => {
      const formData = new FormData()
      formData.append('submission_data', JSON.stringify(submissionData))
      Array.from(files).forEach(file => formData.append('files', file))
      
      return api.post('/submissions/create-with-files', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    }
  })
}

// Permission-aware artifact listing
export function useUserArtifacts(context?: { courseId?: Id, assignmentId?: Id }) {
  return useQuery({
    queryKey: ['artifacts', 'user', context],
    queryFn: () => api.get('/artifacts/my-artifacts', { params: context })
  })
}
```

## Migration Strategy

### Phase 1: Database Schema Updates
1. Add new columns to `artifacts` table
2. Create new indexes for performance
3. Populate `creator_id` from existing data where possible
4. Mark existing artifacts as `attached` if they have relationships

### Phase 2: API Enhancements
1. Implement new atomic endpoints
2. Add permission checks to existing endpoints
3. Deprecate old upload workflows
4. Add lifecycle management endpoints

### Phase 3: Frontend Updates
1. Update TypeScript types
2. Implement new upload components
3. Add permission-aware UI elements
4. Create artifact management interface

### Phase 4: Cleanup & Migration
1. Implement background cleanup jobs
2. Migrate existing workflows to new atomic operations
3. Remove deprecated endpoints
4. Add monitoring and alerting

## Benefits of Proposed Solution

### 1. **Eliminates Orphaned Artifacts**
- Atomic operations prevent partial failures
- Lifecycle management tracks artifact states
- Automated cleanup removes abandoned files

### 2. **Secure Access Control**
- Creator-based ownership model
- Role-based permissions
- Course-scoped access control

### 3. **Better API Design**
- Single-step operations for common workflows
- Clear error handling and rollback
- Context-aware endpoints

### 4. **Enhanced User Experience**
- Direct file uploads to assignments/submissions
- Progress tracking and error recovery
- Proper file management interface

### 5. **Improved Maintainability**
- Clear data model with proper relationships
- Audit trails for compliance
- Automated cleanup reduces manual intervention

## Implementation Priority

1. **HIGH**: Database schema updates and basic ownership model
2. **HIGH**: Atomic submission creation with files
3. **MEDIUM**: Enhanced permission system
4. **MEDIUM**: Lifecycle management and cleanup
5. **LOW**: Advanced UI features and optimizations

This comprehensive solution addresses all the identified problems while providing a clear migration path and significant improvements to security, reliability, and user experience.