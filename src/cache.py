import os
import redis
import json
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")

redis_client = None

def init_redis():
    global redis_client
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)

def get_redis():
    if redis_client is None:
        init_redis()
    return redis_client

def close_redis():
    if redis_client:
        redis_client.close()

def get_from_cache(key: str):
    try:
        r = get_redis()
        return r.get(key)
    except:
        return None
    
def set_in_cache(key: str, value: str, ttl: int = 300):
    try:
        r = get_redis()
        r.setex(key, ttl, value)
    except:
        pass

def get_cached_trace(request_id: str) -> dict:
    try:
        r = get_redis()
        cached = r.get(f"trace:{request_id}")
        return json.loads(cached) if cached else None
    except:
        return None

def cache_trace(request_id: str, trace: dict, ttl: int = 3600):
    try:
        r = get_redis()
        r.setex(f"trace:{request_id}", ttl, json.dumps(trace, default=str))
    except:
        pass