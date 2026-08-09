"""Pandera schema for raw.customers: completeness, uniqueness, validity."""
import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from src.validation.domain import COUNTRIES
from src.validation.schemas.base import null_rate_results, schema_check_results

NULL_THRESHOLDS = {"email": 0.05}

REGISTRY = [
    ("customer_id", "not_nullable"),
    ("customer_id", "field_uniqueness"),
    ("name", "not_nullable"),
    ("signup_date", "not_nullable"),
    ("signup_date", "validity_date_castable"),
    ("country", "not_nullable"),
    ("country", "validity_country_isin"),
]


class CustomersSchema(pa.DataFrameModel):
    customer_id: Series[str] = pa.Field(nullable=False, unique=True)
    name: Series[str] = pa.Field(nullable=False)
    email: Series[str] = pa.Field(nullable=True)
    signup_date: Series[str] = pa.Field(nullable=False)
    country: Series[str] = pa.Field(nullable=False)

    class Config:
        strict = False
        coerce = False

    @pa.check("signup_date", name="validity_date_castable")
    def signup_date_castable(cls, s: Series[str]) -> Series[bool]:
        return pd.to_datetime(s, errors="coerce").notna()

    @pa.check("country", name="validity_country_isin")
    def country_isin(cls, s: Series[str]) -> Series[bool]:
        return s.isin(COUNTRIES)


def validate(df: pd.DataFrame):
    results = null_rate_results("customers", df, NULL_THRESHOLDS)
    schema_results, valid_index = schema_check_results("customers", df, CustomersSchema, REGISTRY)
    results.extend(schema_results)
    return results, valid_index
