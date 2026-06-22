import csv
import sqlite3
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent
STAR_DIR = BASE / "star_schema_output"
DB_DIR = BASE / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "mosquito_trap_dashboard.db"

TABLE_FILES = {
    "dim_date": STAR_DIR / "dim_date.csv",
    "dim_area": STAR_DIR / "dim_area.csv",
    "dim_trap": STAR_DIR / "dim_trap.csv",
    "dim_status": STAR_DIR / "dim_status.csv",
    "fact_observation": STAR_DIR / "fact_observation.csv",
    "fact_trap_health": STAR_DIR / "fact_trap_health.csv",
    "fact_alert": STAR_DIR / "fact_alert.csv",
}


def infer_type(values):
    vals = [v for v in values if v not in (None, "")]
    if not vals:
        return "TEXT"

    def is_int(x):
        try:
            int(str(x))
            return True
        except Exception:
            return False

    def is_float(x):
        try:
            float(str(x))
            return True
        except Exception:
            return False

    if all(is_int(v) for v in vals):
        return "INTEGER"
    if all(is_float(v) for v in vals):
        return "REAL"
    return "TEXT"


def load_csv_rows(path):
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return reader.fieldnames or [], rows


def create_table_and_insert(conn, table_name, columns, rows):
    if not columns:
        return 0

    sample_values = {c: [] for c in columns}
    for r in rows[:200]:
        for c in columns:
            sample_values[c].append(r.get(c, ""))

    col_types = {c: infer_type(sample_values[c]) for c in columns}

    conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
    col_defs = ", ".join([f'"{c}" {col_types[c]}' for c in columns])
    conn.execute(f'CREATE TABLE "{table_name}" ({col_defs})')

    if rows:
        placeholders = ", ".join(["?"] * len(columns))
        quoted_columns = [f'"{c}"' for c in columns]
        insert_sql = f'INSERT INTO "{table_name}" ({", ".join(quoted_columns)}) VALUES ({placeholders})'
        data = [tuple(r.get(c, None) for c in columns) for r in rows]
        conn.executemany(insert_sql, data)

    return len(rows)


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")

    loaded = {}
    for table, csv_path in TABLE_FILES.items():
        cols, rows = load_csv_rows(csv_path)
        loaded[table] = create_table_and_insert(conn, table, cols, rows)

    conn.commit()

    # Add simple metadata table for auditability
    conn.execute('DROP TABLE IF EXISTS "_etl_meta"')
    conn.execute('CREATE TABLE "_etl_meta" (key TEXT, value TEXT)')
    conn.executemany(
        'INSERT INTO "_etl_meta" (key, value) VALUES (?, ?)',
        [
            ("loaded_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("source_dir", str(STAR_DIR)),
            ("db_path", str(DB_PATH)),
        ],
    )
    conn.commit()
    conn.close()

    print("SQLite load completed")
    print(f"DB: {DB_PATH}")
    for t, c in loaded.items():
        print(f"- {t}: {c} rows")


if __name__ == "__main__":
    main()
