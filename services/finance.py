from datetime import date as date_type, timedelta
from decimal import Decimal
from typing import Optional
from models import db, Account, Transaction, Budget, RecurringTransaction


from .exceptions import NotFoundError, AuthError, ValidationError


def _parse_date(raw: str) -> date_type:
    try:
        return date_type.fromisoformat(raw)
    except (ValueError, TypeError):
        raise ValidationError("date must be in YYYY-MM-DD format")


def get_or_404(model, record_id: int):
    obj = db.session.get(model, record_id)
    if obj is None:
        raise NotFoundError(f"{model.__name__} {record_id} not found")
    return obj


def get_account_or_404(account_id: int, user_id: int = None):
    """
    Fetch an account and verify ownership if user_id is provided.
    This is the primary security boundary.
    """
    account = get_or_404(Account, account_id)
    if user_id is not None and account.user_id is not None and account.user_id != user_id:
        # Note: If account.user_id is None, it's a legacy global account.
        # Once migration is complete, we can enforce user_id is not None.
        raise AuthError("You do not have permission to access this account")
    return account


# ── Accounts ──────────────────────────────────────────────────────────────────

def list_accounts(user_id: int = None) -> list[dict]:
    q = Account.query
    if user_id is not None:
        q = q.filter_by(user_id=user_id)
    return [a.to_dict() for a in q.order_by(Account.name).all()]


def create_account(name: str, user_id: int = None) -> dict:
    name = (name or "").strip()
    if not name:
        raise ValidationError("name is required")
    if len(name) > 100:
        raise ValidationError("name must be ≤ 100 characters")
    account = Account(name=name, user_id=user_id)
    db.session.add(account)
    db.session.commit()
    return account.to_dict()


def delete_account(account_id: int, user_id: int = None) -> None:
    account = get_account_or_404(account_id, user_id)
    db.session.delete(account)
    db.session.commit()


# ── Transactions ───────────────────────────────────────────────────────────────

def list_transactions(
    account_id: int,
    user_id: int = None,
    category: Optional[str] = None,
    tx_type: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> list[dict]:
    get_account_or_404(account_id, user_id)
    q = Transaction.query.filter_by(account_id=account_id)
    if category:
        q = q.filter(Transaction.category == category)
    if tx_type:
        q = q.filter(Transaction.type == tx_type)
    if start:
        q = q.filter(Transaction.date >= _parse_date(start))
    if end:
        q = q.filter(Transaction.date <= _parse_date(end))
    return [t.to_dict() for t in q.order_by(Transaction.date.desc()).all()]


def create_transaction(account_id: int, data: dict, user_id: int = None) -> dict:
    get_account_or_404(account_id, user_id)

    errors = {}

    try:
        amount = Transaction.validate_amount(data.get("amount"))
    except (ValueError, KeyError) as e:
        errors["amount"] = str(e)
        amount = None

    try:
        tx_type = Transaction.validate_type(data.get("type", ""))
    except ValueError as e:
        errors["type"] = str(e)
        tx_type = None

    try:
        category = Transaction.validate_category(data.get("category", ""))
    except ValueError as e:
        errors["category"] = str(e)
        category = None

    description = (data.get("description") or "").strip()
    if not description:
        errors["description"] = "description is required"
    elif len(description) > 255:
        errors["description"] = "description must be ≤ 255 characters"

    try:
        date = _parse_date(data.get("date", ""))
    except ValidationError as e:
        errors["date"] = str(e)
        date = None

    if errors:
        raise ValidationError(errors)

    tx = Transaction(
        account_id=account_id,
        amount=amount,
        type=tx_type,
        category=category,
        description=description,
        date=date,
    )
    db.session.add(tx)
    db.session.commit()
    return tx.to_dict()


def update_transaction(account_id: int, tx_id: int, data: dict, user_id: int = None) -> dict:
    get_account_or_404(account_id, user_id)
    tx = get_or_404(Transaction, tx_id)
    if tx.account_id != account_id:
        raise NotFoundError(f"Transaction {tx_id} not found in account {account_id}")

    errors = {}

    if "amount" in data:
        try:
            tx.amount = Transaction.validate_amount(data["amount"])
        except ValueError as e:
            errors["amount"] = str(e)

    if "type" in data:
        try:
            tx.type = Transaction.validate_type(data["type"])
        except ValueError as e:
            errors["type"] = str(e)

    if "category" in data:
        try:
            tx.category = Transaction.validate_category(data["category"])
        except ValueError as e:
            errors["category"] = str(e)

    if "description" in data:
        desc = data["description"].strip()
        if not desc:
            errors["description"] = "description is required"
        elif len(desc) > 255:
            errors["description"] = "description must be ≤ 255 characters"
        else:
            tx.description = desc

    if "date" in data:
        try:
            tx.date = _parse_date(data["date"])
        except ValidationError as e:
            errors["date"] = str(e)

    if errors:
        raise ValidationError(errors)

    db.session.commit()
    return tx.to_dict()


def delete_transaction(account_id: int, tx_id: int, user_id: int = None) -> None:
    get_account_or_404(account_id, user_id)
    tx = get_or_404(Transaction, tx_id)
    if tx.account_id != account_id:
        raise NotFoundError(f"Transaction {tx_id} not found in account {account_id}")
    db.session.delete(tx)
    db.session.commit()


# ── Budgets ───────────────────────────────────────────────────────────────────

def list_budgets(account_id: int, user_id: int = None) -> list[dict]:
    """List all budgets for an account."""
    get_account_or_404(account_id, user_id)
    budgets = Budget.query.filter_by(account_id=account_id).order_by(Budget.category).all()
    return [b.to_dict() for b in budgets]


def set_budget(account_id: int, data: dict, user_id: int = None) -> dict:
    """Create or update a budget for a category."""
    get_account_or_404(account_id, user_id)

    errors = {}

    category = (data.get("category") or "").strip()
    try:
        Transaction.validate_category(category)
    except ValueError as e:
        errors["category"] = str(e)

    try:
        monthly_limit = Transaction.validate_amount(data.get("monthly_limit"))
    except (ValueError, KeyError) as e:
        errors["monthly_limit"] = str(e)
        monthly_limit = None

    if errors:
        raise ValidationError(errors)

    # Upsert: find existing or create
    existing = Budget.query.filter_by(
        account_id=account_id, category=category
    ).first()

    if existing:
        existing.monthly_limit = monthly_limit
        db.session.commit()
        return existing.to_dict()

    budget = Budget(
        account_id=account_id,
        category=category,
        monthly_limit=monthly_limit,
    )
    db.session.add(budget)
    db.session.commit()
    return budget.to_dict()


def delete_budget(account_id: int, category: str, user_id: int = None) -> None:
    """Delete a budget for a category."""
    get_account_or_404(account_id, user_id)
    budget = Budget.query.filter_by(account_id=account_id, category=category).first()
    if not budget:
        raise NotFoundError(f"Budget for '{category}' not found")
    db.session.delete(budget)
    db.session.commit()


def get_budget_status(account_id: int, user_id: int = None) -> list[dict]:
    """Calculate budget utilization for the current month."""
    today = date_type.today()
    first_of_month = today.replace(day=1)

    get_account_or_404(account_id, user_id)
    budgets = Budget.query.filter_by(account_id=account_id).all()
    if not budgets:
        return []

    # Get all expense transactions for the current month
    month_txs = Transaction.query.filter(
        Transaction.account_id == account_id,
        Transaction.type == "expense",
        Transaction.date >= first_of_month,
        Transaction.date <= today,
    ).all()

    # Aggregate spending by category
    spent_by_cat: dict[str, Decimal] = {}
    for tx in month_txs:
        spent_by_cat[tx.category] = spent_by_cat.get(tx.category, Decimal("0")) + Decimal(str(tx.amount))

    result = []
    for b in budgets:
        limit = Decimal(str(b.monthly_limit))
        spent = spent_by_cat.get(b.category, Decimal("0"))
        remaining = limit - spent
        pct = int((spent / limit) * 100) if limit > 0 else 0
        result.append({
            "category": b.category,
            "limit": str(limit),
            "spent_this_month": str(spent),
            "remaining": str(remaining),
            "percentage": min(pct, 100),
        })

    return sorted(result, key=lambda x: -x["percentage"])


# ── Recurring Transactions ────────────────────────────────────────────────────

def list_recurring(account_id: int, user_id: int = None) -> list[dict]:
    """List all recurring transaction templates for an account."""
    get_account_or_404(account_id, user_id)
    recs = RecurringTransaction.query.filter_by(
        account_id=account_id
    ).order_by(RecurringTransaction.next_date).all()
    return [r.to_dict() for r in recs]


def create_recurring(account_id: int, data: dict, user_id: int = None) -> dict:
    """Create a new recurring transaction template."""
    get_account_or_404(account_id, user_id)

    errors = {}

    try:
        amount = Transaction.validate_amount(data.get("amount"))
    except (ValueError, KeyError) as e:
        errors["amount"] = str(e)
        amount = None

    try:
        tx_type = Transaction.validate_type(data.get("type", ""))
    except ValueError as e:
        errors["type"] = str(e)
        tx_type = None

    try:
        category = Transaction.validate_category(data.get("category", ""))
    except ValueError as e:
        errors["category"] = str(e)
        category = None

    description = (data.get("description") or "").strip()
    if not description:
        errors["description"] = "description is required"
    elif len(description) > 255:
        errors["description"] = "description must be ≤ 255 characters"

    try:
        frequency = RecurringTransaction.validate_frequency(data.get("frequency", ""))
    except ValueError as e:
        errors["frequency"] = str(e)
        frequency = None

    try:
        next_date = _parse_date(data.get("next_date", ""))
    except ValidationError as e:
        errors["next_date"] = str(e)
        next_date = None

    if errors:
        raise ValidationError(errors)

    rec = RecurringTransaction(
        account_id=account_id,
        amount=amount,
        type=tx_type,
        category=category,
        description=description,
        frequency=frequency,
        next_date=next_date,
        is_active=True,
    )
    db.session.add(rec)
    db.session.commit()
    return rec.to_dict()


def delete_recurring(account_id: int, recurring_id: int, user_id: int = None) -> None:
    """Delete a recurring transaction template."""
    get_account_or_404(account_id, user_id)
    rec = get_or_404(RecurringTransaction, recurring_id)
    if rec.account_id != account_id:
        raise NotFoundError(f"Recurring {recurring_id} not found in account {account_id}")
    db.session.delete(rec)
    db.session.commit()


def _advance_date(current: date_type, frequency: str) -> date_type:
    """Calculate the next occurrence date based on frequency."""
    if frequency == "weekly":
        return current + timedelta(weeks=1)
    elif frequency == "monthly":
        month = current.month + 1
        year = current.year
        if month > 12:
            month = 1
            year += 1
        day = min(current.day, 28)  # safe day for all months
        return date_type(year, month, day)
    elif frequency == "yearly":
        day = min(current.day, 28)
        return date_type(current.year + 1, current.month, day)
    return current


def process_recurring(account_id: int, user_id: int = None) -> list[dict]:
    """Materialize all due recurring transactions.

    Creates actual Transaction records for all active recurring templates
    whose next_date is today or in the past.
    """
    get_account_or_404(account_id, user_id)
    today = date_type.today()

    due = RecurringTransaction.query.filter(
        RecurringTransaction.account_id == account_id,
        RecurringTransaction.is_active == True,
        RecurringTransaction.next_date <= today,
    ).all()

    created = []
    for rec in due:
        tx = Transaction(
            account_id=account_id,
            amount=rec.amount,
            type=rec.type,
            category=rec.category,
            description=f"[Recurring] {rec.description}",
            date=rec.next_date,
        )
        db.session.add(tx)
        created.append(tx)
        rec.next_date = _advance_date(rec.next_date, rec.frequency)

    db.session.commit()
    return [t.to_dict() for t in created]


# ── Analytics ─────────────────────────────────────────────────────────────────

def get_summary(account_id: int, user_id: int = None) -> dict:
    get_account_or_404(account_id, user_id)
    txs = Transaction.query.filter_by(account_id=account_id).all()

    total_income = sum(Decimal(str(t.amount)) for t in txs if t.type == "income")
    total_expense = sum(Decimal(str(t.amount)) for t in txs if t.type == "expense")

    by_category: dict[str, Decimal] = {}
    for t in txs:
        if t.type == "expense":
            by_category[t.category] = by_category.get(t.category, Decimal("0")) + Decimal(str(t.amount))

    # Monthly trend: last 6 months
    monthly_trend = _compute_monthly_trend(txs)

    return {
        "total_income": str(total_income),
        "total_expense": str(total_expense),
        "balance": str(total_income - total_expense),
        "by_category": {k: str(v) for k, v in sorted(by_category.items(), key=lambda x: -x[1])},
        "transaction_count": len(txs),
        "budget_status": get_budget_status(account_id, user_id),
        "monthly_trend": monthly_trend,
    }


def _compute_monthly_trend(txs: list) -> list[dict]:
    """Compute income/expense totals for the last 6 months."""
    today = date_type.today()
    months = []
    for i in range(5, -1, -1):
        month = today.month - i
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        months.append((year, month))

    trend = []
    for year, month in months:
        month_income = sum(
            Decimal(str(t.amount)) for t in txs
            if t.type == "income" and t.date.year == year and t.date.month == month
        )
        month_expense = sum(
            Decimal(str(t.amount)) for t in txs
            if t.type == "expense" and t.date.year == year and t.date.month == month
        )
        trend.append({
            "month": f"{year}-{month:02d}",
            "income": str(month_income),
            "expense": str(month_expense),
        })

    return trend
