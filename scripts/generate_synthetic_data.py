"""Generate messy synthetic e-commerce CSVs into data/raw/.

Injects the defects the DQ platform is meant to catch: nulls, duplicate
keys, orphan FKs, stale/malformed values, a volume anomaly spike.
Stdlib only, seeded for reproducibility.
"""
import csv
import os
import random
from datetime import datetime, timedelta

random.seed(42)

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
os.makedirs(OUT_DIR, exist_ok=True)

FIRST_NAMES = ["Ava", "Liam", "Mia", "Noah", "Zoe", "Kai", "Leo", "Nina", "Sam", "Ivy"]
LAST_NAMES = ["Tan", "Reyes", "Kim", "Silva", "Nguyen", "Park", "Cruz", "Lopez", "Ito", "Diaz"]
COUNTRIES = ["ID", "SG", "MY", "PH", "VN", "TH"]
CATEGORIES = ["electronics", "apparel", "home", "beauty", "sports", None]
PAYMENT_METHODS = ["credit_card", "e_wallet", "bank_transfer", "cod", None]
STATUSES = ["completed", "refunded", "cancelled", "pending"]

N_CUSTOMERS = 500
N_PRODUCTS = 150
N_TRANSACTIONS = 8000
TODAY = datetime(2026, 8, 9)


def gen_customers():
    rows = []
    for i in range(1, N_CUSTOMERS + 1):
        cid = f"C{i:04d}"
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        email = None if random.random() < 0.04 else f"{name.lower().replace(' ', '.')}@mail.com"
        signup = TODAY - timedelta(days=random.randint(1, 1000))
        rows.append([cid, name, email, signup.date().isoformat(), random.choice(COUNTRIES)])
    # inject duplicate customer_id rows
    for _ in range(6):
        rows.append(random.choice(rows[:N_CUSTOMERS]).copy())
    return rows


def gen_products():
    rows = []
    for i in range(1, N_PRODUCTS + 1):
        pid = f"P{i:03d}"
        price = round(random.uniform(5, 500), 2)
        # a few malformed prices (currency symbol baked into the string)
        price_str = f"${price}" if random.random() < 0.03 else str(price)
        rows.append([pid, f"Product {i}", random.choice(CATEGORIES), price_str])
    for _ in range(4):
        rows.append(random.choice(rows[:N_PRODUCTS]).copy())
    return rows


def gen_transactions(customer_ids, product_ids):
    rows = []
    # freshness defect: no transaction newer than 5 days ago
    latest = TODAY - timedelta(days=5)
    earliest = latest - timedelta(days=60)

    for i in range(1, N_TRANSACTIONS + 1):
        tid = f"T{i:06d}"
        # ~3% orphan FKs
        cid = "C9999" if random.random() < 0.03 else random.choice(customer_ids)
        pid = "P999" if random.random() < 0.03 else random.choice(product_ids)
        qty = "" if random.random() < 0.01 else random.randint(1, 5)
        unit_price = round(random.uniform(5, 500), 2)
        total = "" if qty == "" else round(unit_price * qty, 2)

        day_offset = random.randint(0, (latest - earliest).days)
        ts = earliest + timedelta(days=day_offset, seconds=random.randint(0, 86399))

        rows.append([
            tid, cid, pid, qty, unit_price, total,
            ts.isoformat(sep=" "), random.choice(PAYMENT_METHODS), random.choice(STATUSES),
        ])

    # anomaly: volume spike on one day (10x normal daily count)
    spike_day = earliest + timedelta(days=30)
    for j in range(2000):
        i = N_TRANSACTIONS + j + 1
        cid = random.choice(customer_ids)
        pid = random.choice(product_ids)
        qty = random.randint(1, 5)
        unit_price = round(random.uniform(5, 500), 2)
        ts = spike_day + timedelta(seconds=random.randint(0, 86399))
        rows.append([
            f"T{i:06d}", cid, pid, qty, unit_price, round(unit_price * qty, 2),
            ts.isoformat(sep=" "), random.choice(PAYMENT_METHODS), random.choice(STATUSES),
        ])

    # duplicate transaction_id rows
    for _ in range(10):
        rows.append(random.choice(rows[:N_TRANSACTIONS]).copy())
    return rows


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main():
    customers = gen_customers()
    products = gen_products()
    transactions = gen_transactions(
        [r[0] for r in customers[:N_CUSTOMERS]],
        [r[0] for r in products[:N_PRODUCTS]],
    )

    write_csv(os.path.join(OUT_DIR, "customers.csv"),
              ["customer_id", "name", "email", "signup_date", "country"], customers)
    write_csv(os.path.join(OUT_DIR, "products.csv"),
              ["product_id", "product_name", "category", "price"], products)
    write_csv(os.path.join(OUT_DIR, "transactions.csv"),
              ["transaction_id", "customer_id", "product_id", "quantity", "unit_price",
               "total_amount", "transaction_ts", "payment_method", "status"], transactions)

    print(f"customers={len(customers)} products={len(products)} transactions={len(transactions)}")


if __name__ == "__main__":
    main()
