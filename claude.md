# Backend — AI Guidance (claude.md)

Purpose
-------
This file documents the constraints and guardrails for using AI to generate or modify code in the **backend** service (Flask API) of SpendWise. It is intended for both human reviewers and automated agents.

Project snapshot
----------------
- Service: SpendWise backend (Flask, REST API)
- Primary files: `backend/app.py`, `backend/api/routes.py`, `backend/models/models.py`, `backend/services/`
- DB: SQLite for local dev, PostgreSQL in production
- AI: NVIDIA Gemma (server-side only)

Non‑negotiable rules (always follow)
-----------------------------------
1. Validation first: all incoming data must be validated by model validators in `backend/models/models.py` (or service-level validators) before any DB writes.
2. Response envelope: every HTTP response must use the envelope `{ ok: true, data: ... }` or `{ ok: false, error: "...", details: {...} }`.
3. Money safety: all monetary values must use Python's `Decimal` type — never `float`.
4. Three‑layer boundary: routes (HTTP parsing) → services (business logic) → models (schema/validation). Business logic must live in `services/`, not in `api/routes.py`.
5. Secrets: API keys, secrets, and credentials MUST only come from environment variables or a secrets manager (never committed, never logged).
6. Errors: business validation should raise `ValidationError` (dict) or `NotFoundError` (string) — follow existing patterns in `backend/services/exceptions.py`.
7. Tests required: any behavior change introduced by AI-generated code must include tests in `backend/tests/` that exercise the new behavior and error paths.
8. Dependency changes: do not add new Python packages without updating `backend/requirements.txt` and adding a reason in the PR.

AI usage policy (what AI agents may/should do)
-------------------------------------------
- Allowed: generate unit tests, boilerplate service functions following existing patterns, documentation (README updates), and small route scaffolding that delegates to the service layer.
- Allowed: suggest refactors that reduce duplication; always include tests and a short migration plan (if schema changes).
- Allowed: generate example API requests/responses for documentation and testing.

AI strict prohibitions
----------------------
- Never embed or return secret keys in generated code or docs.
- Never change authentication/authorization patterns without human approval.
- Never generate raw SQL bypassing SQLAlchemy or the model validators.
- Do not change DB schema (models) without an explicit migration plan (Alembic) and human review.

Prompt template for code generation (recommended)
------------------------------------------------
When asking the AI to implement code, include the following in the prompt:

1. Files to read (list relevant files).
2. Exact change requested and the three‑layer boundary to follow.
3. Tests to add (happy path + at least one error path).
4. Where to update `requirements.txt` (if adding deps).
5. A short checklist of things to verify after generation (run tests, lint, run app).

Example prompt
--------------
"Add a service function `get_user_transactions(account_id, user_id, ...)` in `backend/services/finance.py`. Follow existing service patterns and raise `NotFoundError` or `ValidationError` as appropriate. Add a route in `api/routes.py` that calls the service and returns the envelope. Add tests in `backend/tests/test_transactions.py` covering success and validation failure. Do not modify models. Update `requirements.txt` only if a new package is strictly necessary and document why."

Review checklist (human reviewer)
--------------------------------
 - Run `python -m pytest backend/tests -q` and confirm all tests pass.
 - Confirm no secrets are present in diffs or new files.
 - Confirm response envelope format for new endpoints.
 - Confirm monetary fields use `Decimal` where applicable.
 - Confirm services hold business logic and routes only call services.
 - Confirm `requirements.txt` updated when new dependencies are introduced.

Data privacy & AI prompts
------------------------
- Do not send raw PII-sensitive text or unmasked user personal data to external AI APIs. Aggregate and redact personal data where possible.
- Limit context sent to the model to summaries (e.g., aggregated totals, category counts) rather than full raw transaction texts unless explicitly allowed and reviewed.

Secrets & deployment
--------------------
- Local dev: use `backend/.env` (gitignored) and `python-dotenv` for convenience.
- Production: set secrets in the hosting provider's secret manager (Render, Docker secrets, etc.).
- If a secret is accidentally committed, rotate it immediately and record the incident in the repo's security log.

Sign-off and traceability
-------------------------
All AI-assisted commits must mention "AI-assisted" in the commit or PR description and include a short note of what was reviewed. Keep individual changes small for easier review.
