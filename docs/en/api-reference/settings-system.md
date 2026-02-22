---
title: Settings System
description: Developer reference for FAIR user settings architecture, APIs, and extension workflow
---

This page documents the current settings architecture in FAIR for both humans and AI assistants.

## Scope

The settings system covers:

- Persistent user settings in backend DB (`users.settings`)
- Local browser preferences via Zustand
- Query/mutation hooks for reading/updating settings
- Runtime preference application (theme/language/simple view)
- Conditional rendering via `IfSetting`

## Current architecture

### Backend

- Model field: `User.settings` (`JSON`/`JSONB`, non-null)
- Migration: `src/fair_platform/backend/alembic/versions/20260222_0010_add_user_settings_json.py`
- Router:
  - `GET /api/users/me/settings`
  - `PATCH /api/users/me/settings`
- Schemas:
  - `UserSettingsRead`
  - `UserSettingsUpdate`

Relevant files:

- `src/fair_platform/backend/data/models/user.py`
- `src/fair_platform/backend/api/schema/user.py`
- `src/fair_platform/backend/api/routers/users.py`
- `src/fair_platform/backend/core/security/permissions.py`

### Frontend

- Local store: `frontend-dev/src/store/local-preferences-store.ts`
- Local hooks:
  - `useLocalPreference`
  - `useLocalPreferences`
- Backend hooks:
  - `useUserSettings` (uses TanStack `useQueries`)
  - `useUserSetting`
  - `useUpdateUserSettings`
  - `useUpdateUserSetting`
  - `usePatchUserSettings`
- Preference bridge:
  - `usePreferenceSettings`
- Runtime sync:
  - `SettingsRuntime` in `frontend-dev/src/providers.tsx`
- Conditional component:
  - `IfSetting` in `frontend-dev/src/components/if-setting.tsx`

## API contract

### Get current user settings

```http
GET /api/users/me/settings
Authorization: Bearer <token>
```

Response:

```json
{
  "settings": {
    "preferences": {
      "theme": "system",
      "language": "en",
      "simpleView": false
    },
    "ai": {
      "personalization": {
        "chatPersonality": "default",
        "aboutYou": "",
        "persistentMemory": false
      },
      "models": {
        "webSearch": true,
        "defaultModel": "gpt-5-mini"
      }
    },
    "notifications": {
      "batchCompletion": false
    }
  }
}
```

### Replace current user settings

```http
PATCH /api/users/me/settings
Authorization: Bearer <token>
Content-Type: application/json
```

Body:

```json
{
  "settings": {
    "preferences": {
      "theme": "dark"
    }
  }
}
```

Important:

- Backend update is currently **replace**, not merge.
- Frontend `useUpdateUserSetting`/`usePatchUserSettings` already performs merge/path updates client-side before PATCH.

## Precedence and resolution rules

For theme/language/simple view:

1. Check local preference (`ui.*`).
2. Fallback to backend setting (`preferences.*`).
3. Apply at runtime in `SettingsRuntime`.

This provides fast UI response while preserving account-level persistence.

## Data shape conventions

- Backend stores arbitrary nested JSON.
- Frontend uses dot paths for path-based updates (`a.b.c`).
- Paths used for UI should be stable and documented.

Recommended top-level namespaces:

- `preferences.*`
- `ai.personalization.*`
- `ai.models.*`
- `notifications.*`

## Extension workflow

Use this when adding a new setting.

### 1. Define product behavior first

Specify:

- Path (for example `notifications.assignmentEscalation`)
- Type (`boolean`, enum, string, number, object)
- Default
- Scope:
  - local-only
  - backend-only
  - local-first + backend

### 2. Backend changes (if persistent)

In most cases no new DB column is needed because settings are JSON.

Checklist:

1. Update API schema docs if new typed surface is exposed.
2. Keep auth payload compatibility when settings affect auth bootstrap fields.
3. Add tests for:
   - GET current settings
   - PATCH update behavior
   - Any derived payload behavior (`/api/auth/me` etc.)

### 3. Frontend hook integration

Use existing hooks:

- `useUserSetting(path, fallback)`
- `useUpdateUserSetting()`
- `usePatchUserSettings()`
- `useLocalPreference(path, fallback?)`

Pattern:

```tsx
const value = useUserSetting<boolean>("notifications.assignmentEscalation", false).value;
const update = useUpdateUserSetting();

<Switch
  checked={value}
  onCheckedChange={(checked) =>
    update.mutate({ path: "notifications.assignmentEscalation", value: Boolean(checked) })
  }
/>
```

### 4. Add UI in settings sections

Current section registry:

- `frontend-dev/src/components/settings/settings-sections.tsx`

Add or extend a section component under:

- `frontend-dev/src/components/settings/sections/`

### 5. Add i18n labels

Update:

- `frontend-dev/src/i18n/locales/en.json`

If translation parity is required later, update other locales too.

### 6. Document it

Update:

- `docs/en/platform/settings.md` (user-facing)
- this page (system reference)

## Conditional rendering with settings

Use `IfSetting` when a feature should only render under specific settings.

Example:

```tsx
<IfSetting setting="preferences.simpleView" equals={false}>
  <AdvancedNavigation />
</IfSetting>
```

Props:

- `setting`: dot path
- `equals` (optional): exact value check; if omitted uses truthiness
- `scope`: `local` | `user` | `local-first` (default)
- `fallback` (optional): render alternative content

## Guidelines

- Keep setting keys explicit and stable. Avoid renaming paths casually.
- Prefer booleans/enums over free text for behavior flags.
- Keep defaults deterministic in hooks.
- Avoid hidden coupling: if a setting changes behavior across many screens, document all affected surfaces.
- If backend starts validating specific keys, document validation errors and migration strategy.
- For AI-agent compatibility, always include path, type, default, and scope in docs.

## Known limitations

- Backend settings endpoint currently replaces full settings payload on PATCH.
- No server-side schema validation for nested settings keys yet.
- Notification toggles are persisted, but delivery channels may still be implementation-dependent.
