"""Load scripts/seed.sql into the database, but only if it has no users yet.

Run on every deploy (see scripts/start.sh): on hosts with a throwaway disk the DB starts
empty each time, so this gives you demo data again. Safe to run repeatedly.
"""

import sqlite3
from pathlib import Path

from sqlalchemy.engine import make_url

from app.config import settings

SEED = Path(__file__).parent / "seed.sql"


def main() -> None:
    path = make_url(settings.database_url).database
    with sqlite3.connect(path) as conn:
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
            print("seed skipped: database already has users")
            return
        conn.executescript(SEED.read_text())
        print("seeded demo data")


if __name__ == "__main__":
    main()
