import os
import sqlite3
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


def main() -> int:
    load_dotenv()

    base_dir = Path(__file__).resolve().parent.parent
    sqlite_path = base_dir / "db.sqlite3"

    sqlite_tables: list[str] = []
    if sqlite_path.exists():
        con = sqlite3.connect(sqlite_path)
        try:
            cur = con.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
            sqlite_tables = [row[0] for row in cur.fetchall()]
        finally:
            con.close()
    else:
        print("SQLite db not found:", sqlite_path)

    pg_tables: list[str] = []
    conn = None
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME", "postgres"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            sslmode=os.getenv("DB_SSLMODE", "require"),
        )
        cur = conn.cursor()
        cur.execute(
            "SELECT tablename FROM pg_catalog.pg_tables "
            "WHERE schemaname='public' ORDER BY tablename;"
        )
        pg_tables = [row[0] for row in cur.fetchall()]
    finally:
        if conn is not None:
            conn.close()

    print("SQLite tables:", sqlite_tables)
    print("Postgres tables:", pg_tables)

    missing_in_pg = sorted(set(sqlite_tables) - set(pg_tables))
    missing_in_sqlite = sorted(set(pg_tables) - set(sqlite_tables))

    print("Missing in Postgres:", missing_in_pg)
    print("Missing in SQLite:", missing_in_sqlite)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
