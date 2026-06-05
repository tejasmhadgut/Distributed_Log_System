import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from src.core.exceptions import APIError
from src.core.middleware import api_error_handler
from src.db.postgres import init_pool, close_pool, init_archive_table, init_auth_tables, init_alert_tables
from src.services.cache_service import init_redis, close_redis
from src.workers.producer import close_producer
from src.api.routers import logs, traces, alerts, rules, auth, users
from src.api.routers.ws import router as ws_router, metrics_broadcaster

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    init_redis()
    init_archive_table()
    init_auth_tables()
    init_alert_tables()
    print("✓ Database and Redis initialized")
    task = asyncio.create_task(metrics_broadcaster())
    yield
    task.cancel()
    close_pool()
    close_redis()
    close_producer()
    print("✓ Connections closed")


app = FastAPI(title="Log Analytics Platform", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://18.191.36.209"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(APIError, api_error_handler)
app.include_router(auth.router)
app.include_router(logs.router)
app.include_router(traces.router)
app.include_router(alerts.router)
app.include_router(rules.router)
app.include_router(users.router)
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "healthy"}
