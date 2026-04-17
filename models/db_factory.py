import os


def get_db():
    """Return SQLiteManager or PostgreSQLManager based on DB_BACKEND env var.

    DB_BACKEND=sqlite   (default) — original behaviour, no change
    DB_BACKEND=postgres           — use PostgreSQL (TB_SEC_REPORTS)

    Rollback: set DB_BACKEND=sqlite in .env and restart the container.
    """
    backend = os.getenv("DB_BACKEND", "sqlite").lower()
    if backend == "postgres":
        from models.PostgreSQLManager import PostgreSQLManager
        return PostgreSQLManager()
    from models.SQLiteManager import SQLiteManager
    return SQLiteManager()
