import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.db.postgres import get_alerts
from src.db.clickhouse import get_latest_metrics_ch, get_recent_errors_ch

router = APIRouter()

_clients: set[WebSocket] = set()

async def broadcast(data: dict):
    dead = set()
    for ws in _clients:
        try:
            await ws.send_json(data)
        except Exception:
            dead.add(ws)
        _clients.difference_update(dead)

async def metrics_broadcaster():
    while True:
        await asyncio.sleep(5)
        if not _clients:
            continue
        try:
            metrics_rows = await asyncio.to_thread(get_latest_metrics_ch)
            alert_rows = await asyncio.to_thread(get_alerts, "FIRING", None, 20)

            alerts = []
            for a in alert_rows:
                error_rows = await asyncio.to_thread(get_recent_errors_ch, a[2])
                alerts.append({
                    "alert_id": a[0],
                    "service_name": a[2],
                    "metric_type": a[4],
                    "actual_value": round(float(a[6]), 2) if a[6] else 0.0,
                    "state": a[7],
                    "recent_errors": [
                        {"message": r[0], "timestamp": r[1].isoformat() if r[1] else None}
                        for r in error_rows
                    ],
                })

            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metrics": [
                    {
                        "service_name": r[0],
                        "window_time": r[1].isoformat() if r[1] else None,
                        "request_count": int(r[2]),
                        "error_count": int(r[3]),
                        "error_rate": round(float(r[4]), 2) if r[4] else 0.0,
                        "latency_p95": round(float(r[5]), 1) if r[5] else 0.0,
                    }
                    for r in metrics_rows
                ],
                "alerts": alerts,
            }
            await broadcast(payload)
        except Exception as e:
            print(f"WS broadcaster error: {e}")


@router.websocket("/ws/metrics")
async def ws_metrics(websocket: WebSocket):
    await websocket.accept()
    _clients.add(websocket)
    print(f"WS client connected ({len(_clients)} total)")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _clients.discard(websocket)
        print(f"WS client disconnected ({len(_clients)} total)")
