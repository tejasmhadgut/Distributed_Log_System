import os
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

connection_pool = None


def init_pool():
    global connection_pool
    connection_pool = psycopg2.pool.SimpleConnectionPool(1, 20, DATABASE_URL)

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
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM alert_rules WHERE rule_id = %s", (rule_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        return_connection(conn)

def get_alerts(state: str = None, service: str = None, limit: int = 100) -> list:
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

def create_alert_for_failed_trace(trace_id: str, service_name: str) -> dict:
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

def init_archive_table():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS archive_metadata (
                archive_id SERIAL PRIMARY KEY,
                log_count INT NOT NULL,
                s3_path VARCHAR(255) NOT NULL,
                tier VARCHAR(10) NOT NULL,
                status VARCHAR(20) DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                error_message TEXT,
                retry_count INT DEFAULT 0
            )
        """)
        conn.commit()
        print("✓ Archive metadata table initialized")
    except Exception as e:
        print(f"Archive table may already exist: {e}")
    finally:
        return_connection(conn)

def init_alert_tables():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alert_rules (
                rule_id SERIAL PRIMARY KEY,
                service_name VARCHAR(100) NOT NULL,
                metric_type VARCHAR(50) NOT NULL,
                threshold FLOAT NOT NULL,
                enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id SERIAL PRIMARY KEY,
                rule_id INT REFERENCES alert_rules(rule_id),
                service_name VARCHAR(100) NOT NULL,
                metric_type VARCHAR(50) NOT NULL,
                metric_value FLOAT NOT NULL,
                threshold FLOAT NOT NULL,
                state VARCHAR(20) DEFAULT 'FIRING',
                message TEXT,
                fired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP
            )
        """)
        conn.commit()
        print("✓ Alert tables initialized")
    except Exception as e:
        print(f"Alert tables may already exist: {e}")
    finally:
        return_connection(conn)

def track_archive(log_count: int, s3_path: str, tier: str, status: str = "PENDING", error_msg: str = None) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO archive_metadata (log_count, s3_path, tier, status, error_message)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING archive_id
        """, (log_count, s3_path, tier, status, error_msg))
        archive_id = cursor.fetchone()[0]
        conn.commit()
        return archive_id
    finally:
        return_connection(conn)

def update_archive_status(archive_id: int, status: str, error_msg: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE archive_metadata
            SET status = %s, completed_at = CURRENT_TIMESTAMP, error_message = %s
            WHERE archive_id = %s
        """, (status, error_msg, archive_id))
        conn.commit()
    finally:
        return_connection(conn)

def get_archive_status(archive_id: int) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT archive_id, log_count, s3_path, tier, status, created_at, completed_at, error_message, retry_count
            FROM archive_metadata WHERE archive_id = %s
        """, (archive_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "archive_id": row[0],
            "log_count": row[1],
            "s3_path": row[2],
            "tier": row[3],
            "status": row[4],
            "created_at": row[5],
            "completed_at": row[6],
            "error_message": row[7],
            "retry_count": row[8]
        }
    finally:
        return_connection(conn)

def get_failed_archives() -> list:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT archive_id, log_count, s3_path, tier, retry_count
            FROM archive_metadata
            WHERE status = 'FAILED' AND retry_count < 3
            ORDER BY created_at ASC
        """)
        return cursor.fetchall()
    finally:
        return_connection(conn)

def increment_archive_retry(archive_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE archive_metadata
            SET retry_count = retry_count + 1
            WHERE archive_id = %s
        """, (archive_id,))
        conn.commit()
    finally:
        return_connection(conn)

def init_auth_tables():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                       user_id SERIAL PRIMARY KEY,
                       username VARCHAR(50) UNIQUE NOT NULL,
                        email VARCHAR(100) UNIQUE NOT NULL,
                        hashed_password VARCHAR(255) NOT NULL,
                        role VARCHAR(20) DEFAULT 'viewer',
                        is_active BOOLEAN DEFAULT true,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                       )
                       """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                token_id SERIAL PRIMARY KEY,
                user_id INT REFERENCES users(user_id),
                token TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                is_revoked BOOLEAN DEFAULT false,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Seed default admin if no users exist
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            from src.core.auth import hash_password
            hashed = hash_password("admin123")
            cursor.execute(
                "INSERT INTO users (username, email, hashed_password, role) VALUES (%s, %s, %s, %s)",
                ("admin", "admin@localhost", hashed, "admin")
            )
            print("✓ Default admin created (admin / admin123) — change this password")

        conn.commit()
        print("✓ Auth tables initialized")
    except Exception as e:
        conn.rollback()
        print(f"Auth table init error: {e}")
    finally:
        return_connection(conn)

def get_user_by_username(username: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT user_id, username, email, hashed_password, role, is_active FROM users WHERE username = %s",
            (username,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {"user_id": row[0], "username": row[1], "email": row[2],
                "hashed_password": row[3], "role": row[4], "is_active": row[5]}
    finally:
        return_connection(conn)

def get_user_by_id(user_id: int) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT user_id, username, email, role, is_active FROM users WHERE user_id = %s",
            (user_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {"user_id": row[0], "username": row[1], "email": row[2],
                "role": row[3], "is_active": row[4]}
    finally:
        return_connection(conn)

def store_refresh_token(user_id: int, token: str, expires_at) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO refresh_tokens (user_id, token, expires_at) VALUES (%s, %s, %s)",
            (user_id, token, expires_at)
        )
        conn.commit()
    finally:
        return_connection(conn)

def verify_refresh_token(token: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT token_id, user_id FROM refresh_tokens WHERE token = %s AND is_revoked = false AND expires_at > NOW()",
            (token,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {"token_id": row[0], "user_id": row[1]}
    finally:
        return_connection(conn)

def revoke_refresh_token(token: str) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE refresh_tokens SET is_revoked = true WHERE token = %s",
            (token,)
        )
        conn.commit()
    finally:
        return_connection(conn)

def create_user(username: str, email: str, hashed_password: str, role: str = "viewer") -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO users (username, email, hashed_password, role)
            VALUES (%s, %s, %s, %s)
            RETURNING user_id, username, email, role, is_active, created_at
            """,
            (username, email, hashed_password, role)
        )
        row = cursor.fetchone()
        conn.commit()
        return {
            "user_id": row[0], "username": row[1], "email": row[2],
            "role": row[3], "is_active": row[4], "created_at": row[5]
        }
    finally:
        return_connection(conn)


def get_all_users() -> list:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT user_id, username, email, role, is_active, created_at FROM users ORDER BY created_at ASC"
        )
        return cursor.fetchall()
    finally:
        return_connection(conn)


def update_user_role(user_id: int, role: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE users SET role = %s
            WHERE user_id = %s
            RETURNING user_id, username, email, role, is_active, created_at
            """,
            (role, user_id)
        )
        row = cursor.fetchone()
        conn.commit()
        if not row:
            return None
        return {
            "user_id": row[0], "username": row[1], "email": row[2],
            "role": row[3], "is_active": row[4], "created_at": row[5]
        }
    finally:
        return_connection(conn)


def deactivate_user(user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users SET is_active = false WHERE user_id = %s",
            (user_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        return_connection(conn)

def get_warm_archives(start_date: str, end_date: str) -> list:
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        start_path = "warm/" + start_date.replace("-", "/")
        end_path = "warm/" + end_date.replace("-", "/") + "~"
        cursor.execute(
            """
            SELECT s3_path FROM archive_metadata
            WHERE tier = 'warm'
            AND status = 'SUCCESS'
            AND s3_path >= %s AND s3_path <= %s
            ORDER BY s3_path ASC
            """,
            (start_path, end_path)
        )
        return [row[0] for row in cursor.fetchall()]
    finally:
        return_connection(conn)

def resolve_alert(alert_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE alerts SET state = 'RESOLVED', resolved_at = CURRENT_TIMESTAMP
            WHERE alert_id = %s AND state = 'FIRING'
        """, (alert_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        return_connection(conn)
