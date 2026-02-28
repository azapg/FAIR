# FAIR API: Communication & Event Routing Specification

The FAIR API is an HTTP-based protocol that transforms the core platform into a scalable event router. In this architecture, the platform acts as a control plane: it registers extensions, routes actions from the UI to the appropriate extension, and pipes the processed data back to the client.

To ensure we "dogfood" our own protocol, the default capabilities of the platform (rubric generation, chatbots, grading) will be packaged as a standalone extension called **FairGrade Core**. This ships alongside the platform, establishing the current state-of-the-art (SOTA) baseline while allowing the community to easily swap it out for their own research and tools.

## 1. The Core Infrastructure: State and Queues

Because HTTP requests are stateless, the platform needs a brain to remember what is currently processing. We handle this via a Job Queue system, abstracted behind an interface so it can run in two modes:

* **Production Mode (Redis):** For actual deployments, we use Redis. Redis acts as the external nervous system. It holds the queue of pending jobs and stores the current state of active jobs. Because it sits outside the Python application, you can spin up 50 Uvicorn workers, and they all share the same state.
* **Local/Dev Mode (`asyncio.Queue`):** For seamless open-source onboarding, we use Python's built-in `asyncio.Queue`. This lives entirely in the memory of a single running Python process. It requires zero setup or external databases, allowing a developer to run FAIR out of the box, though it cannot scale beyond a single worker.

## 2. Client-Platform-Extension Flow

The communication lifecycle follows a strict asynchronous pattern to prevent blocked connections and timeouts during long-running AI tasks.

1. **Registration:** Extensions send a standard HTTP `POST` to the platform upon startup, declaring their URL, intents, and capabilities. The platform stores this registry.
2. **User Action:** A user interacts with the UI (e.g., clicks "Grade"). The client sends a `POST` request to the platform, specifying the payload and the target extension.
3. **Job Creation:** The platform does not process the request directly. It creates a Job ID (e.g., `#job_123`), pushes the payload into the Redis job queue, and immediately returns a `202 Accepted` to the client along with the Job ID.
4. **The Dispatcher:** A background process within the platform (the Dispatcher) constantly monitors the Redis queue. When it sees `#job_123`, it pulls it off the queue, looks up the target extension's webhook URL, and sends a `POST` request to the extension with the job details.
5. **Client Subscription:** The client, having received the Job ID, opens an HTTP `GET` request to the platform's SSE (Server-Sent Events) endpoint: `/api/jobs/123/stream`.

## 3. Streaming Updates (Piping Logs to the UI)

This is where the architecture handles the disconnect between the extension doing the work and the user waiting for the result.

* **Who receives the updates?** As the extension processes the job, it sends `POST` requests containing logs, token streams, or progress updates back to the platform (e.g., `POST /api/jobs/123/updates`). Because the platform is running behind a load balancer, *any* available Uvicorn worker might receive this `POST` request.
* **How do we route it to the right user?** The worker that receives the extension's `POST` request takes that payload and immediately publishes it to a **Redis Pub/Sub channel** named `job_updates_123`.
* **Who keeps track of the SSE?** Meanwhile, a completely different Uvicorn worker might be holding the open SSE connection with the client. That specific worker is subscribed to the `job_updates_123` Redis channel. As soon as the update hits the channel, the worker catches it and flushes it down the HTTP stream to the client.

This design makes the piping incredibly fast and entirely stateless. No worker needs to know about the others; they only talk to Redis.

## 4. Scalability: Surviving Exam Day

This event-driven, webhook-based architecture is designed to horizontally scale under massive load, such as university-wide exam days.

* **Scaling the Platform:** If millions of students are clicking buttons, the platform's Uvicorn servers might get overwhelmed. Because the platform is stateless (relying on Redis), you simply add more Uvicorn containers.
* **Scaling the Dispatcher:** If the queue is filling up faster than jobs are being dispatched, you can run multiple Dispatcher processes using Redis Consumer Groups. This ensures jobs are distributed evenly among dispatchers without duplicating work.
* **Scaling the Extensions:** If `FairGrade Core` is taking too long to generate rubrics, you put the extension behind an HTTP load balancer (like Nginx or an AWS ALB). You can spin up hundreds of identical extension servers. The Dispatcher only ever hits the load balancer's URL, and the load balancer smoothly routes the heavy compute tasks across all available extension nodes.

## 5. Current Implementation Notes (February 27, 2026)

The current codebase implements the first communications slice:
- Job queue abstraction (`local` + `redis`)
- Job APIs (`/api/jobs`)
- Update stream endpoint (SSE)
- Minimal extension registration (`/api/extensions`)
- Dispatcher service

Important current constraints:
- Dispatcher startup is currently controlled by `FAIR_ENABLE_JOB_DISPATCHER` and defaults to `false`.
- This default is intentional while extension authentication/authorization is still pending.
- Extension registry is currently in-memory, so it is not yet shared across multiple API instances.
- Dispatcher retries are basic and do not yet include DLQ/consumer-group level reliability controls.

So, the architecture target is scalable, but only part of that scalability is implemented today.
To reach the full target, we still need:
- shared/persistent extension registry
- extension identity + authz policy
- hardened dispatcher reliability primitives (consumer groups, DLQ, robust retry scheduling)

## 6. Practical Testing Surface (Current)

To validate the communication layer end-to-end today:

1. Start the backend with dispatcher enabled:
   - `FAIR_ENABLE_JOB_DISPATCHER=true fair serve --headless`
2. Start a mock extension:
   - `uv run python scripts/mock_extension.py --platform-url http://127.0.0.1:8000 --id mock.echo --port 9101 --auto-register`
3. Open the frontend Jobs Lab page:
   - `/jobs-lab`
4. Create a job targeting `mock.echo`, then inspect:
   - `/api/jobs/{job_id}` state transitions
   - `/api/jobs/{job_id}/stream` SSE updates

This gives a real platform + extension webhook loop before auth/SDK ergonomics are layered on top.
