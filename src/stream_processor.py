import json
import time
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from kafka import KafkaConsumer
from src.database import get_connection, return_connection

class StreamProcessor:
    def __init__(self):
        self.windows = defaultdict(lambda: {'logs': [], 'start_time': None})
        self.grace_period = 30
        
    def process(self):
        """Main processing loop."""
        
        # Retry connecting to Kafka
        max_retries = 10
        consumer = None
        for attempt in range(max_retries):
            try:
                consumer = KafkaConsumer(
                    'logs',
                    bootstrap_servers=['kafka:29092'],
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    auto_offset_reset='earliest',
                    group_id='metric-processors',
                    session_timeout_ms=30000,
                    request_timeout_ms=40000
                )
                print("✓ Stream processor started")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"⏳ Kafka not ready, retrying in {wait_time}s... ({attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    print(f"✗ Failed to connect to Kafka")
                    raise
        
        try:
            while True:
                msg = consumer.poll(timeout_ms=1000)
                
                if msg:
                    for topic_partition, messages in msg.items():
                        for message in messages:
                            self.handle_log(message.value)
                
                self.flush_closed_windows()
                
        except KeyboardInterrupt:
            print("\n✓ Stream processor shutting down")
        finally:
            consumer.close()
    
    def handle_log(self, log: dict):
        """Collect log into appropriate window."""
        timestamp = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
        minute_start = timestamp.replace(second=0, microsecond=0)
        window_key = (log['service_name'], minute_start.isoformat())
        
        self.windows[window_key]['logs'].append(log)
        if self.windows[window_key]['start_time'] is None:
            self.windows[window_key]['start_time'] = minute_start
    
    def flush_closed_windows(self):
        """Check for windows that are old enough to close."""
        
        now = datetime.now(timezone.utc)
        
        for window_key, window_data in list(self.windows.items()):
            service_name, minute_start_str = window_key
            minute_start = datetime.fromisoformat(minute_start_str)
            minute_end = minute_start + timedelta(minutes=1)
            time_since_window_close = (now - minute_end).total_seconds()
            
            if time_since_window_close > self.grace_period:
                self.compute_and_store_metrics(window_key, window_data)
                del self.windows[window_key]
    
    def compute_and_store_metrics(self, window_key: tuple, window_data: dict):
        """Compute metrics for a closed window."""
        service_name, minute_start_str = window_key
        logs = window_data['logs']
        
        if not logs:
            return
        
        request_count = len(logs)
        error_count = sum(1 for log in logs if log['log_level'] == 'ERROR')
        error_rate = (error_count / request_count * 100) if request_count > 0 else 0
        
        latencies = [log.get('latency_ms', 0) for log in logs if log.get('latency_ms')]
        if latencies:
            latencies.sort()
            p95_idx = int(len(latencies) * 0.95)
            latency_p95 = latencies[p95_idx]
        else:
            latency_p95 = 0
        
        self.store_metrics(
            minute_start_str,
            service_name,
            request_count,
            error_count,
            error_rate,
            latency_p95
        )
        
        print(f"✓ Metrics for {service_name} @ {minute_start_str}: "
              f"requests={request_count}, errors={error_count}, "
              f"error_rate={error_rate:.1f}%, p95={latency_p95}ms")
    
    def store_metrics(self, timestamp: str, service: str, request_count: int, 
                     error_count: int, error_rate: float, latency_p95: int):
        """Store metrics in database."""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    service_name VARCHAR(255) NOT NULL,
                    request_count INT,
                    error_count INT,
                    error_rate FLOAT,
                    latency_p95 INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                INSERT INTO metrics 
                (timestamp, service_name, request_count, error_count, error_rate, latency_p95)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (timestamp, service, request_count, error_count, error_rate, latency_p95))
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"✗ Error storing metrics: {e}")
        finally:
            return_connection(conn)

if __name__ == '__main__':
    processor = StreamProcessor()
    processor.process()
