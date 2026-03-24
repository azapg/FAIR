# State Injection Specification

## Overview

This specification defines a system for injecting initial application state into the frontend SPA via a global `window.__FAIR_INITIAL_STATE__` object. This eliminates redundant API calls during app initialization and improves perceived performance by reducing loader spinners and cascading network requests.

## Problem Statement

Currently, the frontend must make multiple API calls after loading to determine:
- Whether the user is authenticated
- User identity, role, and capabilities
- Feature availability (e.g., email enabled, email verification enforcement)
- Platform deployment mode

This results in:
- Unnecessary delays before UI can be properly rendered
- Multiple loading states (initial auth check, system config check)
- Potential for race conditions between dependent requests
- Worse perceived performance

## Solution: Window State Injection

The backend will inject a JSON object into the HTML template before serving the SPA, containing all necessary initial state. This data is computed server-side once and included in the initial HTTP response.

## Architecture

### State Injection Pipeline (Production Only)

**Note**: State injection is a **production-only feature** enabled by `fair serve`. In development mode (`fair dev`), the frontend makes normal API calls. This keeps the dev setup simple and avoids unnecessary complexity.

```
Production Request to / (FastAPI Handler)
    ↓
    ├─ User authentication check (via JWT cookie or unauthenticated state)
    ├─ User capabilities computation (from role + deployment mode)
    ├─ System features fetch (email_enabled, enforce_email_verification, etc.)
    ├─ Platform config fetch (deployment mode, base_url, etc.)
    ↓
    └─→ Render HTML with <script id="__FAIR_INITIAL_STATE__" type="application/json">
         {state object}
         </script>
    ↓
React App Bootstrap (Production)
    ↓
    ├─ Hydrate from window.__FAIR_INITIAL_STATE__
    ├─ Initialize Zustand store with injected state
    ├─ Skip redundant /api/auth/me and /api/v1/system/config calls
    ↓
    └─→ Render UI with instant knowledge of auth/features
```

### Where Injection Happens

**Production Mode** (`fair serve`): The backend's SPA fallback middleware in `main.py` serves `index.html` with injected state.

- A route handler intercepts requests to `/` (the SPA entry point)
- Loads the `index.html` template from dist
- Injects state into it via a `<script>` tag
- Returns the modified HTML with `Cache-Control: no-cache` headers

**Development Mode** (`fair dev`): No state injection. The frontend calls API endpoints normally.

### State Structure

```typescript
interface FairInitialState {
  // Authentication & User
  auth: {
    isAuthenticated: boolean;
    user: {
      id: string;           // UUID
      name: string;
      email: string;
      role: "admin" | "instructor" | "user";
      capabilities: string[];  // e.g., ["admin", "create_course", ...]
      settings: Record<string, unknown>;  // User settings (camelCase)
      isVerified: boolean;
    } | null;
    // Future: token refresh metadata if needed
  };

  // Platform Features & Configuration
  features: {
    emailEnabled: boolean;
    enforceEmailVerification: boolean;
    // Future: other feature flags
  };

  // Platform Configuration
  platform: {
    deploymentMode: "COMMUNITY" | "ENTERPRISE";
    baseUrl: string;  // e.g., "http://localhost:3000"
    // Future: version, etc.
  };

  // Timestamp for debugging/cache invalidation
  injectedAt: string;  // ISO 8601 timestamp
}
```

## Implementation

### Backend Changes

#### 1. New Helper Module: `src/fair_platform/backend/core/state_injection.py`

```python
from datetime import datetime, timezone
from typing import Optional
from fair_platform.backend.data.models import User
from fair_platform.backend.core.config import (
    get_deployment_mode,
    get_email_enabled,
    get_enforce_email_verification,
    get_base_url,
)
from fair_platform.backend.core.security.permissions import auth_user_payload

def build_initial_state(user: Optional[User] = None) -> dict:
    """
    Build the initial state object to be injected into the frontend.
    
    Args:
        user: The authenticated User model, or None if unauthenticated.
    
    Returns:
        A dict representing FairInitialState.
    """
    auth_user = None
    if user:
        auth_user = auth_user_payload(user)
        # Convert settings to camelCase (already handled in auth_user_payload)
    
    return {
        "auth": {
            "isAuthenticated": user is not None,
            "user": auth_user,
        },
        "features": {
            "emailEnabled": get_email_enabled(),
            "enforceEmailVerification": get_enforce_email_verification(),
        },
        "platform": {
            "deploymentMode": get_deployment_mode(),
            "baseUrl": get_base_url(),
        },
        "injectedAt": datetime.now(timezone.utc).isoformat(),
    }
```

#### 2. Modify `src/fair_platform/backend/main.py`

In the `run()` function, wrap the SPA serving logic to inject state:

```python
import json
from fair_platform.backend.core.state_injection import build_initial_state

def run(host: str = "127.0.0.1", port: int = 8000, headless: bool = False, dev: bool = False):
    if not headless and not dev:  # State injection only in production (fair serve)
        frontend_files = importlib.resources.files("fair_platform.frontend")
        dist_dir = frontend_files / "dist"

        with importlib.resources.as_file(dist_dir) as dist_path:
            # ... existing static file mounts ...
            
            # Read the index.html template once at startup
            index_path = dist_path / "index.html"
            with open(index_path, 'r', encoding='utf-8') as f:
                index_template = f.read()
            
            @app.get("/", include_in_schema=False)
            async def serve_index(request: Request):
                """
                Serve index.html with injected initial state (production only).
                For authenticated requests, extract the user from the JWT token.
                """
                user = None
                token = request.cookies.get("access_token")
                if token:
                    try:
                        # Decode token and fetch user from DB
                        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                        user_id = payload.get("sub")
                        if user_id:
                            db = SessionLocal()
                            try:
                                user = db.get(User, UUID(user_id))
                            finally:
                                db.close()
                    except (JWTError, Exception):
                        # Invalid token; user remains None
                        pass
                
                initial_state = build_initial_state(user)
                state_json = json.dumps(initial_state)
                
                # Inject state into HTML
                html = index_template.replace(
                    '</head>',
                    f'<script id="__FAIR_INITIAL_STATE__" type="application/json">{state_json}</script>\n</head>'
                )
                
                return HTMLResponse(
                    content=html,
                    headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
                )
    
    elif dev:  # Development mode: no state injection, normal SPA serving
        # State injection is skipped; frontend makes normal API calls
        pass
```

#### 3. Necessary Imports

Add to `main.py`:
```python
from fastapi import Request
from fastapi.responses import HTMLResponse
from jose import jwt, JWTError
from fair_platform.backend.data.models import User
from fair_platform.backend.core.state_injection import build_initial_state
from uuid import UUID
```

### Frontend Changes

#### 1. Create `frontend-dev/src/lib/initial-state.ts`

```typescript
export interface FairInitialState {
  auth: {
    isAuthenticated: boolean;
    user: {
      id: string;
      name: string;
      email: string;
      role: "admin" | "instructor" | "user";
      capabilities: string[];
      settings: Record<string, unknown>;
      isVerified: boolean;
    } | null;
  };
  features: {
    emailEnabled: boolean;
    enforceEmailVerification: boolean;
  };
  platform: {
    deploymentMode: "COMMUNITY" | "ENTERPRISE";
    baseUrl: string;
  };
  injectedAt: string;
}

export function getInitialState(): FairInitialState {
  const script = document.getElementById("__FAIR_INITIAL_STATE__");
  
  if (!script || script.textContent === null) {
    throw new Error("Initial state not found in HTML. This may indicate a server-side rendering error.");
  }
  
  try {
    return JSON.parse(script.textContent);
  } catch (error) {
    console.error("Failed to parse initial state:", error);
    throw new Error("Failed to parse initial state from server.");
  }
}
```

#### 2. Update Zustand Auth Store

In `frontend-dev/src/stores/auth-store.ts` (or similar), initialize from injected state:

```typescript
import { getInitialState } from "@/lib/initial-state";

interface AuthState {
  user: FairInitialState["auth"]["user"];
  isAuthenticated: boolean;
  // ... other fields
}

const initialState = getInitialState();

export const useAuthStore = create<AuthState>((set) => ({
  user: initialState.auth.user,
  isAuthenticated: initialState.auth.isAuthenticated,
  // ... other store methods
}));
```

#### 3. Update System/Features Store

In `frontend-dev/src/stores/system-store.ts`:

```typescript
import { getInitialState } from "@/lib/initial-state";

const initialState = getInitialState();

export const useSystemStore = create<SystemState>((set) => ({
  features: initialState.features,
  platform: initialState.platform,
  // ... other store methods
}));
```

#### 4. Skip Redundant API Calls

In initialization code (e.g., app middleware or `main.tsx`), remove or guard:
- Calls to `GET /api/auth/me` on app load (if user is already in store)
- Calls to `GET /api/v1/system/config` on app load

Example guard in a hook:
```typescript
export function useInitializeAuth() {
  const { user, isAuthenticated } = useAuthStore();
  
  // Only fetch if not already initialized from injected state
  if (isAuthenticated && user) {
    return; // Skip API call
  }
  
  // Otherwise, fetch /api/auth/me
  // ...
}
```

## Security Considerations

### 1. JWT Token in Cookie vs. State Injection

- The injected state is computed server-side before response rendering
- User data is derived from the JWT token (if present in cookie or header)
- The injected JSON is part of the HTML; it is **not** secret and **not** a security boundary
- The actual JWT token remains in the cookie (HttpOnly, Secure flags) and is used for subsequent API requests

### 2. No Sensitive Data in Injected State

- **Do not** inject passwords, secret tokens, or API keys
- Current approach is safe: only public user info (name, email, role, capabilities) is included
- Settings field should be validated to ensure no sensitive data

### 3. Tampering Risk

- Browser-resident state can be modified by users/scripts
- Injected state is **informational**; authorization is enforced server-side on each API request
- Backend must always re-validate permissions on writes
- This is identical to the current threat model (localStorage, sessionStorage, etc.)

## Development Mode

In development mode (`fair dev`), state injection is **not applied**. The frontend's bun dev server runs independently (port 3000), and the backend runs on port 8000. The frontend makes normal API calls to:
- `GET /api/auth/me` for auth info
- `GET /api/v1/system/config` for platform features

This keeps the dev experience simple and avoids the complexity of injecting state at build time or modifying the dev server setup. State injection only kicks in when running `fair serve` in production.

## Migration Path

### Phase 1: Implement Injection (No Breaking Changes)

- Add `build_initial_state()` function
- Add state injection middleware to backend
- Frontend reads from injected state if available, falls back to API calls
- Both code paths coexist; no changes required to existing components

### Phase 2: Adopt in Components

- Update stores to hydrate from injected state
- Gradually remove redundant API calls
- Test thoroughly to ensure no regressions

## Extensibility

Future state fields can be added to `FairInitialState`:

```typescript
export interface FairInitialState {
  // ... existing fields ...
  workspace?: {
    id: string;
    name: string;
    // ...
  };
  theme?: {
    mode: "light" | "dark";
    // ...
  };
  experiments?: {
    // Feature flags, A/B tests
  };
}
```

Backend implementation in `build_initial_state()` would simply add the new fields.

## Testing

### Backend Tests

- Unit test `build_initial_state(user=None)` with and without a user
- Unit test state injection middleware with mock users
- Integration test: verify HTML contains valid JSON in the injected script tag

### Frontend Tests

- Unit test `getInitialState()` parsing
- Unit test store initialization from injected state
- Integration test: verify stores are hydrated without API calls during app boot

## Rollout Checklist

- [ ] Implement `build_initial_state()` in backend
- [ ] Update `main.py` to serve index with injected state
- [ ] Test backend state injection in isolation
- [ ] Implement `getInitialState()` helper in frontend
- [ ] Update auth and system stores to read from injected state
- [ ] Test frontend hydration without API calls
- [ ] Update vite dev server config for proxy (if needed)
- [ ] Remove or guard redundant API calls
- [ ] Remove loading states for auth/system info
- [ ] Test e2e: app boots without /api/auth/me and /api/v1/system/config calls
- [ ] Deploy to production and monitor

## Future Enhancements

- Extend injected state with additional runtime features (theme, locale, workspace info)
- Cache invalidation strategy (e.g., set state expiry in headers for browser/CDN caching)
- Integration with analytics (track which features are enabled per deployment)
- Support for custom state fields per deployment via environment variables
