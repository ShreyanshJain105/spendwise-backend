from datetime import datetime, timezone, date as date_type
from decimal import Decimal
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

VALID_CATEGORIES = {
    "housing", "food", "transport", "health",
    "entertainment", "shopping", "utilities", "income", "other"
}

VALID_TYPES = {"expense", "income"}

VALID_FREQUENCIES = {"weekly", "monthly", "yearly"}


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    accounts = db.relationship(
        "Account", back_populates="user", cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "created_at": self.created_at.isoformat(),
        }


class Account(db.Model):
    __tablename__ = "accounts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", back_populates="accounts")
    transactions = db.relationship(
        "Transaction", back_populates="account", cascade="all, delete-orphan"
    )
    budgets = db.relationship(
        "Budget", back_populates="account", cascade="all, delete-orphan"
    )
    recurring_transactions = db.relationship(
        "RecurringTransaction", back_populates="account", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {"id": self.id, "name": self.name, "user_id": self.user_id, "created_at": self.created_at.isoformat()}


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    type = db.Column(db.String(10), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    account = db.relationship("Account", back_populates="transactions")

    def to_dict(self):
        return {
            "id": self.id,
            "account_id": self.account_id,
            "amount": str(self.amount),
            "type": self.type,
            "category": self.category,
            "description": self.description,
            "date": self.date.isoformat(),
            "created_at": self.created_at.isoformat(),
        }

    @staticmethod
    def validate_type(value: str) -> str:
        if value not in VALID_TYPES:
            raise ValueError(f"type must be one of {sorted(VALID_TYPES)}")
        return value

    @staticmethod
    def validate_category(value: str) -> str:
        if value not in VALID_CATEGORIES:
            raise ValueError(f"category must be one of {sorted(VALID_CATEGORIES)}")
        return value

    @staticmethod
    def validate_amount(value) -> Decimal:
        try:
            d = Decimal(str(value))
        except Exception:
            raise ValueError("amount must be a valid number")
        if d <= 0:
            raise ValueError("amount must be positive")
        if d > Decimal("999999999.99"):
            raise ValueError("amount exceeds maximum allowed value")
        return d


class Budget(db.Model):
    __tablename__ = "budgets"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    monthly_limit = db.Column(db.Numeric(12, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    account = db.relationship("Account", back_populates="budgets")

    __table_args__ = (
        db.UniqueConstraint("account_id", "category", name="uq_account_category"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "account_id": self.account_id,
            "category": self.category,
            "monthly_limit": str(self.monthly_limit),
            "created_at": self.created_at.isoformat(),
        }


class RecurringTransaction(db.Model):
    __tablename__ = "recurring_transactions"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    type = db.Column(db.String(10), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    frequency = db.Column(db.String(10), nullable=False)
    next_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    account = db.relationship("Account", back_populates="recurring_transactions")

    def to_dict(self):
        return {
            "id": self.id,
            "account_id": self.account_id,
            "amount": str(self.amount),
            "type": self.type,
            "category": self.category,
            "description": self.description,
            "frequency": self.frequency,
            "next_date": self.next_date.isoformat(),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }

    @staticmethod
    def validate_frequency(value: str) -> str:
        if value not in VALID_FREQUENCIES:
            raise ValueError(f"frequency must be one of {sorted(VALID_FREQUENCIES)}")
        return value
