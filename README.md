# SpendWise — Backend

This document describes the backend service for SpendWise: a Flask-based REST API that powers accounts, transactions, budgets, recurring transactions, and an AI chat endpoint.

**Quick Links**
- App entry: `backend/app.py`
- Models: `backend/models/models.py`
- Services: `backend/services/finance.py`, `backend/services/ai_service.py`
- Routes / HTTP API: `backend/api/routes.py`
- DB init helper: `backend/create_db.py`
- Production WSGI: `gunicorn app:application`
- Dockerfile: `backend/Dockerfile`

---

**Table of Contents**
- Overview
- Tech stack
- Architecture & file layout
- Environment variables
- Local development (install, run, test)
- Database initialization
- API overview (routes)
- Docker (build & run)
- Deploying to Render (brief)
- Production recommendations
- Troubleshooting
- Contributing & license

---

## Overview

The backend is a Flask 3.x application that exposes a JSON REST API under the `/api` prefix. It provides authentication (JWT), CRUD for accounts and transactions, budgets, recurring transaction templates, summary analytics, and AI-backed chat (NVIDIA Gemma 3n integration).

When run locally the app uses SQLite by default (`spendwise.db`). In production you should use a managed PostgreSQL database and set `DATABASE_URL`.

## Tech stack

- Python 3.12
- Flask 3.x
- Flask-SQLAlchemy (SQLAlchemy 2.x)
- python-dotenv (`.env` support)
- requests (for NVIDIA API calls)
- PyJWT for token signing
- pytest / pytest-flask for tests
- Gunicorn for production WSGI server

## Architecture & file layout

- `app.py` — application factory and WSGI `application` object (used by Gunicorn).
- `api/` — Flask blueprint and HTTP route handlers (`api/routes.py`).
- `models/` — SQLAlchemy model definitions and validation logic.
- `services/` — business logic and service functions that routes call.
- `create_db.py` — small helper that creates DB tables within the app context.
- `requirements.txt` — Python dependencies.
- `Dockerfile` — production image instructions.

## Environment variables

Create a `backend/.env` (development) and set at least the following:

```
JWT_SECRET=your_jwt_secret_here
NVIDIA_API_KEY=your_nvidia_api_key_here
DATABASE_URL=sqlite:///spendwise.db    # or a full Postgres URI in production
FLASK_DEBUG=1                           # 1 or 0 (development only)
PORT=5000
```

Notes:
- On Render / Heroku style services set `DATABASE_URL` to the provided Postgres URI. The app will convert `postgres://` to `postgresql://` automatically.
- Never commit `.env` or secrets to source control.

## Local development

1. Create Python virtual environment and install dependencies

```bash
cd backend
python -m venv .venv
.
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate
pip install -r requirements.txt
```

2. Configure environment variables (see above). You can copy `.env.example` if present or create `.env`.

3. Initialize the database

```bash
python create_db.py
```

4. Run the server (development)

```bash
python app.py
# or with FLASK_DEBUG=1
```

5. Run tests

```bash
python -m pytest tests -v
```

## Database initialization

Use `create_db.py` (it runs `db.create_all()` inside an application context). For production DB provisioning use migrations (Alembic) — this project currently uses SQLAlchemy's simple create_all approach.

## API overview

All endpoints are under the `/api` prefix. The most used endpoints:

- Authentication
  - `POST /api/auth/register` — register (returns `{ user, token }`)
  - `POST /api/auth/login` — login (returns `{ user, token }`)
  - `GET /api/auth/me` — get current user (requires Bearer token)

- Accounts
  - `GET /api/accounts` — list accounts
  - `POST /api/accounts` — create account
  - `DELETE /api/accounts/<id>` — delete account

- Transactions
  - `GET /api/accounts/<account_id>/transactions` — list transactions (query params: `category`, `type`, `start`, `end`)
  - `POST /api/accounts/<account_id>/transactions` — create
  - `PATCH /api/accounts/<account_id>/transactions/<tx_id>` — update
  - `DELETE /api/accounts/<account_id>/transactions/<tx_id>` — delete

- Budgets
  - `GET /api/accounts/<account_id>/budgets`
  - `PUT /api/accounts/<account_id>/budgets` — set budget for a category
  - `DELETE /api/accounts/<account_id>/budgets/<category>` — delete

- Recurring transactions
  - `GET /api/accounts/<account_id>/recurring`
  - `POST /api/accounts/<account_id>/recurring`
  - `POST /api/accounts/<account_id>/recurring/process` — materialize overdue recurring transactions

- AI chat
  - `POST /api/accounts/<account_id>/chat` — AI chat with account context
  - `POST /api/chat` — AI chat without account context

All responses adhere to the envelope: `{ ok: true, data: ... }` or `{ ok: false, error: "...", details: {...} }`.

Authentication: All protected endpoints require `Authorization: Bearer <token>` header. Tokens are issued at login/register and verified by services.

## Docker (build & run)

Build the backend image (from repository root):

```bash
# build using backend folder as context
docker build -t spendwise-backend:local -f backend/Dockerfile backend
```

Run the container:

```bash
docker run --rm -p 5000:5000 \
  -e JWT_SECRET=change_me \
  -e NVIDIA_API_KEY=your_key \
  -e DATABASE_URL=sqlite:///spendwise.db \
  spendwise-backend:local
```

For production with PostgreSQL, set `DATABASE_URL` to the full Postgres connection string and ensure the DB is available to the container.

## Deploying to Render

This repository includes `render.yaml` to simplify deployment as a blueprint. Quick steps:

1. Push your repository to GitHub.
2. In Render, create a new service from the `render.yaml` blueprint or create a Web Service and point it at the `backend/` directory.
3. Set environment variables in Render's dashboard: `JWT_SECRET`, `NVIDIA_API_KEY`, `DATABASE_URL` (create a managed Postgres instance on Render and copy its URL).
4. The service uses `gunicorn app:application` (configured in `render.yaml`) — database tables can be created via Render Shell: `python create_db.py`.

## Production recommendations

- Use a managed PostgreSQL instance (do not rely on SQLite in production).
- Add proper DB migrations with Alembic for schema evolution.
- Add monitoring/logging (Sentry / Datadog) and health checks.
- Rotate secrets and store them in the platform secrets manager.

## Troubleshooting

- "Working outside of application context" when running DB commands — use `create_db.py` or run inside `app.app_context()`.
- If `DATABASE_URL` starts with `postgres://` some drivers (SQLAlchemy) require `postgresql://` — this app will auto-rewrite that prefix.

## Contributing

Follow the three-layer boundary:
- Routes (`api/`) — only parse requests and return responses
- Services (`services/`) — business logic
- Models (`models/`) — validation and schema

Run tests locally before pushing changes.

## License

MIT
