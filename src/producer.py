import json
import os
from kafka import KafkaProducer
from dotenv import load_dotenv

load_dotenv()

producer = None

def init_producer():
    """Initialize Kafka producer (lazy - happens on first use)."""
    global producer
    if producer is None:
        producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            retries=3  # Retry connection 3 times
        )

def get_producer():
    """Get or create producer."""
    if producer is None:
        init_producer()
    return producer

def send_log(log: dict):
    """Send a log to Kafka. Fire-and-forget."""
    try:
        if 'timestamp' in log and hasattr(log['timestamp'], 'isoformat'):
            log['timestamp'] = log['timestamp'].isoformat()
        p = get_producer()
        p.send('logs', value=log)
    except Exception as e:
        raise Exception(f"Failed to send log to Kafka: {e}")

def close_producer():
    """Close producer connection."""
    global producer
    if producer:
        producer.flush()
        producer.close()
        producer = None
