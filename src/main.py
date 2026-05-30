from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
import json
from dotenv import load_dotenv

from src.models.log import Log
from src.database import init_pool, close_pool, insert_logs, search_logs
from src.cache import init_redis, close_redis, get_from_cache, set_in_cache
from src.producer import send_log, init_producer, close_producer
from src.cache import get_cached_trace, cache_trace
from src.database import get_trace
from src.models.alert import AlertRuleCreate, AlertRuleUpdate, AlertRuleResponse, AlertResponse
from src.database import (
    create_alert_rule, get_alert_rules, get_alert_rule, 
    update_alert_rule, delete_alert_rule, get_alerts, acknowledge_alert
)
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    init_redis()
    # Don't initialize producer yet - do it lazily on first use
    print("✓ Database and Redis initialized")
    yield
    close_pool()
    close_redis()
    close_producer()
    print("✓ Connections closed")



app = FastAPI(title = "Log Analytics Platform", version="0.1.0", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status":"healthy"}

@app.post("/logs/ingest")
async def ingest_logs(logs: list[Log]):
    try:
        for log in logs:
            send_log(log.model_dump(mode='json'))
        return {"inserted":len(logs)}
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
    
@app.get("/traces/{request_id}")
async def get_trace_by_request_id(request_id: str, limit: int = 100, offset: int = 0):
    try:
        cache_key = f"trace:{request_id}:p{offset}:l{limit}"
        cached = get_cached_trace(cache_key)
        if cached:
            cached["source"] = "cache"
            return cached
        
        trace = get_trace(request_id, limit, offset)

        if not trace:
            raise HTTPException(status_code=404, detail="Request ID not found")
        
        trace["source"] = "database"

        # Cache the result
        cache_trace(cache_key, trace)

        return trace
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("traces/{request_id}/summary")
async def get_trace_summary(request_id: str):
    try:
        cached = get_cached_trace(f"trace-summary:{request_id}")
        if cached:
            return cached

        trace = get_trace(request_id, limit=1)

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

@app.post("/alert_rules", response_model=AlertRuleResponse)
async def create_rule(rule: AlertRuleCreate):
    try:
        return create_alert_rule(
            rule.service_name,
            rule.metric_type,
            rule.threshold,
            rule.enabled
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/alert_rules")
async def list_rules(enabled_only: bool = False):
    try:
        rules = get_alert_rules(enabled_only)
        return {
            "rules": [
                {
                    "rule_id": r[0],
                    "service_name": r[1],
                    "metric_type": r[2],
                    "threshold": r[3],
                    "enabled": r[4],
                    "created_at": r[5].isoformat() if r[5] else None,
                    "updated_at": r[6].isoformat() if r[6] else None
                }
                for r in rules
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/alert_rules/{rule_id}", response_model=AlertRuleResponse)
async def get_rule(rule_id: int):
    try:
        rule = get_alert_rule(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail="Alert rule not found")
        return rule
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/alert_rules/{rule_id}", response_model=AlertRuleResponse)
async def update_rule(rule_id: int, updates: AlertRuleUpdate):
    try:
        rule = update_alert_rule(
            rule_id,
            updates.threshold,
            updates.enabled
        )
        if not rule:
            raise HTTPException(status_code=404, detail="Alert rule not found")
        return rule
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/alert_rules/{rule_id}")
async def delete_rule(rule_id: int):
    try:
        if not delete_alert_rule(rule_id):
            raise HTTPException(status_code=404, detail="Alert rule not found")
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/alerts")
async def list_alerts(state: str = None, service: str = None, limit: int = 100):
    try:
        alerts = get_alerts(state, service, limit)
        return {
            "alerts": [
                {
                    "alert_id": a[0],
                    "rule_id": a[1],
                    "service_name": a[2],
                    "trace_id": a[3],
                    "metric_type": a[4],
                    "threshold": a[5],
                    "actual_value": a[6],
                    "state": a[7],
                    "created_at": a[8].isoformat() if a[8] else None,
                    "resolved_at": a[9].isoformat() if a[9] else None,
                    "acknowledged_at": a[10].isoformat() if a[10] else None,
                    "webhook_status": a[11]
                }
                for a in alerts
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/alerts/{alert_id}/acknowledge")
async def ack_alert(alert_id: int):
    try:
        if not acknowledge_alert(alert_id):
            raise HTTPException(status_code=404, detail="Alert not found")
        return {"acknowledged": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/webhook/alerts")
async def receive_alert(alert: dict):
    """Webhook endpoint to receive alerts from alert processor."""
    try:
        print(f"📨 Webhook received: {alert}")
        return {"received": True, "alert_id": alert.get("alert_id")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
