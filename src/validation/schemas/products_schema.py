"""Pandera schema for raw.products: completeness, uniqueness, validity."""
import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from src.validation.domain import CATEGORIES
from src.validation.schemas.base import null_rate_results, schema_check_results

NULL_THRESHOLDS = {"category": 0.20}

REGISTRY = [
    ("product_id", "not_nullable"),
    ("product_id", "field_uniqueness"),
    ("product_name", "not_nullable"),
    ("category", "validity_category_isin"),
    ("price", "not_nullable"),
    ("price", "validity_price_castable"),
]


def _price_castable_positive(value) -> bool:
    if pd.isna(value):
        return True
    try:
        return float(str(value).strip("$")) > 0
    except ValueError:
        return False


class ProductsSchema(pa.DataFrameModel):
    product_id: Series[str] = pa.Field(nullable=False, unique=True)
    product_name: Series[str] = pa.Field(nullable=False)
    category: Series[str] = pa.Field(nullable=True)
    price: Series[str] = pa.Field(nullable=False)

    class Config:
        strict = False
        coerce = False

    @pa.check("category", name="validity_category_isin")
    def category_isin(cls, s: Series[str]) -> Series[bool]:
        return s.isin(CATEGORIES)

    @pa.check("price", name="validity_price_castable")
    def price_castable(cls, s: Series[str]) -> Series[bool]:
        return s.map(_price_castable_positive)


def validate(df: pd.DataFrame):
    results = null_rate_results("products", df, NULL_THRESHOLDS)
    schema_results, valid_index = schema_check_results("products", df, ProductsSchema, REGISTRY)
    results.extend(schema_results)
    return results, valid_index
