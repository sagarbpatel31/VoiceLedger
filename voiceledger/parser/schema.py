"""Pydantic schemas for VoiceLedger transactions."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


TransactionType = Literal["sale", "expense", "customer_credit", "customer_payment", "unknown"]
PaymentStatus = Literal["paid", "unpaid", "credit", "unknown"]


class Transaction(BaseModel):
    """Structured bookkeeping record parsed from a user's note."""

    transaction_type: TransactionType = Field(
        default="unknown",
        description="Business classification for the transaction.",
    )
    item: str | None = Field(default=None, description="Product or expense item.")
    quantity: float | None = Field(default=None, ge=0)
    unit_price: float | None = Field(default=None, ge=0)
    amount: float | None = Field(default=None, ge=0)
    customer: str | None = Field(default=None)
    payment_status: PaymentStatus = Field(default="unknown")
    notes: str = Field(default="")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("item", "customer", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: object) -> str | None:
        """Trim optional text fields and convert blanks to None."""
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value: object) -> str:
        """Store notes as a stripped string."""
        if value is None:
            return ""
        return str(value).strip()

    @model_validator(mode="after")
    def derive_amount(self) -> "Transaction":
        """Derive amount from quantity and unit price when possible."""
        if self.amount is None and self.quantity is not None and self.unit_price is not None:
            self.amount = round(self.quantity * self.unit_price, 2)
        return self
