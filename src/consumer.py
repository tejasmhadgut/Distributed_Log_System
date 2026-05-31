import json
import time
from kafka import KafkaConsumer
from src.clickhouse_db import batch_insert_logs_ch

def start_consumer():
    """Start Kafka consumer with batching logic (Option C)."""

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
                group_id='storage-workers',
                session_timeout_ms=30000,
                request_timeout_ms=40000
            )
            print("✓ Consumer started, listening on 'logs' topic")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"⏳ Kafka not ready, retrying in {wait_time}s... ({attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"✗ Failed to connect to Kafka")
                raise

    batch = []
    last_insert_time = time.time()

    try:
        while True:
            msg = consumer.poll(timeout_ms=500)
            
            if msg:
                for topic_partition, messages in msg.items():
                    for message in messages:
                        batch.append(message.value)
            
            time_elapsed = time.time() - last_insert_time
            should_insert = len(batch) >= 100 or (time_elapsed >= 5 and batch)
            
            if should_insert:
                try:
                    inserted = batch_insert_logs_ch(batch)  # Changed function name
                    print(f"✓ Inserted {inserted} logs (time: {time_elapsed:.1f}s, count: {len(batch)})")
                    batch = []
                    last_insert_time = time.time()
                except Exception as e:
                    print(f"✗ Error inserting batch: {e}")
                    
    except KeyboardInterrupt:
        print("\n✓ Consumer shutting down")
    finally:
        consumer.close()

if __name__ == '__main__':
    start_consumer()
