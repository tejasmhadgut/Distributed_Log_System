import time
from datetime import datetime
from src.database import (
    check_and_fire_alerts, 
    create_alert_for_failed_trace,
    get_connection,
    return_connection
)
from src.webhook import send_webhook

def start_alert_processor():
    """Main alert processor loop."""
    print("✓ Alert processor starting, polling every 2 minutes")
    
    while True:
        try:
            # Check metrics and fire alerts
            alerts = check_and_fire_alerts()
            
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
