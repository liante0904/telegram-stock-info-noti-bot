import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(override=True)

conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST"),
    port=os.getenv("POSTGRES_PORT"),
    dbname=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
)

cur = conn.cursor()
cur.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name ILIKE '%firm_info%';
""")
rows = cur.fetchall()
for row in rows:
    print(f"Table found: {row[0]}")
conn.close()
