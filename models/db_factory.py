import os


def get_db():
    """Return SecReportsManager (ssh-library) by default, or SQLiteManager if DB_BACKEND=sqlite.

    DB_BACKEND=sqlite   — use SQLite (original behaviour)
    All other cases      — use SecReportsManager from ssh-library (default)
    """
    backend = os.getenv("DB_BACKEND", "postgres").lower()
    if backend == "sqlite":
        from models.SQLiteManager import SQLiteManager
        return SQLiteManager()

    from ssh_library import SecReportsManager
    return SecReportsManager()
