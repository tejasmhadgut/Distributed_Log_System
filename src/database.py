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
    
def create_alert_rule(service_name: str, metric_type: str, threshold: float, enabled: bool = True) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO alert_rules (service_name, metric_type, threshold, enabled)
            VALUES (%s, %s, %s, %s)
            RETURNING rule_id, service_name, metric_type, threshold, enabled, created_at, updated_at
        """, (service_name, metric_type, threshold, enabled))
        rule = cursor.fetchone()
        conn.commit()
        return {
            "rule_id": rule[0],
            "service_name": rule[1],
            "metric_type": rule[2],
            "threshold": rule[3],
            "enabled": rule[4],
            "created_at": rule[5],
            "updated_at": rule[6]
        }
    finally:
        return_connection(conn)

def get_alert_rules(enabled_only: bool = False) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = "SELECT rule_id, service_name, metric_type, threshold, enabled, created_at, updated_at FROM alert_rules"
        if enabled_only:
            query += " WHERE enabled = true"
        query += " ORDER BY created_at DESC"
        cursor.execute(query)
        return cursor.fetchall()
    finally:
        return_connection(conn)


def get_alert_rule(rule_id: int) -> dict:
    """Get a specific alert rule."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT rule_id, service_name, metric_type, threshold, enabled, created_at, updated_at
            FROM alert_rules WHERE rule_id = %s
        """, (rule_id,))
        rule = cursor.fetchone()
        if not rule:
            return None
        return {
            "rule_id": rule[0],
            "service_name": rule[1],
            "metric_type": rule[2],
            "threshold": rule[3],
            "enabled": rule[4],
            "created_at": rule[5],
            "updated_at": rule[6]
        }
    finally:
        return_connection(conn)

def delete_alert_rule(rule_id: int) -> bool:
    """Delete an alert rule."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM alert_rules WHERE rule_id = %s", (rule_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        return_connection(conn)

def get_alerts(state: str = None, service: str = None, limit: int = 100) -> list:
    """Get alerts with optional filtering."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = "SELECT alert_id, rule_id, service_name, trace_id, metric_type, threshold, actual_value, state, created_at, resolved_at, acknowledged_at, webhook_status FROM alerts WHERE 1=1"
        params = []
        
        if state:
            query += " AND state = %s"
            params.append(state)
        if service:
            query += " AND service_name = %s"
            params.append(service)
        
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        return_connection(conn)

def acknowledge_alert(alert_id: int) -> bool:
    """Mark an alert as acknowledged."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE alerts SET acknowledged_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE alert_id = %s
        """, (alert_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        return_connection(conn)

def update_alert_rule(rule_id: int, threshold: float = None, enabled: bool = None) -> dict:
    """Update an alert rule."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        updates = []
        params = []
        if threshold is not None:
            updates.append("threshold = %s")
            params.append(threshold)
        if enabled is not None:
            updates.append("enabled = %s")
            params.append(enabled)
        
        if not updates:
            return get_alert_rule(rule_id)
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(rule_id)
        
        query = f"UPDATE alert_rules SET {', '.join(updates)} WHERE rule_id = %s RETURNING rule_id, service_name, metric_type, threshold, enabled, created_at, updated_at"
        cursor.execute(query, params)
        rule = cursor.fetchone()
        conn.commit()
        return {
            "rule_id": rule[0],
            "service_name": rule[1],
            "metric_type": rule[2],
            "threshold": rule[3],
            "enabled": rule[4],
            "created_at": rule[5],
            "updated_at": rule[6]
        }
    finally:
        return_connection(conn)

def check_and_fire_alerts() -> list:
    """Check metrics against rules and create/update alerts."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Get enabled rules
        cursor.execute("""
            SELECT rule_id, service_name, metric_type, threshold 
            FROM alert_rules WHERE enabled = true
        """)
        rules = cursor.fetchall()
        
        alerts_fired = []
        
        for rule in rules:
            rule_id, service_name, metric_type, threshold = rule
            
            # Get the latest 2 metric windows for this service
            cursor.execute("""
                SELECT timestamp, {} 
                FROM metrics 
                WHERE service_name = %s 
                ORDER BY timestamp DESC 
                LIMIT 2
            """.format(metric_type), (service_name,))
            
            recent_metrics = cursor.fetchall()
            
            if not recent_metrics or len(recent_metrics) < 2:
                continue
            
            # Check if both recent windows exceed threshold
            breaches = sum(1 for _, value in recent_metrics if value is not None and value > threshold)
            should_fire = breaches >= 2
            
            # Get current alert state for this rule+service
            cursor.execute("""
                SELECT alert_id, state FROM alerts 
                WHERE rule_id = %s AND service_name = %s AND state = 'FIRING'
                ORDER BY created_at DESC LIMIT 1
            """, (rule_id, service_name))
            
            current_alert = cursor.fetchone()
            current_state = current_alert[1] if current_alert else None
            
            # State transition logic
            if should_fire and current_state != 'FIRING':
                # Create new alert or update existing
                actual_value = recent_metrics[0][1]
                if current_alert:
                    # Update existing alert to FIRING
                    cursor.execute("""
                        UPDATE alerts 
                        SET state = 'FIRING', updated_at = CURRENT_TIMESTAMP
                        WHERE alert_id = %s
                    """, (current_alert[0],))
                else:
                    # Create new alert
                    cursor.execute("""
                        INSERT INTO alerts 
                        (rule_id, service_name, trace_id, metric_type, threshold, actual_value, state, webhook_status)
                        VALUES (%s, %s, %s, %s, %s, %s, 'FIRING', 'PENDING')
                        RETURNING alert_id
                    """, (rule_id, service_name, None, metric_type, threshold, actual_value))
                    alert_id = cursor.fetchone()[0]
                    alerts_fired.append({
                        "alert_id": alert_id,
                        "rule_id": rule_id,
                        "service_name": service_name,
                        "state": "FIRING",
                        "actual_value": actual_value
                    })
            
            elif not should_fire and current_state == 'FIRING':
                # Check if 3 consecutive windows below threshold
                cursor.execute("""
                    SELECT COUNT(*) FROM metrics 
                    WHERE service_name = %s 
                    AND {} <= %s
                    ORDER BY timestamp DESC LIMIT 3
                """.format(metric_type), (service_name, threshold))
                
                windows_below = cursor.fetchone()[0]
                
                if windows_below >= 3:
                    # Resolve alert
                    cursor.execute("""
                        UPDATE alerts 
                        SET state = 'RESOLVED', resolved_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                        WHERE alert_id = %s
                    """, (current_alert[0],))
                    alerts_fired.append({
                        "alert_id": current_alert[0],
                        "state": "RESOLVED"
                    })
        
        conn.commit()
        return alerts_fired
    finally:
        return_connection(conn)

def create_alert_for_failed_trace(trace_id: str, service_name: str) -> dict:
    """Create an alert for a failed trace."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO alerts 
            (rule_id, service_name, trace_id, metric_type, threshold, actual_value, state, webhook_status)
            VALUES (%s, %s, %s, 'trace_failure', 1, 1, 'FIRING', 'PENDING')
            RETURNING alert_id
        """, (None, service_name, trace_id))
        
        alert_id = cursor.fetchone()[0]
        conn.commit()
        return {
            "alert_id": alert_id,
            "trace_id": trace_id,
            "service_name": service_name,
            "state": "FIRING"
        }
    finally:
        return_connection(conn)
