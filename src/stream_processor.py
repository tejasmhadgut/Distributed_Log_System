import time
from datetime import datetime, timedelta, timezone
from src.clickhouse_db import get_logs_for_metrics, insert_metrics_ch, get_client, init_clickhouse_metrics_table

class StreamProcessor:
    def __init__(self):
        self.grace_period = timedelta(seconds=30)
        init_clickhouse_metrics_table()
    
    def compute_metrics(self, service_name: str, window_start: datetime):
        """Compute metrics from ClickHouse logs."""
        window_end = window_start + timedelta(minutes=1)
        
        try:
            logs = get_logs_for_metrics(service_name, window_start, window_end)
            
            if not logs:
                return None
            
            request_count = len(logs)
            error_count = sum(1 for log in logs if log[0] == "ERROR")
            error_rate = (error_count / request_count * 100) if request_count > 0 else 0
            
            latencies = [log[1] for log in logs if log[1] is not None]
            latency_p95 = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0
            
            return {
                "service_name": service_name,
                "window_start": window_start,
                "request_count": request_count,
                "error_count": error_count,
                "error_rate": error_rate,
                "latency_p95": int(latency_p95)
            }
        except Exception as e:
            print(f"Error computing metrics: {e}")
            return None
    
    def get_unique_services(self) -> list:
        """Get all services that have logs in the last 10 minutes."""
        try:
            ch = get_client()
            query = "SELECT DISTINCT service_name FROM logs_db.logs WHERE timestamp > now() - INTERVAL 10 MINUTE"
            result = ch.execute(query)
            return [row[0] for row in result]
        except Exception as e:
            print(f"Error getting unique services: {e}")
            return []
    
    def start(self):
        """Main processing loop."""
        print("✓ Stream processor starting, computing metrics every 1 minute")
        
        while True:
            try:
                # Compute metrics for the window that just closed
                now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
                window_start = now - timedelta(minutes=1)
                
                # Get all services
                services = self.get_unique_services()
                
                if not services:
                    print("⏳ No services found yet")
                else:
                    for service in services:
                        metrics = self.compute_metrics(service, window_start)
                        if metrics:
                            insert_metrics_ch(
                                metrics["service_name"],
                                metrics["request_count"],
                                metrics["error_count"],
                                metrics["error_rate"],
                                metrics["latency_p95"],
                                window_start
                            )
                            print(f"✓ Metrics for {service}: {metrics['request_count']} requests, {metrics['error_rate']:.1f}% errors, {metrics['latency_p95']}ms p95")
                
                # Wait for next window
                time.sleep(60)
            
            except KeyboardInterrupt:
                print("\n✓ Stream processor shutting down")
                break
            except Exception as e:
                print(f"✗ Error in stream processor: {e}")
                time.sleep(60)

if __name__ == '__main__':
    processor = StreamProcessor()
    processor.start()
