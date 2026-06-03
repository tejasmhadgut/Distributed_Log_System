import time
from src.core.exceptions import RateLimitError

def check_rate_limit(user_id: int, redis_client, limit_per_min: int = 60) -> None:
    key = f"rate_limit:{user_id}"
    now = time.time()

    pipe = redis_client.pipeline()
    pipe.hgetall(key)
    results = pipe.execute()
    bucket = results[0]

    if bucket:
        tokens = float(bucket["tokens"])
        last_refill = float(bucket["last_refill"])
    else:
        tokens = limit_per_min
        last_refill = now

    # Refill tokens based on elapsed time
    elapsed = now - last_refill
    refill_rate = limit_per_min / 60.0  # tokens per second
    tokens = min(limit_per_min, tokens + elapsed * refill_rate)

    if tokens < 1:
        raise RateLimitError(f"Rate limit exceeded. Try again in {int(1 / refill_rate)}s")

    # Consume one token and save
    tokens -= 1
    pipe = redis_client.pipeline()
    pipe.hset(key, mapping={"tokens": tokens, "last_refill": now})
    pipe.expire(key, 120)
    pipe.execute()