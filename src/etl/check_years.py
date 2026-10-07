import sqlite3
import pandas as pd
import re

DB = "db/nifty100.db"

conn = sqlite3.connect(DB)

tables = [
    "profitandloss",
    "balancesheet",
    "cashflow",
    "financial_ratios"
]

pattern = re.compile(r"^\d{4}-\d{2}$")

for table in tables:
    df = pd.read_sql_query(f'SELECT * FROM "{table}"', conn)

    if "year" not in df.columns:
        print(f"\n{table}: no year column")
        continue

    invalid = df[
        ~df["year"].astype(str).str.strip().str.match(pattern)
    ]

    print(f"\n{'=' * 60}")
    print(f"{table}")
    print(f"Invalid rows: {len(invalid)}")

    if len(invalid) > 0:
        print("\nInvalid year values:")
        print(
            invalid["year"]
            .value_counts(dropna=False)
            .to_string()
        )

conn.close()