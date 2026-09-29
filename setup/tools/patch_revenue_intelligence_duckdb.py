#!/usr/bin/env python3
"""DuckDB dialect patch for the revenue-intelligence project (run from the repository root).

Snowflake NUMBER(p,s) and DECIMAL(p,s) are synonyms. DuckDB has no NUMBER type,
so this rewrites `number(` to `decimal(` in dbt/models/**/*.sql and prints every
changed line. Nothing else changes. The pinned, unpatched files stay the
reference for what a metric means; this patch only lets the project build locally.
"""
import re
from pathlib import Path

pat = re.compile(r"\bnumber\s*\(", re.I)
n = 0
for f in sorted(Path("dbt/models").rglob("*.sql")):
    old = f.read_text()
    new = pat.sub("decimal(", old)
    if new != old:
        for i, (a, b) in enumerate(zip(old.splitlines(), new.splitlines()), 1):
            if a != b:
                print(f"{f}:{i}\n  - {a.strip()}\n  + {b.strip()}")
                n += 1
        f.write_text(new)
print(f"{n} line(s) changed")
