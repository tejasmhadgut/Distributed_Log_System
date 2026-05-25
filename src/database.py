import os
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

connection_pool = None

def init_pool():
    global connection_pool
    connection_pool = psycopg2.pool.SimpleConnectionPool(1,20,DATABASE_URL)

def get_connection():
    if connection_pool is None:
        init_pool()
    return connection_pool.getconn()

def return_connection(conn):
    if connection_pool:
        connection_pool.putconn(conn)

def close_pool():
    if connection_pool:
        connection_pool.closeall()

def insert_logs(logs: list) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    inserted = 0

    try:
        for log in logs:
            cursor.execute(
                """
                INSERT INTO logs (timestamp, service_name, log_level, message, request_id, user_id, latency_ms, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (log.timestamp, log.service_name, log.log_level, log.message, log.request_id, log.user_id, log.latency_ms, log.metadata)
            

            )
            inserted += 1
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        return_connection(conn)
    
    return inserted

def batch_insert_logs(logs: list) -> int:
    if not logs:
        return 0
    
    conn = get_connection()
    cursor = conn.cursor()

    try:
        values = []
        for log in logs:
            values.append((
                log['timestamp'],
                log['service_name'],
                log['log_level'],
                log['message'],
                log.get('request_id'),
                log.get('user_id'),
                log.get('latency_ms'),
                log.get('metadata')
            ))

        cursor.executemany(
                """INSERT INTO logs 
                (timestamp, service_name, log_level, message, request_id, user_id, latency_ms, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                values
            )
        conn.commit()
        inserted = len(logs)
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        return_connection(conn)
    
    return inserted


def search_logs(service: str, level: str = None, hours: int = 1, limit: int = 100) -> list:
    conn = get_connection()
    cursor = conn.cursor()

    try:
        query = "SELECT id, timestamp, service_name, log_level, message, request_id, user_id, latency_ms, metadata FROM logs WHERE service_name = %s"
        params = [service]

        if level:
            query += " AND log_level = %s"
            params.append(level)

        query += " AND timestamp > NOW() - INTERVAL '%s hours' ORDER BY timestamp DESC LIMIT %s"
        params.extend([hours, limit])

        cursor.execute(query, tuple(params))
        results = cursor.fetchall()

        return results
    finally:
        return_connection(conn)