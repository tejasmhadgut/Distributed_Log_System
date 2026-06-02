from fastapi import FastAPI
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from src.db.postgres import init_pool, close_pool, init_archive_table
from src.services.cache_service import init_redis, close_redis
from src.workers.producer import close_producer
from src.api.routers import logs, traces, alerts, rules

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    init_redis()
    init_archive_table()
    print("✓ Database and Redis initialized")
    yield
    close_pool()
    close_redis()
    close_producer()
    print("✓ Connections closed")


app = FastAPI(title="Log Analytics Platform", version="0.1.0", lifespan=lifespan)

app.include_router(logs.router)
app.include_router(traces.router)
app.include_router(alerts.router)
app.include_router(rules.router)


@app.get("/health")
async def health():
    return {"status": "healthy"}
