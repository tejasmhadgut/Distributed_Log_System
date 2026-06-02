import time
from datetime import datetime
import requests
from src.db.postgres import get_connection, return_connection


def send_webhook(alert_id: int, alert_data: dict, webhook_url: str = "http://api:8000/webhook/alerts") -> bool:
    max_retries = 3
    retry_delay = 1

    for attempt in range(max_retries):
        try:
            response = requests.post(
                webhook_url,
                json={
                    "alert_id": alert_data.get("alert_id"),
                    "rule_id": alert_data.get("rule_id"),
                    "service_name": alert_data.get("service_name"),
                    "trace_id": alert_data.get("trace_id"),
                    "state": alert_data.get("state"),
                    "actual_value": alert_data.get("actual_value"),
                    "timestamp": datetime.now().isoformat()
                },
                timeout=5
            )
            if response.status_code == 200:
                conn = get_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                        UPDATE alerts SET webhook_status = 'SENT', updated_at = CURRENT_TIMESTAMP
                        WHERE alert_id = %s
                    """, (alert_id,))
                    conn.commit()
                finally:
                    return_connection(conn)
                return True
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                print(f"Webhook failed for alert {alert_id}: {e}")

    return False
