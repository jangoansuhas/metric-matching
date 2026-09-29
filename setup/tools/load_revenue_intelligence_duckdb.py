#!/usr/bin/env python3
"""Load the revenue-intelligence project's own synthetic data into a local DuckDB file.

The project ships only a Snowflake loader. This script calls the project's own
generator (src/ingestion/sample_data.generate, with the project's default
n_customers=400, seed=42) and writes each table to RAW.<TABLE> in DuckDB, which
is where the Snowflake loader would put it. It also defines to_date(text) ->
date, because the project's time spine calls Snowflake's to_date().
No project file is changed.

Usage (run from the repository root):
  python load_revenue_intelligence_duckdb.py <path/to/warehouse.duckdb>
"""
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path.cwd()))
from src.ingestion.sample_data import generate  # noqa: E402

db_path = sys.argv[1]
con = duckdb.connect(db_path)
con.execute("CREATE SCHEMA IF NOT EXISTS RAW")
for name, df in generate().items():
    con.register("df_in", df)
    con.execute(f'CREATE OR REPLACE TABLE RAW."{name.upper()}" AS SELECT * FROM df_in')
    con.unregister("df_in")
    print(f"loaded RAW.{name.upper()}")
con.execute("CREATE OR REPLACE MACRO to_date(s) AS CAST(s AS DATE)")
print("defined macro to_date")
con.close()
