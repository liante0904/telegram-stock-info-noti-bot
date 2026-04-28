import os

import psycopg2
from dotenv import load_dotenv


def postgres_available() -> bool:
    load_dotenv(override=False)
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            dbname=os.getenv("POSTGRES_DB", "main_db"),
            user=os.getenv("POSTGRES_USER", "admin"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            connect_timeout=3,
        )
        conn.close()
        return True
    except Exception:
        return False
