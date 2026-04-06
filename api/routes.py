import logging
from functools import wraps
from flask import Blueprint, jsonify, request, g
from services import (
    list_accounts, create_account, delete_account,
    list_transactions, create_transaction, update_transaction, delete_transaction,
    get_summary, NotFoundError, ValidationError,
    list_budgets, set_budget, delete_budget,
    list_recurring, create_recurring, delete_recurring, process_recurring,
    get_financial_advice,
    register, login, verify_token, get_user_by_id, AuthError,
)

logger = logging.getLogger(__name__)
bp = Blueprint("api", __name__, url_prefix="/api")


def ok(data, status=200):
    return jsonify({"ok": True, "data": data}), status


def err(message, status, details=None):
    body = {"ok": False, "error": message}
    if details:
        body["details"] = details
    return jsonify(body), status


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return err("Missing or invalid authorization token", 401)
        
        token = auth_header.split(" ")[1]
        try:
            user_id = verify_token(token)
            g.user_id = user_id
            return f(*args, **kwargs)
        except AuthError as e:
            logger.warning("Auth error (verification): %s", e)
            return err(str(e), 401)
        except Exception as e:
            logger.exception("Auth error (unexpected): %s", e)
            return err("Authentication failed", 401)
            
    return decorated


# ── Auth ──────────────────────────────────────────────────────────────────────

@bp.post("/auth/register")
def auth_register():
    body = request.get_json(silent=True) or {}
    try:
        return ok(register(body), 201)
    except ValidationError as e:
        if isinstance(e.args[0], dict):
            return err("Validation failed", 422, details=e.args[0])
        return err(str(e), 422)


@bp.post("/auth/login")
def auth_login():
    body = request.get_json(silent=True) or {}
    try:
        return ok(login(body))
    except (AuthError, ValidationError) as e:
        return err(str(e), 401)


@bp.get("/auth/me")
@require_auth
def auth_me():
    try:
        return ok(get_user_by_id(g.user_id))
    except AuthError as e:
        return err(str(e), 401)


# ── Accounts ──────────────────────────────────────────────────────────────────

@bp.get("/accounts")
@require_auth
def accounts_list():
    return ok(list_accounts(user_id=g.user_id))


@bp.post("/accounts")
@require_auth
def accounts_create():
    body = request.get_json(silent=True) or {}
    try:
        return ok(create_account(body.get("name", ""), user_id=g.user_id), 201)
    except ValidationError as e:
        return err(str(e), 422)


@bp.delete("/accounts/<int:account_id>")
@require_auth
def accounts_delete(account_id):
    try:
        delete_account(account_id, user_id=g.user_id)
        return ok({"deleted": account_id})
    except (NotFoundError, AuthError) as e:
        status = 401 if isinstance(e, AuthError) else 404
        return err(str(e), status)


# ── Transactions ───────────────────────────────────────────────────────────────

@bp.get("/accounts/<int:account_id>/transactions")
@require_auth
def transactions_list(account_id):
    try:
        txs = list_transactions(
            account_id,
            user_id=g.user_id,
            category=request.args.get("category"),
            tx_type=request.args.get("type"),
            start=request.args.get("start"),
            end=request.args.get("end"),
        )
        return ok(txs)
    except (NotFoundError, AuthError) as e:
        status = 401 if isinstance(e, AuthError) else 404
        return err(str(e), status)
    except ValidationError as e:
        return err(str(e), 422)


@bp.post("/accounts/<int:account_id>/transactions")
@require_auth
def transactions_create(account_id):
    body = request.get_json(silent=True) or {}
    try:
        return ok(create_transaction(account_id, body, user_id=g.user_id), 201)
    except (NotFoundError, AuthError) as e:
        status = 401 if isinstance(e, AuthError) else 404
        return err(str(e), status)
    except ValidationError as e:
        return err("Validation failed", 422, details=e.args[0])


@bp.patch("/accounts/<int:account_id>/transactions/<int:tx_id>")
@require_auth
def transactions_update(account_id, tx_id):
    body = request.get_json(silent=True) or {}
    try:
        return ok(update_transaction(account_id, tx_id, body, user_id=g.user_id))
    except (NotFoundError, AuthError) as e:
        status = 401 if isinstance(e, AuthError) else 404
        return err(str(e), status)
    except ValidationError as e:
        return err("Validation failed", 422, details=e.args[0])


@bp.delete("/accounts/<int:account_id>/transactions/<int:tx_id>")
@require_auth
def transactions_delete(account_id, tx_id):
    try:
        delete_transaction(account_id, tx_id, user_id=g.user_id)
        return ok({"deleted": tx_id})
    except (NotFoundError, AuthError) as e:
        status = 401 if isinstance(e, AuthError) else 404
        return err(str(e), status)


# ── Budgets ───────────────────────────────────────────────────────────────────

@bp.get("/accounts/<int:account_id>/budgets")
@require_auth
def budgets_list(account_id):
    try:
        return ok(list_budgets(account_id, user_id=g.user_id))
    except (NotFoundError, AuthError) as e:
        status = 401 if isinstance(e, AuthError) else 404
        return err(str(e), status)


@bp.put("/accounts/<int:account_id>/budgets")
@require_auth
def budgets_set(account_id):
    body = request.get_json(silent=True) or {}
    try:
        return ok(set_budget(account_id, body, user_id=g.user_id), 201)
    except (NotFoundError, AuthError) as e:
        status = 401 if isinstance(e, AuthError) else 404
        return err(str(e), status)
    except ValidationError as e:
        if isinstance(e.args[0], dict):
            return err("Validation failed", 422, details=e.args[0])
        return err(str(e), 422)


@bp.delete("/accounts/<int:account_id>/budgets/<category>")
@require_auth
def budgets_delete(account_id, category):
    try:
        delete_budget(account_id, category, user_id=g.user_id)
        return ok({"deleted": category})
    except (NotFoundError, AuthError) as e:
        status = 401 if isinstance(e, AuthError) else 404
        return err(str(e), status)


# ── Recurring Transactions ────────────────────────────────────────────────────

@bp.get("/accounts/<int:account_id>/recurring")
@require_auth
def recurring_list(account_id):
    try:
        return ok(list_recurring(account_id, user_id=g.user_id))
    except (NotFoundError, AuthError) as e:
        status = 401 if isinstance(e, AuthError) else 404
        return err(str(e), status)


@bp.post("/accounts/<int:account_id>/recurring")
@require_auth
def recurring_create(account_id):
    body = request.get_json(silent=True) or {}
    try:
        return ok(create_recurring(account_id, body, user_id=g.user_id), 201)
    except (NotFoundError, AuthError) as e:
        status = 401 if isinstance(e, AuthError) else 404
        return err(str(e), status)
    except ValidationError as e:
        if isinstance(e.args[0], dict):
            return err("Validation failed", 422, details=e.args[0])
        return err(str(e), 422)


@bp.delete("/accounts/<int:account_id>/recurring/<int:recurring_id>")
@require_auth
def recurring_delete(account_id, recurring_id):
    try:
        delete_recurring(account_id, recurring_id, user_id=g.user_id)
        return ok({"deleted": recurring_id})
    except (NotFoundError, AuthError) as e:
        status = 401 if isinstance(e, AuthError) else 404
        return err(str(e), status)


@bp.post("/accounts/<int:account_id>/recurring/process")
@require_auth
def recurring_process(account_id):
    try:
        created = process_recurring(account_id, user_id=g.user_id)
        return ok({"processed": len(created), "transactions": created})
    except (NotFoundError, AuthError) as e:
        status = 401 if isinstance(e, AuthError) else 404
        return err(str(e), status)


# ── AI Chat ───────────────────────────────────────────────────────────────────

@bp.post("/accounts/<int:account_id>/chat")
@require_auth
def chat_with_context(account_id):
    """AI chat with account-specific financial context."""
    body = request.get_json(silent=True) or {}
    message = (body.get("message") or "").strip()
    if not message:
        return err("message is required", 422)

    try:
        summary = get_summary(account_id, user_id=g.user_id)
    except (NotFoundError, AuthError) as e:
        status = 401 if isinstance(e, AuthError) else 404
        return err(str(e), status)

    try:
        reply = get_financial_advice(message, summary=summary)
        return ok({"reply": reply})
    except RuntimeError as e:
        logger.error("AI chat error: %s", e)
        return err(str(e), 503)


@bp.post("/chat")
@require_auth
def chat_general():
    """AI chat without account context — general financial advice."""
    body = request.get_json(silent=True) or {}
    message = (body.get("message") or "").strip()
    if not message:
        return err("message is required", 422)

    try:
        reply = get_financial_advice(message)
        return ok({"reply": reply})
    except RuntimeError as e:
        logger.error("AI chat error: %s", e)
        return err(str(e), 503)


# ── Analytics ─────────────────────────────────────────────────────────────────

@bp.get("/accounts/<int:account_id>/summary")
@require_auth
def account_summary(account_id):
    try:
        return ok(get_summary(account_id, user_id=g.user_id))
    except (NotFoundError, AuthError) as e:
        status = 401 if isinstance(e, AuthError) else 404
        return err(str(e), status)
