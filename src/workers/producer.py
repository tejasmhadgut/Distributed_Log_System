import json
import os
import time
from kafka import KafkaProducer
from dotenv import load_dotenv

load_dotenv()

producer = None

def init_producer():
    global producer
    max_retries = 10
    for attempt in range(max_retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=['kafka:29092'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                retries=3,
                request_timeout_ms=40000
            )
            break
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"⏳ Kafka not ready, retrying in {wait_time}s... ({attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                raise Exception(f"Failed to connect to Kafka after {max_retries} attempts")

def get_producer():
    if producer is None:
        init_producer()
    return producer

def send_log(log: dict):
    try:
        p = get_producer()
        p.send('logs', value=log)
    except Exception as e:
        raise Exception(f"Failed to send log to Kafka: {e}")

def close_producer():
    global producer
    if producer:
        producer.flush()
        producer.close()
        producer = None
