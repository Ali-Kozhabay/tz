## Backend Core (FastAPI)

Async FastAPI backend that covers auth, role-based access, courses/progress API, invite-driven membership, S3 storage signing, Redis-backed realtime chat, SMTP notifications, and JSON logging with `request_id`.

### Stack
- FastAPI + Uvicorn
- SQLAlchemy (async) + Alembic + PostgreSQL (dev via docker compose)
- Redis (rate limits, chat pub/sub, RQ queue)
- MinIO/S3 via boto3 presigned URLs
- MailHog/SMTP for dev notifications
- SlowAPI rate limiting, structlog JSON logs

### Getting Started
1. **Install dependencies**
   ```bash
   poetry install
   ```
2. **Bootstrap infrastructure**
   ```bash
   cp .env.example .env
   docker compose up -d
   ```
3. **Create database schema (PostgreSQL async via `postgresql+asyncpg://`)**
   ```bash
   poetry run alembic upgrade head
   ```
4. **Run the API**
   ```bash
   poetry run uvicorn app:app --reload
   ```
5. **Run background notifications worker (optional)**
   ```bash
   poetry run rq worker notifications
   ```

### Environment
Key variables (see `.env.example`). The app defaults to PostgreSQL via `postgresql+asyncpg://` DSNs:

- `DATABASE_URL=postgresql+asyncpg://app:app@localhost:5432/app`
- `REDIS_URL=redis://localhost:6379/0`
- `JWT_SECRET=dev-secret`
- `SMTP_HOST=localhost / SMTP_PORT=1025` (MailHog)
- `S3_ENDPOINT=http://localhost:9000` etc.

### API Overview
- `POST /auth/register` – register + receive JWT pair (access 15m, refresh 7d).
- `POST /auth/login` / `POST /auth/refresh`.
- `GET /courses?visibility=...` – paginated listing (guest sees public, member/admin sees all).
- `GET /courses/{slug}` – course detail + published lessons (lesson URLs presigned for 5 minutes).
- `POST /admin/courses` / `POST /admin/lessons` – admin-only management.
- `POST /progress/mark` – idempotent progress updates.
- `GET /storage/sign` – presign download (authenticated), `/storage/sign-upload` for admins.
- `POST /admin/invites` – create one-time member invites; `POST /invites/redeem` upgrades role.
- `WS /ws/channels/{slug}?token=ACCESS` – realtime chat with Redis pub/sub, soft delete, pins, readonly channels (announcements).

### Chat Protocol
Client sends JSON frames:
```json
{ "type": "message.create", "payload": { "text": "hello", "parent_id": null } }
{ "type": "message.delete", "payload": { "id": 10 } }
{ "type": "message.pin", "payload": { "id": 10 } }
```
Server broadcasts events (`message.created`, `message.deleted`, `message.pinned`) to every subscriber. Read-only channels reject non-admin posts. Rate limiting (per Redis) protects spam.

### Notifications
RQ queue (`notifications`) enqueues welcome mail, invite redemption, and weekly digest jobs. Dev SMTP is MailHog (`http://localhost:8025`). Templates live under `app/templates/emails/`.

### Logging & Security
- Structured JSON logs with `request_id`.
- SlowAPI-based rate limits on auth/storage/progress endpoints.
- JWT guards + role dependency (`guest/user/member/admin` order).

### Testing
```bash
poetry run pytest
```
Sample tests cover hashing/JWT primitives and storage signing TTL. Extend with integration/E2E flows using `httpx` + `websockets`.

### Alembic
- `poetry run alembic revision --autogenerate -m "..."` to create migrations.
- `poetry run alembic upgrade head` / `downgrade -1`.

### Useful curl
```bash
# Register
curl -X POST http://localhost:8000/auth/register -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"Secret123"}'

# List courses
curl http://localhost:8000/courses
```

