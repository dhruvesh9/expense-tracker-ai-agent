"""Run the real Alembic migrations on a throwaway file DB to prove they work."""

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.database import build_engine


def test_migrations_create_expected_tables(tmp_path):
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")
    tables = set(inspect(build_engine(url)).get_table_names())
    assert {"users", "expenses", "alembic_version"} <= tables
    user_columns = {c["name"] for c in inspect(build_engine(url)).get_columns("users")}
    assert {"country", "default_currency", "monthly_budget_minor"} <= user_columns


def test_migrations_preserve_data_both_ways(tmp_path):
    """Upgrade a 0001 database holding rows to head, then back: no rows are lost."""
    from sqlalchemy import text

    url = f"sqlite:///{tmp_path / 'roundtrip.db'}"
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "0001")
    engine = build_engine(url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id, name, created_at, updated_at) VALUES (1, 'Old', '2026-01-01', '2026-01-01')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO expenses (user_id, amount_minor, currency, expense_date, created_at, updated_at) "
                "VALUES (1, 5000, 'INR', '2026-01-02', '2026-01-02', '2026-01-02')"
            )
        )
    command.upgrade(cfg, "head")
    with engine.connect() as conn:
        row = conn.execute(text("SELECT default_currency FROM users")).one()
        assert row[0] == "INR"  # existing rows get the default
        assert conn.execute(text("SELECT is_recurring FROM expenses")).one()[0] == 0
    command.downgrade(cfg, "0001")  # rebuilds tables while expenses reference users
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM users")).one()[0] == 1
        assert conn.execute(text("SELECT COUNT(*) FROM expenses")).one()[0] == 1
