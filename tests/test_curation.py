"""End-to-end curation gate: dedupe keep-first, orphan-FK exclusion, type cast."""
from src.curation.build_curated import build_curated


def _seed_raw(con):
    con.execute("DELETE FROM raw.transactions")
    con.execute("DELETE FROM raw.products")
    con.execute("DELETE FROM raw.customers")

    con.execute("""
        INSERT INTO raw.customers (customer_id, name, email, signup_date, country) VALUES
        ('C0001', 'Ava Tan', 'ava@mail.com', '2026-01-01', 'SG'),
        ('C0001', 'Ava Tan Dupe', 'ava2@mail.com', '2026-01-02', 'SG')
    """)
    con.execute("""
        INSERT INTO raw.products (product_id, product_name, category, price) VALUES
        ('P001', 'Widget', 'home', '10.00')
    """)
    con.execute("""
        INSERT INTO raw.transactions
            (transaction_id, customer_id, product_id, quantity, unit_price, total_amount,
             transaction_ts, payment_method, status)
        VALUES
        ('T000001', 'C0001', 'P001', '1', '10.00', '10.00', '2026-08-01 10:00:00', 'cod', 'completed'),
        ('T000002', 'C9999', 'P001', '1', '10.00', '10.00', '2026-08-01 11:00:00', 'cod', 'completed')
    """)


def test_duplicate_customer_id_deduped_keep_first(con):
    _seed_raw(con)
    build_curated(con)
    customers = con.execute("SELECT customer_id, name FROM curated.customers").df()
    assert len(customers) == 1
    assert customers.iloc[0]["name"] == "Ava Tan"


def test_orphan_fk_transaction_dropped_from_curated(con):
    _seed_raw(con)
    build_curated(con)
    curated_tx = con.execute("SELECT transaction_id FROM curated.transactions").df()
    assert list(curated_tx["transaction_id"]) == ["T000001"]


def test_curated_price_cast_from_text(con):
    _seed_raw(con)
    build_curated(con)
    price = con.execute("SELECT price FROM curated.products WHERE product_id = 'P001'").fetchone()[0]
    assert float(price) == 10.00
