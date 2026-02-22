---
title: Settings
description: Personalize FAIR for your workflow
---

The platform offers a variety of settings to customize your experience, control notifications, and tailor AI behavior. This page explains each option and how to use it effectively.

## Account and preferences
This section covers settings related to your account and how you interact with the FAIR platform. You can find this section under `ACCOUNT AND PREFERENCES` inside the settings menu.

### Preferences

These options control your personal workspace experience.

<ResponseField name="Theme" type="select" required>
Choose how FAIR looks: `System`, `Light`, or `Dark`.
</ResponseField>

<ResponseField name="Language" type="select" required>
Choose your interface language: `English` or `Spanish`.
</ResponseField>

<ResponseField name="Simple View" type="boolean" required>
When enabled, FAIR uses a denser, more focused layout with less visual clutter.
</ResponseField>

### Notifications

Notification settings let you choose exactly what updates you receive.

| Group | Setting | What you get |
|---|---|---|
| Grading and AI | Batch Completion | Alert when AI finishes grading a full batch. |
| Grading and AI | Low Confidence Flags | Alert when AI is unsure and recommends manual review. |
| Grading and AI | Plagiarism/AI Detection | Alert on high similarity or likely AI-generated patterns. |
| Grading and AI | Token/Quota Limits | Alert when approaching usage or credit limits. |
| Student Activity | New Submissions | Alert when students submit new work. |
| Student Activity | Late Submissions | Alert when work arrives after deadline. |
| Student Activity | Feedback Read | Alert when students open grades or feedback. |
| Student Activity | Regrade Requests | Alert when students dispute grades or request review. |
| Collaboration | Rubric Changes | Alert when shared rubrics are edited. |
| Collaboration | Grade Overrides | Alert when a TA/co-teacher changes an AI-suggested score. |
| Collaboration | New Course Invites | Alert when you are added to a class/group. |
| System and Delivery | Daily Digest | Receive one summary instead of many instant alerts. |
| System and Delivery | Browser Notifications | Receive in-app browser push notifications. |
| System and Delivery | Platform Updates | Receive FAIR feature and maintenance announcements. |

## AI Features
This section covers settings related to assistant behavior and model defaults. You can find this section under `AI FEATURES` inside the settings menu.

### Personalization

Customize how the assistant behaves with you.

<ResponseField name="Chat Personality" type="select" required>
Select the assistant tone: `Default` (balanced), `Professional` (concise/formal), or `Friendly` (warm/encouraging).
</ResponseField>

<ResponseField name="About You (Custom Instructions)" type="string" required>
Add context like your role, program, or grading philosophy so AI responses align better with your workflow.
</ResponseField>

<ResponseField name="Enable Persistent Memory" type="boolean" required>
Allow AI to remember your custom context from **About You** across sessions.
</ResponseField>

### Models

<ResponseField name="Web Search" type="boolean" required>
Allow the assistant to use web search when real-time information is needed.
</ResponseField>

<ResponseField name="Default Model" type="select" required>
Choose which model FAIR uses by default for chat.
</ResponseField>

## Tips

- Start with only essential alerts enabled, then add more as needed.
- Use **Daily Digest** if instant alerts feel noisy.
- Use **Simple View** if you prefer denser screens with less visual clutter.
