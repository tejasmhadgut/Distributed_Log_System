from clickhouse_driver import Client
import os
from datetime import datetime, timedelta

CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CLICKHOUSE_HTTP_PORT = int(os.getenv("CLICKHOUSE_HTTP_PORT", 8123))
CLICKHOUSE_NATIVE_PORT = int(os.getenv("CLICKHOUSE_PORT", 9000))
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB", "logs_db")

client = None

def init_clickhouse():
    global client
    client = Client(CLICKHOUSE_HOST, port=CLICKHOUSE_NATIVE_PORT, database=CLICKHOUSE_DB, settings={'connect_timeout': 10})

    client.execute(f"CREATE DATABASE IF NOT EXISTS {CLICKHOUSE_DB}")

    client.execute(f"""
        CREATE TABLE IF NOT EXISTS {CLICKHOUSE_DB}.logs (
            id UInt64,
            timestamp DateTime,
            service_name String,
            log_level String,
            message String,
            request_id Nullable(String),
            user_id Nullable(String),
            latency_ms Nullable(Int32),
            metadata Nullable(String),
            span_id Nullable(String),
            parent_span_id Nullable(String),
            created_at DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY (service_name, timestamp)
        PARTITION BY toDate(timestamp)
        TTL timestamp + INTERVAL 90 DAY
    """)

    print("✓ ClickHouse initialized")

def get_client():
    global client
    if client is None:
        init_clickhouse()
    return client

def batch_insert_logs_ch(logs: list) -> int:
    if not logs:
        return 0

    try:
        ch = get_client()
        values = []
        for i, log in enumerate(logs):
            ts = log['timestamp']
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))

            values.append((
                i,
                ts,
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

        ch.execute(
            f"INSERT INTO {CLICKHOUSE_DB}.logs "
            "(id, timestamp, service_name, log_level, message, request_id, user_id, "
            "latency_ms, metadata, span_id, parent_span_id) VALUES",
            values
        )
        return len(logs)
    except Exception as e:
        print(f"Error inserting logs to ClickHouse: {e}")
        raise

def search_logs_ch(service: str, level: str = None, hours: int = 1, limit: int = 100) -> list:
    try:
        ch = get_client()
        query = f"SELECT * FROM {CLICKHOUSE_DB}.logs WHERE service_name = %(service)s"
        params = {"service": service}

        if level:
            query += " AND log_level = %(level)s"
            params["level"] = level

        query += f" AND timestamp > now() - INTERVAL {hours} HOUR ORDER BY timestamp DESC LIMIT {limit}"

        return ch.execute(query, params)
    except Exception as e:
        print(f"Error searching logs: {e}")
        raise

def get_trace_ch(request_id: str, limit: int = 100, offset: int = 0) -> dict:
    try:
        ch = get_client()

        query = f"""
            SELECT id, timestamp, service_name, log_level, message, latency_ms, span_id, parent_span_id
            FROM {CLICKHOUSE_DB}.logs
            WHERE request_id = %(request_id)s
            ORDER BY timestamp ASC
            LIMIT {limit} OFFSET {offset}
        """

        results = ch.execute(query, {"request_id": request_id})

        if not results:
            return None

        count_query = f"SELECT COUNT(*) FROM {CLICKHOUSE_DB}.logs WHERE request_id = %(request_id)s"
        total_spans = ch.execute(count_query, {"request_id": request_id})[0][0]

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
            if row[5] and row[5] > 500:
                slow_spans += 1
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
    except Exception as e:
        print(f"Error getting trace: {e}")
        raise

def get_logs_for_metrics(service_name: str, window_start: datetime, window_end: datetime) -> list:
    try:
        ch = get_client()
        query = f"""
            SELECT log_level, latency_ms
            FROM {CLICKHOUSE_DB}.logs
            WHERE service_name = %(service_name)s AND timestamp BETWEEN %(start)s AND %(end)s
        """
        return ch.execute(query, {
            "service_name": service_name,
            "start": window_start,
            "end": window_end
        })
    except Exception as e:
        print(f"Error getting logs for metrics: {e}")
        raise

def init_clickhouse_metrics_table():
    ch = get_client()

    ch.execute(f"""
        CREATE TABLE IF NOT EXISTS {CLICKHOUSE_DB}.metrics (
            id UInt64,
            timestamp DateTime,
            service_name String,
            request_count UInt32,
            error_count UInt32,
            error_rate Float32,
            latency_p95 UInt32,
            created_at DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY (service_name, timestamp)
        PARTITION BY toDate(timestamp)
        TTL timestamp + INTERVAL 365 DAY
    """)

def insert_metrics_ch(service_name: str, request_count: int, error_count: int,
                      error_rate: float, latency_p95: int, window_start) -> bool:
    try:
        ch = get_client()

        ch.execute(
            f"INSERT INTO {CLICKHOUSE_DB}.metrics "
            "(id, timestamp, service_name, request_count, error_count, error_rate, latency_p95) VALUES",
            [(
                hash(f"{service_name}_{window_start}") % 2147483647,
                window_start,
                service_name,
                request_count,
                error_count,
                error_rate,
                latency_p95
            )]
        )
        return True
    except Exception as e:
        print(f"Error inserting metrics: {e}")
        raise

def get_metrics_for_alert(service_name: str, metric_type: str, lookback_windows: int = 2) -> list:
    try:
        ch = get_client()

        query = f"""
            SELECT timestamp, {metric_type}
            FROM {CLICKHOUSE_DB}.metrics
            WHERE service_name = %(service_name)s
            ORDER BY timestamp DESC
            LIMIT {lookback_windows}
        """

        return ch.execute(query, {"service_name": service_name})
    except Exception as e:
        print(f"Error getting metrics for alert: {e}")
        raise

def get_logs_for_archival(older_than_days: int = 7, limit: int = 10000) -> list:
    try:
        ch = get_client()
        query = f"""
            SELECT id, timestamp, service_name, log_level, message, request_id, user_id,
                   latency_ms, metadata, span_id, parent_span_id
            FROM {CLICKHOUSE_DB}.logs
            WHERE timestamp < now() - INTERVAL {older_than_days} DAY
            ORDER BY timestamp ASC
            LIMIT {limit}
        """
        return ch.execute(query)
    except Exception as e:
        print(f"Error getting logs for archival: {e}")
        raise

def delete_archived_logs(log_ids: list) -> int:
    if not log_ids:
        return 0
    try:
        ch = get_client()
        placeholders = ','.join(str(id) for id in log_ids)
        query = f"ALTER TABLE {CLICKHOUSE_DB}.logs DELETE WHERE id IN ({placeholders})"
        ch.execute(query)
        return len(log_ids)
    except Exception as e:
        print(f"Error deleting archived logs: {e}")
        raise

def get_latest_metrics_ch() -> list:
    try:
        ch = get_client()
        return ch.execute(f"""
            SELECT service_name, timestamp, request_count, error_count, error_rate, latency_p95
            FROM {CLICKHOUSE_DB}.metrics
            WHERE timestamp >= now() - INTERVAL 10 MINUTE
            ORDER BY timestamp DESC
            LIMIT 1 BY service_name
        """)
    except Exception as e:
        print(f"Error getting latest metrics: {e}")
        return []

def get_recent_errors_ch(service_name: str, limit: int = 5) -> list:
    try:
        ch = get_client()
        return ch.execute(
            f"""
            SELECT message, timestamp
            FROM {CLICKHOUSE_DB}.logs
            WHERE service_name = %(service)s
              AND log_level = 'ERROR'
              AND timestamp >= now() - INTERVAL 1 HOUR
            ORDER BY timestamp DESC
            LIMIT {limit}
            """,
            {"service": service_name}
        )
    except Exception as e:
        print(f"Error getting recent errors: {e}")
        return []
