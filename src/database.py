import os
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
import json

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
TRACE_LATENCY_THRESHOLD = 500 # ms - considered slow

connection_pool = None

def get_trace(request_id: str, limit: int = 100, offset: int = 0) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = """
            SELECT id, timestamp, service_name, log_level, message, latency_ms, span_id, parent_span_id
            FROM logs
            WHERE request_id = %s
            ORDER BY timestamp ASC
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, (request_id, limit, offset))
        results = cursor.fetchall()

        if not results:
            return None

        # Get total count
        cursor.execute("SELECT COUNT(*) FROM logs WHERE request_id = %s", (request_id,))
        total_spans = cursor.fetchone()[0]

        # Format spans with hierarchy
        spans = []
        services = set()
        errors = 0
        slow_spans = 0
        min_time = None
        max_time = None
        for row in results:
            span = {
                "id": row[0],
                "timestamp": row[1].isoformat() if row[1] else None,
                "service_name": row[2],
                "log_level": row[3],
                "message": row[4],
                "latency_ms": row[5],
                "span_id": row[6],
                "parent_span_id": row[7],
                "children": []
            }
            spans.append(span)
            services.add(row[2])

            if row[3] == "ERROR":
                errors += 1
            if row[5] and row[5] > TRACE_LATENCY_THRESHOLD:
                slow_spans +=1
            if min_time is None or row[1] < min_time:
                min_time = row[1]
            if max_time is None or row[1] > max_time:
                max_time = row[1]

        if spans and spans[0].get('span_id'):
            span_map = {s['span_id']: s for s in spans}
            root_spans = []
            for span in spans:
                if span['parent_span_id'] and span['parent_span_id'] in span_map:
                    span_map[span['parent_span_id']]['children'].append(span)
                else:
                    root_spans.append(span)
            spans = root_spans

        duration_ms = int((max_time - min_time).total_seconds() * 1000) if max_time else 0

        has_errors = errors > 0
        is_slow = slow_spans > 0
        success = not (has_errors or is_slow)

        return {
            "request_id": request_id,
            "spans": spans,
            "total_spans": total_spans,
            "returned_spans": len(results),
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": (offset + len(results)) < total_spans
            },
            "total_duration_ms": duration_ms,
            "services_involved": sorted(list(services)),
            "error_count": errors,
            "slow_span_count": slow_spans,
            "status": "SUCCESS" if success else ("FAILED" if has_errors else "SLOW")
        }
    finally:
        return_connection(conn)


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
                INSERT INTO logs (timestamp, service_name, log_level, message, request_id, user_id, latency_ms, metadata, span_id, parent_span_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (log.timestamp, log.service_name, log.log_level, log.message, log.request_id, log.user_id, log.latency_ms, log.metadata, log.span_id, log.parent_span_id)


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
                log.get('metadata'),
                log.get('span_id'),
                log.get('parent_span_id')
            ))

        cursor.executemany(
                """INSERT INTO logs
                (timestamp, service_name, log_level, message, request_id, user_id, latency_ms, metadata, span_id, parent_span_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
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