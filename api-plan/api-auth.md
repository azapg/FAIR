#### 1. The Core Philosophy

* **Internal Trust, Verified Execution:** Extensions are trusted services deployed by platform admins, but they still operate under a "Zero Trust" model regarding user data.
* **Bounded Inherited Authority:** Extensions do not have universal permissions. When an extension makes an API call on behalf of a user, the platform calculates the **Effective Permission** by intersecting three layers:
1. **User RBAC:** What is the human actually allowed to do?
2. **Extension Scopes:** What is this specific extension *capable* of doing globally? (e.g., `read:grades`, `write:grades`, `read:roster`).
3. **Contextual Overrides:** What has the Professor/Admin explicitly disabled for this specific context? (e.g., Professor turns off `write:grades` for their specific course).


* **Decoupled Capabilities:** Authentication dictates *who* the extension is and *what* it is allowed to touch. A separate system (to be designed later) will handle registering *what* the extension does (agents, UI buttons, chatbots).

#### 2. Authentication & Identity

Identity and network location remain decoupled to survive serverless environments, local tunnels, and dynamic IP changes.

* **`EXTENSION_ID`:** The public identifier (e.g., `ext_123abc`). Safe to expose in the UI, database, logs, and frontend payloads to track the origin of actions.
* **`EXTENSION_SECRET`:** The private cryptographic key. Used by the extension as a Bearer token to authenticate inbound API calls to the platform. Used by the platform to HMAC-sign outbound webhook payloads (`X-FAIR-Signature`) so the extension knows the request actually came from your platform.

#### 3. The Permission Resolver (Solving the Overrides)

To address your concerns about professors restricting grading or admins killing a buggy feature, we introduce a **Scope-Based Resolver**.

Every API request from an extension must include the `JOB_ID` or `USER_ID` it is acting on behalf of. The API Gateway evaluates:

```text
Effective Permission = (User's RBAC) ∩ (Admin's Global Extension Scopes) ∩ (Professor's Context Overrides)

```

* **The Admin/IT Control:** When IT installs the extension, they grant it global scopes (e.g., `["read:submissions", "write:grades", "chat"]`). If the grading model goes rogue or gets too expensive, the Admin simply removes `write:grades` from the extension's global profile. The extension is instantly nerfed platform-wide without needing to uninstall it.
* **The Professor Control:** In the course settings, the UI lists active extensions. The professor sees the scopes the extension requested. They can toggle off "Modify Grades." This creates a record in the database: `Course_ID: 101, Ext_ID: 123, Denied_Scopes: ["write:grades"]`. If the extension tries to post a grade, the API rejects it with a `403 Forbidden`.

#### 4. The Admin Setup Flow

1. Admin clicks "Register New Extension" in the dashboard.
2. Platform generates the `EXTENSION_ID` and a high-entropy `EXTENSION_SECRET`.
3. The UI displays the secret **exactly once**.
4. The secret is immediately hashed (bcrypt/Argon2) and only the hash is stored in the FAIR database.
5. The Admin defines the maximum allowed **Scopes** for this extension (e.g., `read:users`, `write:grades`).
6. The Admin drops the credentials into their extension's environment variables.

#### 5. The Connection Handshake (Stripped of Intents)

When an extension boots up, it automatically calls `POST /api/extensions/connect` using its Secret as auth. We remove the hardcoded intents and replace them with purely infrastructural and cryptographic metadata.

**The Payload:**

```json
{
  "extension_id": "ext_123abc",
  "webhook_url": "https://agent.fairgradeproject.org/webhook",
  "healthcheck_url": "https://agent.fairgradeproject.org/health",
  "requested_scopes": ["read:submissions", "write:grades", "chat:interaction"]
}

```

*Note: The platform checks `requested_scopes` against what the Admin actually approved. If the extension asks for `write:grades` but the Admin didn't approve it, the handshake succeeds but returns the restricted scopes in the response so the extension knows its limits.*
