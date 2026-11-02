"""Create all tables (safe to run more than once).

Usage:  python -m scripts.init_db
"""

from sqlalchemy import inspect, text

from app import models  # noqa: F401  (registers the tables on Base)
from app.core.config import settings
from app.core.db import Base, engine


def grant_agent_access() -> None:
    """The agent's SQL tool may read the documents table and nothing else."""
    role = engine.dialect.identifier_preparer.quote(settings.agent_db_user)
    with engine.begin() as conn:
        conn.execute(text(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {role}"))
        conn.execute(text(f"GRANT SELECT ON documents TO {role}"))


def main() -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    grant_agent_access()

    tables = inspect(engine).get_table_names()
    print("Tables ready:", ", ".join(sorted(tables)))


if __name__ == "__main__":
    main()
