from fastapi import APIRouter, HTTPException, Depends
from src.models.alert import AlertResponse
from src.db.postgres import get_alerts, acknowledge_alert, resolve_alert
from src.api.dependencies import require_permission

router = APIRouter(tags=["alerts"])


@router.get("/alerts", dependencies=[Depends(require_permission("alerts:read"))])
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


@router.put("/alerts/{alert_id}/acknowledge", dependencies=[Depends(require_permission("alerts:acknowledge"))])
async def ack_alert(alert_id: int):
    try:
        if not acknowledge_alert(alert_id):
            raise HTTPException(status_code=404, detail="Alert not found")
        return {"acknowledged": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook/alerts")
async def receive_alert(alert: dict):
    """Webhook endpoint to receive alerts from alert processor."""
    try:
        print(f"Webhook received: {alert}")
        return {"received": True, "alert_id": alert.get("alert_id")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/alerts/{alert_id}/resolve", dependencies=[Depends(require_permission("alerts:acknowledge"))])
async def resolve(alert_id: int):
    try:
        if not resolve_alert(alert_id):
            raise HTTPException(status_code=404, detail="Alert not found or already resolved")
        return {"resolved": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
