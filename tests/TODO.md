# Test TODOs (2026-02-05)

This file tracks tests removed or disabled because they were AI-generated and failing in CI. The failing tests are commented in-place with a matching TODO note.

## Removed files
- `tests/test_atomic_assignment_creation.py`: All tests failed. The `/api/assignments/create-with-files` endpoint currently returns `405 Method Not Allowed`, and one test also expects a mocked `upload_file` attribute that does not exist. Reintroduce when the endpoint and storage hooks are implemented.

## Disabled tests (commented in-place)
- `tests/test_artifact_lifecycle.py`
  - `test_orphan_detection_on_course_deletion`: Expected artifacts to become `orphaned` after course deletion, but status remained `attached`.
  - `test_orphan_detection_on_assignment_deletion`: Expected artifacts to become `orphaned` after assignment deletion, but status remained `attached`.
  - `test_orphan_cleanup_old_artifacts`: Cleanup endpoint returned `404` instead of `200`.
  - `test_cleanup_permission_restriction`: Cleanup endpoint returned `404` instead of `403`.
  - `test_cleanup_deletes_storage_files`: Cleanup endpoint returned `404` instead of `200`.
  - `test_bulk_status_update_operations`: Bulk update endpoint returned `404` instead of `200`.
  - `test_lifecycle_event_triggers`: Expected orphaning on lifecycle triggers, but status remained `attached`.

- `tests/test_artifact_permissions.py`
  - `test_artifact_list_permission_filtering`: Permission filtering allowed `Course1 Material` to appear unexpectedly.
  - `test_artifact_delete_permissions`: Delete returned `200` instead of expected `404` after deletion.
  - `test_artifact_delete_protection_active_submissions`: Delete returned `204` instead of expected `403/409`.
  - `test_artifact_download_permissions`: Download returned `404` instead of `200/302`.
  - `test_permission_computed_fields`: Response missing `can_view/can_edit/can_delete` fields.

- `tests/test_atomic_submission_creation.py`
  - `test_create_submission_invalid_assignment`: Returned `404` instead of expected `400`.
  - `test_submission_timestamps_and_metadata`: `submittedAt` timestamp did not fall between request start/end times.

- `tests/test_enhanced_artifacts.py`
  - `test_artifact_timestamps_auto_management`: `created_at` and `updated_at` differed by a few microseconds at creation time in GitHub CI.

## Permissions Migration TODOs (2026-02-17)
- Add mode-aware authorization tests that run the same scenarios under both `FAIR_DEPLOYMENT_MODE=COMMUNITY` and `FAIR_DEPLOYMENT_MODE=ENTERPRISE`.
- Add a focused matrix test for `/api/auth/me` ensuring returned `capabilities` reflect role + mode combinations.
- Cover alias compatibility for legacy roles (`student`, `professor`) in auth payload normalization and DB-migrated users.
- Add API contract tests for course visibility in community mode:
  - users can see courses they own and courses they are enrolled in.
  - enrollment code visibility is restricted to owner/admin responses.
- Add workflow/workflow-runs tests that are mode-aware:
  - community user-owner access should pass.
  - enterprise user (non-owner) should be denied where expected.
- Add artifact permission regression tests using capability semantics rather than explicit roles:
  - create/list/update/delete with owner override.
  - cleanup endpoint restricted to `cleanup_orphaned_artifacts`.
- Add submissions/submission-results tests for:
  - `manage_submission` and `update_submission_results` checks.
  - ownership override via course instructor.
  - timeline visibility rules for non-owner users.
- Add rubrics tests for:
  - create/generate/list/get/update/delete through `create_rubric`/`manage_rubric`.
  - own-rubric access vs admin global access.
