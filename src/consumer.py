import json
import time
from kafka import KafkaConsumer
from src.database import batch_insert_logs

def start_consumer():
    consumer = KafkaConsumer(
        'logs',
        bootstrap_servers=['localhost:9092'],
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='earliest',
        group_id='storage-workers'
    )

    print("✓ Consumer started, listening on 'logs' topic")
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
                    inserted = batch_insert_logs(batch)
                    print(f"✓ Inserted {inserted} logs (time: {time_elapsed:.1f}s, count: {len(batch)})")
                    batch = []
                    last_insert_time = time.time()
                except Exception as e:
                    print(f"✗ Error inserting batch: {e}")
                    # Don't clear batch - will retry
                    
    except KeyboardInterrupt:
        print("\n✓ Consumer shutting down")
    finally:
        consumer.close()

if __name__ == '__main__':
    start_consumer()