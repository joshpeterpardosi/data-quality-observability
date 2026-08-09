"""Pandera schema for raw.transactions: completeness, uniqueness, validity.

customer_id / product_id existence is a cross-table concern and is checked
separately in src/validation/checks/orphan_fk.py, not here.
"""
import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from src.validation.domain import PAYMENT_METHODS, STATUSES
from src.validation.schemas.base import null_rate_results, schema_check_results

NULL_THRESHOLDS = {"quantity": 0.02, "total_amount": 0.02, "payment_method": 0.25}

REGISTRY = [
    ("transaction_id", "not_nullable"),
    ("transaction_id", "field_uniqueness"),
    ("customer_id", "not_nullable"),
    ("product_id", "not_nullable"),
    ("quantity", "validity_numeric_castable"),
    ("unit_price", "not_nullable"),
    ("unit_price", "validity_numeric_castable"),
    ("total_amount", "validity_numeric_castable"),
    ("transaction_ts", "not_nullable"),
    ("transaction_ts", "validity_timestamp_castable"),
    ("payment_method", "validity_payment_method_isin"),
    ("status", "not_nullable"),
    ("status", "validity_status_isin"),
]


def _numeric_castable_positive(value) -> bool:
    if pd.isna(value):
        return True
    try:
        return float(value) > 0
    except ValueError:
        return False


class TransactionsSchema(pa.DataFrameModel):
    transaction_id: Series[str] = pa.Field(nullable=False, unique=True)
    customer_id: Series[str] = pa.Field(nullable=False)
    product_id: Series[str] = pa.Field(nullable=False)
    quantity: Series[str] = pa.Field(nullable=True)
    unit_price: Series[str] = pa.Field(nullable=False)
    total_amount: Series[str] = pa.Field(nullable=True)
    transaction_ts: Series[str] = pa.Field(nullable=False)
    payment_method: Series[str] = pa.Field(nullable=True)
    status: Series[str] = pa.Field(nullable=False)

    class Config:
        strict = False
        coerce = False

    @pa.check("quantity", name="validity_numeric_castable")
    def quantity_castable(cls, s: Series[str]) -> Series[bool]:
        return s.map(_numeric_castable_positive)

    @pa.check("unit_price", name="validity_numeric_castable")
    def unit_price_castable(cls, s: Series[str]) -> Series[bool]:
        return s.map(_numeric_castable_positive)

    @pa.check("total_amount", name="validity_numeric_castable")
    def total_amount_castable(cls, s: Series[str]) -> Series[bool]:
        return s.map(_numeric_castable_positive)

    @pa.check("transaction_ts", name="validity_timestamp_castable")
    def transaction_ts_castable(cls, s: Series[str]) -> Series[bool]:
        return pd.to_datetime(s, errors="coerce").notna()

    @pa.check("payment_method", name="validity_payment_method_isin")
    def payment_method_isin(cls, s: Series[str]) -> Series[bool]:
        return s.isin(PAYMENT_METHODS)

    @pa.check("status", name="validity_status_isin")
    def status_isin(cls, s: Series[str]) -> Series[bool]:
        return s.isin(STATUSES)


def validate(df: pd.DataFrame):
    results = null_rate_results("transactions", df, NULL_THRESHOLDS)
    schema_results, valid_index = schema_check_results("transactions", df, TransactionsSchema, REGISTRY)
    results.extend(schema_results)
    return results, valid_index
