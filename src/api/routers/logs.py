import json
from fastapi import APIRouter, HTTPException
from src.models.log import Log
from src.workers.producer import send_log
from src.db.clickhouse import search_logs_ch
from src.services.cache_service import get_from_cache, set_in_cache

router = APIRouter(prefix="/logs", tags=["logs"])


@router.post("/ingest")
async def ingest_logs(logs: list[Log]):
    try:
        for log in logs:
            send_log(log.model_dump(mode='json'))
        return {"inserted": len(logs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search(service: str, level: str = None, hours: int = 1, limit: int = 100, tier: str = "hot"):
    """
    Search logs.
    tier: hot (ClickHouse, <7 days), warm (S3, 7-90 days), cold (Glacier, 90-365 days)
    """
    try:
        if tier not in ["hot", "warm", "cold"]:
            raise HTTPException(status_code=400, detail="tier must be 'hot', 'warm', or 'cold'")

        cache_key = f"search:{service}:{level}:{hours}:{limit}:t{tier}"
        cached = get_from_cache(cache_key)
        if cached:
            return {"results": json.loads(cached), "source": "cache"}

        if tier == "hot":
            results = search_logs_ch(service, level, hours, limit)

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
        else:
            raise HTTPException(status_code=501, detail=f"Tier '{tier}' querying not yet implemented")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
