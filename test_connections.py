import os
from dotenv import load_dotenv
import psycopg2
import redis

load_dotenv()

print("Testing PostgreSQL...")
try:
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM logs;")
    count = cursor.fetchone()[0]
    print(f" PostgreSQL connected! Logs table has {count} rows")
    conn.close()
except Exception as e:
    print(f" PostgreSQL failed: {e}")

print("Testing Redis..")
try:
    r = redis.from_url(os.getenv("REDIS_URL"))
    r.ping()
    print(" Redis connected")
except Exception as e:
    print(f" Redis failed: {e}")