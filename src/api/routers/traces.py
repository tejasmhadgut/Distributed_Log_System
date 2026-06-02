from fastapi import APIRouter, HTTPException
from src.db.clickhouse import get_trace_ch
from src.services.cache_service import get_cached_trace, cache_trace

router = APIRouter(prefix="/traces", tags=["traces"])


@router.get("/{request_id}")
async def get_trace_by_request_id(request_id: str, limit: int = 100, offset: int = 0, tier: str = "hot"):
    """
    Get trace by request ID.
    tier: hot (ClickHouse, <7 days), warm (S3, 7-90 days), cold (Glacier, 90-365 days)
    """
    try:
        if tier not in ["hot", "warm", "cold"]:
            raise HTTPException(status_code=400, detail="tier must be 'hot', 'warm', or 'cold'")

        cache_key = f"trace:{request_id}:p{offset}:l{limit}:t{tier}"
        cached = get_cached_trace(cache_key)
        if cached:
            cached["source"] = "cache"
            return cached

        if tier == "hot":
            trace = get_trace_ch(request_id, limit, offset)

            if not trace:
                raise HTTPException(status_code=404, detail="Request ID not found")

            trace["source"] = "database"
            cache_trace(cache_key, trace)

            return trace
        else:
            raise HTTPException(status_code=501, detail=f"Tier '{tier}' querying not yet implemented")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{request_id}/summary")
async def get_trace_summary(request_id: str):
    try:
        cached = get_cached_trace(f"trace-summary:{request_id}")
        if cached:
            return cached

        trace = get_trace_ch(request_id, limit=1)

        if not trace:
            raise HTTPException(status_code=404, detail="Request ID not found")

        summary = {
            "request_id": request_id,
            "total_spans": trace["total_spans"],
            "services": trace["services_involved"],
            "duration_ms": trace["total_duration_ms"],
            "errors": trace["error_count"],
            "slow_spans": trace["slow_span_count"],
            "status": trace["status"]
        }
        cache_trace(f"trace-summary:{request_id}", summary)
        return summary
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
