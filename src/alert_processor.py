import time
from datetime import datetime
from src.clickhouse_db import get_metrics_for_alert, get_client
from src.database import (
    get_alert_rules, 
    get_connection, 
    return_connection
)
from src.webhook import send_webhook

def check_and_fire_alerts_ch() -> list:
    """Check metrics from ClickHouse against rules and create/update alerts."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Get enabled rules
        rules = get_alert_rules(enabled_only=True)
        alerts_fired = []
        
        for rule in rules:
            rule_id, service_name, metric_type, threshold, enabled, _, _ = rule
            
            # Get the latest 2 metric windows for this service
            recent_metrics = get_metrics_for_alert(service_name, metric_type, lookback_windows=2)
            
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
                recent_metrics_3 = get_metrics_for_alert(service_name, metric_type, lookback_windows=3)
                windows_below = sum(1 for _, value in recent_metrics_3 if value is not None and value <= threshold)
                
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

def start_alert_processor():
    """Main alert processor loop."""
    print("✓ Alert processor starting, polling every 2 minutes")
    
    while True:
        try:
            # Check metrics and fire alerts
            alerts = check_and_fire_alerts_ch()
            
            for alert in alerts:
                if alert['state'] == 'FIRING':
                    print(f"🔔 Alert fired: {alert['service_name']} - {alert.get('actual_value', 'N/A')}")
                    send_webhook(alert['alert_id'], alert)
                elif alert['state'] == 'RESOLVED':
                    print(f"✓ Alert resolved: {alert['service_name']}")
                    send_webhook(alert['alert_id'], alert)
            
            # Wait 2 minutes before next check
            time.sleep(120)
        
        except KeyboardInterrupt:
            print("\n✓ Alert processor shutting down")
            break
        except Exception as e:
            print(f"✗ Error in alert processor: {e}")
            time.sleep(120)

if __name__ == '__main__':
    start_alert_processor()
