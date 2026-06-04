import json
from datetime import date, timedelta
from fastapi import APIRouter, HTTPException, Depends
from src.models.log import Log
from src.workers.producer import send_log
from src.db.clickhouse import search_logs_ch
from src.services.cache_service import get_from_cache, set_in_cache
from src.services.s3_service import search_warm_logs
from src.api.dependencies import require_permission

router = APIRouter(prefix="/logs", tags=["logs"])


@router.post("/ingest", dependencies=[Depends(require_permission("logs:write"))])
async def ingest_logs(logs: list[Log]):
    try:
        for log in logs:
            send_log(log.model_dump(mode='json'))
        return {"inserted": len(logs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", dependencies=[Depends(require_permission("logs:read"))])
async def search(
    service: str,
    level: str = None,
    hours: int = 1,
    limit: int = 100,
    tier: str = "hot",
    start_date: str = None,
    end_date: str = None,
):
    """
    Search logs.
    tier=hot  → ClickHouse, use hours param (e.g. hours=1)
    tier=warm → S3, use start_date + end_date (YYYY-MM-DD)
    """
    try:
        if tier not in ["hot", "warm", "cold"]:
            raise HTTPException(status_code=400, detail="tier must be 'hot', 'warm', or 'cold'")

        if tier == "hot":
            cache_key = f"search:{service}:{level}:{hours}:{limit}:hot"
            cached = get_from_cache(cache_key)
            if cached:
                return {"results": json.loads(cached), "source": "cache"}

            results = search_logs_ch(service, level, hours, limit)
            formatted = [
                {
                    "id": row[0],
                    "timestamp": row[1].isoformat(),
                    "service_name": row[2],
                    "log_level": row[3],
                    "message": row[4],
                    "request_id": row[5],
                    "user_id": row[6],
                    "latency_ms": row[7],
                    "metadata": row[8]
                }
                for row in results
            ]
            set_in_cache(cache_key, json.dumps(formatted), ttl=300)
            return {"results": formatted, "source": "clickhouse"}

        elif tier == "warm":
            if not start_date:
                start_date = (date.today() - timedelta(days=30)).isoformat()
            if not end_date:
                end_date = (date.today() - timedelta(days=7)).isoformat()

            cache_key = f"search:{service}:{level}:{start_date}:{end_date}:{limit}:warm"
            cached = get_from_cache(cache_key)
            if cached:
                return {"results": json.loads(cached), "source": "cache"}

            results = search_warm_logs(service, level, start_date, end_date, limit)
            set_in_cache(cache_key, json.dumps(results), ttl=600)
            return {"results": results, "source": "s3", "files_scanned": "see archive_metadata"}

        else:
            raise HTTPException(status_code=501, detail="Cold tier (Glacier) querying not yet implemented")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
