"""Pandera schemas against fixture data: completeness, uniqueness, validity."""
import pandas as pd

from src.validation.schemas import customers_schema, products_schema, transactions_schema


def test_customers_valid_row_passes():
    df = pd.DataFrame({
        "customer_id": ["C0001"], "name": ["Ava Tan"], "email": ["ava@mail.com"],
        "signup_date": ["2026-01-01"], "country": ["SG"],
    })
    results, valid_index = customers_schema.validate(df)
    assert all(r.passed for r in results)
    assert list(valid_index) == [0]


def test_customers_duplicate_id_reported_but_not_excluded():
    # duplicate keys are a curation-step dedup concern, not a reason to drop every copy
    df = pd.DataFrame({
        "customer_id": ["C0001", "C0001"], "name": ["Ava", "Ava"], "email": [None, None],
        "signup_date": ["2026-01-01", "2026-01-01"], "country": ["SG", "SG"],
    })
    results, valid_index = customers_schema.validate(df)
    dupe = next(r for r in results if r.check_name == "field_uniqueness")
    assert not dupe.passed
    assert dupe.failed_rows == 2
    assert list(valid_index) == [0, 1]


def test_customers_invalid_country_excluded_from_valid_index():
    df = pd.DataFrame({
        "customer_id": ["C0001"], "name": ["Ava"], "email": ["ava@mail.com"],
        "signup_date": ["2026-01-01"], "country": ["XX"],
    })
    results, valid_index = customers_schema.validate(df)
    country_check = next(r for r in results if r.check_name == "validity_country_isin")
    assert not country_check.passed
    assert list(valid_index) == []


def test_customers_null_email_within_threshold_passes():
    emails = [None] + [f"user{i}@mail.com" for i in range(19)]  # 1/20 = 5%, threshold is 5%
    df = pd.DataFrame({
        "customer_id": [f"C{i:04d}" for i in range(20)],
        "name": ["X"] * 20, "email": emails,
        "signup_date": ["2026-01-01"] * 20, "country": ["SG"] * 20,
    })
    results, _ = customers_schema.validate(df)
    null_rate = next(r for r in results if r.check_name == "null_rate")
    assert null_rate.passed


def test_customers_null_email_over_threshold_fails():
    emails = [None, None] + [f"user{i}@mail.com" for i in range(18)]  # 2/20 = 10%
    df = pd.DataFrame({
        "customer_id": [f"C{i:04d}" for i in range(20)],
        "name": ["X"] * 20, "email": emails,
        "signup_date": ["2026-01-01"] * 20, "country": ["SG"] * 20,
    })
    results, _ = customers_schema.validate(df)
    null_rate = next(r for r in results if r.check_name == "null_rate")
    assert not null_rate.passed
    assert null_rate.failed_rows == 2


def test_products_malformed_price_fails_validity():
    df = pd.DataFrame({
        "product_id": ["P001"], "product_name": ["Widget"], "category": ["home"], "price": ["not-a-price"],
    })
    results, valid_index = products_schema.validate(df)
    price_check = next(r for r in results if r.check_name == "validity_price_castable")
    assert not price_check.passed
    assert list(valid_index) == []


def test_products_dollar_prefixed_price_is_valid():
    df = pd.DataFrame({
        "product_id": ["P001"], "product_name": ["Widget"], "category": ["home"], "price": ["$35.75"],
    })
    results, valid_index = products_schema.validate(df)
    assert all(r.passed for r in results)
    assert list(valid_index) == [0]


def test_products_null_category_is_not_a_validity_failure():
    # nullable=True means Pandera skips null values in the isin Check -- completeness owns this instead
    df = pd.DataFrame({
        "product_id": ["P001"], "product_name": ["Widget"], "category": [None], "price": ["10.00"],
    })
    results, valid_index = products_schema.validate(df)
    category_check = next(r for r in results if r.check_name == "validity_category_isin")
    assert category_check.passed
    assert list(valid_index) == [0]


def test_transactions_valid_row_passes_fk_columns_untouched():
    # customer_id/product_id existence is orphan_fk's job, not the schema's
    df = pd.DataFrame({
        "transaction_id": ["T000001"], "customer_id": ["C9999"], "product_id": ["P999"],
        "quantity": ["2"], "unit_price": ["10.0"], "total_amount": ["20.0"],
        "transaction_ts": ["2026-08-01 10:00:00"], "payment_method": ["cod"], "status": ["completed"],
    })
    results, valid_index = transactions_schema.validate(df)
    assert all(r.passed for r in results)
    assert list(valid_index) == [0]


def test_transactions_invalid_status_excluded():
    df = pd.DataFrame({
        "transaction_id": ["T000001"], "customer_id": ["C0001"], "product_id": ["P001"],
        "quantity": ["2"], "unit_price": ["10.0"], "total_amount": ["20.0"],
        "transaction_ts": ["2026-08-01 10:00:00"], "payment_method": ["cod"], "status": ["shipped"],
    })
    results, valid_index = transactions_schema.validate(df)
    status_check = next(r for r in results if r.check_name == "validity_status_isin")
    assert not status_check.passed
    assert list(valid_index) == []


def test_transactions_negative_quantity_fails_numeric_castable():
    df = pd.DataFrame({
        "transaction_id": ["T000001"], "customer_id": ["C0001"], "product_id": ["P001"],
        "quantity": ["-1"], "unit_price": ["10.0"], "total_amount": ["20.0"],
        "transaction_ts": ["2026-08-01 10:00:00"], "payment_method": ["cod"], "status": ["completed"],
    })
    results, valid_index = transactions_schema.validate(df)
    qty_check = next(r for r in results if r.column_name == "quantity" and r.check_name == "validity_numeric_castable")
    assert not qty_check.passed
    assert list(valid_index) == []
