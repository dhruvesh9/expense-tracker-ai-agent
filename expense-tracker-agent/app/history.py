import sqlite3
from contextlib import closing

from app.config import get_settings


def _connect():
    return sqlite3.connect(get_settings().history_db)


def init_db() -> None:
    """Create the table if it doesn't exist yet. Called once at app startup."""
    # closing() closes the connection; `with conn` commits (or rolls back on error).
    with closing(_connect()) as conn, conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS turns (
                   id         INTEGER PRIMARY KEY AUTOINCREMENT,
                   session_id TEXT    NOT NULL,
                   user_id    INTEGER NOT NULL,
                   role       TEXT    NOT NULL,   -- 'user' or 'assistant'
                   content    TEXT    NOT NULL,
                   created_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
               )"""
        )
        _seed_demo(conn)


# (session_id, user_id, [(role, content), ...]): sample chats so a fresh deploy isn't empty
DEMO_CHATS = [
    ("demo-1", 1, [
        ("user", "I paid 250 for lunch at Starbucks"),
        ("assistant", "Saved: 250.00 for Lunch at Starbucks (food), today."),
        ("user", "make it 300"),
        ("assistant", "Updated: Lunch at Starbucks is now 300.00."),
    ]),
    ("demo-2", 2, [
        ("user", "show my expenses for last week"),
        ("assistant", "Here are your expenses for last week. Want a total?"),
        ("user", "yes, by category"),
        ("assistant", "Here is your spending by category for last week."),
    ]),
    ("demo-3", 3, [
        ("user", "bought chocolate for 2 rupees"),
        ("assistant", "Saved: 2.00 INR for Chocolate (food), today."),
        ("user", "delete that"),
        ("assistant", "Deleted the Chocolate expense."),
    ]),
]


def _seed_demo(conn) -> None:
    if conn.execute("SELECT COUNT(*) FROM turns").fetchone()[0]:
        return
    for session_id, user_id, turns in DEMO_CHATS:
        conn.executemany(
            "INSERT INTO turns (session_id, user_id, role, content) VALUES (?, ?, ?, ?)",
            [(session_id, user_id, role, content) for role, content in turns],
        )


def add_turn(session_id: str, user_id: int, role: str, content: str) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO turns (session_id, user_id, role, content) VALUES (?, ?, ?, ?)",
            (session_id, user_id, role, content),
        )

def get_recent(session_id: str, user_id: int, n: int = 6) -> list[dict]:
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT role, content FROM turns "
            "WHERE session_id = ? AND user_id = ? "
            "ORDER BY id DESC LIMIT ?",
            (session_id, user_id, n),
        ).fetchall()
    
    return [{"role": role, "content": content} for role, content in reversed(rows)]