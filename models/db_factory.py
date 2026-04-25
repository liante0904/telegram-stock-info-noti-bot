import os


def get_db():
    """Return PostgreSQLManager by default, or SQLiteManager if DB_BACKEND=sqlite.

    DB_BACKEND=sqlite   — use SQLite (original behaviour)
    All other cases      — use PostgreSQL (default)
    """
    backend = os.getenv("DB_BACKEND", "postgres").lower()
    if backend == "sqlite":
        from models.SQLiteManager import SQLiteManager
        return SQLiteManager()
    
    from models.PostgreSQLManager import PostgreSQLManager
    return PostgreSQLManager()
