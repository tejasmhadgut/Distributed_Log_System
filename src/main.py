from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
import json
from dotenv import load_dotenv

from src.models.log import Log
from src.database import init_pool, close_pool, insert_logs, search_logs
from src.cache import init_redis, close_redis, get_from_cache, set_in_cache

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    init_redis()
    print(" Database and Redis initialized")
    yield
    close_pool()
    close_redis()
    print(" Connections closed")


app = FastAPI(title = "Log Analytics Platform", version="0.1.0", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status":"healthy"}

@app.post("/logs/ingest")
async def ingest_logs(logs: list[Log]):
    try:
        inserted = insert_logs(logs)
        return {"inserted":inserted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/logs/search")
async def search(service: str, level: str = None, hours: int =1, limit: int = 100):
    try:
        cache_key = f"search:{service}:{level}:{hours}:{limit}"
        cached = get_from_cache(cache_key)
        if cached:
            return {"results": json.loads(cached), "source": "cache"}
        
        results = search_logs(service, level, hours, limit)

        formatted = []
        for row in results:
            formatted.append({
                "id": row[0],
                "timestamp": row[1].isoformat(),
                "service_name": row[2],
                "log_level": row[3],
                "message": row[4],
                "request_id": row[5],
                "user_id": row[6],
                "latency_ms": row[7],
                "metadata": row[8]
            })

        set_in_cache(cache_key, json.dumps(formatted), ttl=300)
        return {"results": formatted, "source": "database"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))