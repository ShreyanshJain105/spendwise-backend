# Backend — Agents Guidance (agents.md)

Before starting any task
------------------------
1. Read `backend/claude.md` fully.
2. Inspect the specific files related to the task (routes, services, models).
3. Confirm which layer the change affects (route, service, or model).
4. State the tests you will add or update before coding.

What AI agents may do
---------------------
- Implement service-layer functions that follow existing patterns.
- Add unit tests for new behavior and failure cases.
- Create route scaffolding that delegates to the service layer.
- Update documentation and README fragments.

What AI agents must NOT do
-------------------------
- Do not modify secrets, credentials, or add them to code or docs.
- Do not perform DB schema migrations without a documented plan and human approval.
- Do not add or remove production-critical dependencies without justification.
- Do not change authentication logic or authorization checks.

Prompting patterns that work
---------------------------
- Provide a short bullet list: files to read, desired change, tests to write, constraints to follow.
- Ask for minimal, well-scoped diffs and explicit tests.

Prompt patterns to avoid
------------------------
- Vague requests like "make it faster" or "rewrite backend" without acceptance criteria.
- Requests that imply bypassing validation or security checks.

Testing & verification
----------------------
Run these commands locally and include results in the PR description:

```bash
cd backend
python -m pytest tests -q
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('NVIDIA_API_KEY' in os.environ)"
```

Review checklist for maintainers
-------------------------------
- Tests: all new and existing tests pass.
- Secrets: verify no secrets in diffs.
- Boundary: the change respects routes → services → models separation.
- Envelope: API responses follow `{ ok, data }` or `{ ok, error, details }`.
- Money: monetary values use `Decimal`.
- Documentation: README or changelog updated when behavior changes.

Commit & PR guidance
--------------------
- Make small, incremental commits. Each commit should be one logical change with tests.
- PR description must include:
  - Summary of the change
  - Which files were changed
  - Test commands & results
  - Whether the change was AI-assisted (yes/no) and what was reviewed

Incident response
-----------------
If an API key or secret is exposed, rotate it immediately and add a note to the repo's security log. Notify maintainers and include remediation steps in the PR.

Where to place service-scoped guidance
-------------------------------------
Keep global project guidance at the repository root (`claude.md`, `agents.md`). For service-specific constraints, add short files in each service folder (this file is the backend's local guidance).
