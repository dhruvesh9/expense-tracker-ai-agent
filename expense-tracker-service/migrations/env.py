"""Alembic environment: tells Alembic which database and which models to use.

Alembic compares ``Base.metadata`` (our models) with the real database to
auto-generate migration scripts in ``migrations/versions``.
"""

from alembic import context

from app.config import settings
from app.database import build_engine
from app.models import Base

target_metadata = Base.metadata
# Use the same DATABASE_URL as the app (a caller may pre-set it, e.g. the tests).
db_url = context.config.get_main_option("sqlalchemy.url") or settings.database_url


def run_migrations_online() -> None:
    engine = build_engine(db_url)
    is_sqlite = engine.dialect.name == "sqlite"
    with engine.connect() as connection:
        if is_sqlite:
            # SQLite "batch" migrations rebuild a table (copy -> drop -> rename). With
            # foreign keys enforced, dropping a table that other tables reference fails,
            # so enforcement is paused for the migration and integrity is verified after.
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.commit()  # close the implicit transaction so Alembic manages its own
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # SQLite can't ALTER most things; batch mode recreates tables
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
        if is_sqlite:
            violations = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise RuntimeError(f"Migration left foreign key violations: {violations}")


run_migrations_online()
