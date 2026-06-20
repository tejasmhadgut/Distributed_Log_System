# Implementation Details

Detailed reference for implementation specifics, benchmark methodology, full API, and service configuration. Moved here from README to keep the main README readable.

---

## Benchmark Methodology

Run `benchmark.py` against a local docker-compose stack:

```bash
python benchmark.py --host http://localhost:8000 --logs 50000 --batch 1000
```

The script:
1. Authenticates and gets a JWT
2. Sends logs in batches, measures wall-clock throughput
3. Waits 10 seconds for Kafka consumer to process
4. Queries each service and measures DB vs cache latency
5. Looks up a trace by request_id and measures lookup latency

### Results

| Metric | Result |
|--------|--------|
| Ingestion throughput | ~5,200 logs/sec (batch size 1000, 50k logs) |
| Hot-tier query latency (uncached) | ~51ms avg (ClickHouse columnar scan) |
| Hot-tier query latency (cached) | ~34ms avg (Redis cache hit) |
| Trace lookup latency | ~18ms avg |
| Cache speedup | ~1.5x |
| Stream processing window | 1 minute (30s grace period for late logs) |
| Alert detection latency | ~2 minutes (2-window confirmation) |

The 1.5x cache speedup is lower than expected because ClickHouse is already fast at this data scale — the cache primarily protects against thundering herd, not individual query latency.

---

## Feature Details

| Feature | Implementation |
|---------|---------------|
| **Log Ingestion** | Batch ingest via REST API → Kafka → ClickHouse (fire-and-forget) |
| **Log Search** | Query by service, level, and time window across hot/warm tiers |
| **Distributed Tracing** | Hierarchical span trees reconstructed from correlated logs via span_id/parent_span_id |
| **Stream Processing** | 1-minute tumbling windows with 30s grace period, per-service metrics |
| **Alert System** | Rule-based alerting with 2-window confirmation, 3-window cooldown, webhook delivery |
| **Tiered Storage** | Hot (ClickHouse <7d) → Warm (S3 7-90d) → Cold (Glacier 90-365d via lifecycle policy) |
| **JWT Auth** | Access tokens (15min) + refresh tokens (7 days) with rotation |
| **RBAC** | Role-based permissions (admin / user / viewer) enforced per endpoint |
| **Rate Limiting** | Token bucket algorithm per user in Redis (60 req/min, fail-open) |
| **WebSocket Dashboard** | Live metrics, active alerts, fan-out broadcaster (single DB query per 5s regardless of client count) |
| **React UI** | Log search, trace viewer, alert rule management, user management |

---

## Full API Reference

All endpoints except `/auth/login`, `/auth/register`, and `/health` require `Authorization: Bearer <token>`.

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | Get access + refresh tokens |
| POST | `/auth/register` | Self-register (gets viewer role) |
| POST | `/auth/refresh` | Rotate refresh token |
| POST | `/auth/logout` | Revoke refresh token |

### Logs
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/logs/ingest` | Batch ingest logs |
| GET | `/logs/search?service=&level=&hours=&tier=` | Search logs (hot or warm tier) |

### Traces
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/traces/{request_id}` | Full span tree for a request |
| GET | `/traces/{request_id}/summary` | Aggregated trace stats |

### Alerts & Rules
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/alerts` | List alerts (filter by state, service) |
| PUT | `/alerts/{id}/acknowledge` | Acknowledge a firing alert |
| GET | `/alert_rules` | List all rules |
| POST | `/alert_rules` | Create rule |
| PUT | `/alert_rules/{id}` | Update threshold or enabled state |
| DELETE | `/alert_rules/{id}` | Delete rule |

### Users
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/users` | List all users (admin only) |
| PUT | `/users/{id}/role` | Change user role (admin only) |
| PUT | `/users/{id}/deactivate` | Deactivate user (admin only) |

### WebSocket
| Endpoint | Description |
|----------|-------------|
| `ws://host/ws/metrics` | Live metrics push every 5s (no auth required) |

---

## Services (docker-compose)

| Service | Port | Description |
|---------|------|-------------|
| FastAPI | 8000 | REST API + WebSocket |
| PostgreSQL | 5432 | Relational data |
| ClickHouse | 9000/8123 | Log and metrics storage |
| Redis | 6379 | Cache + rate limiting |
| Kafka | 9092 | Log message queue |
| Zookeeper | 2181 | Kafka coordinator |
| Consumer | — | Kafka → ClickHouse batch writer |
| Stream Processor | — | Computes 1-min metric windows |
| Alert Processor | — | Evaluates alert rules, fires webhooks |
| Archiver | — | ClickHouse → S3 archival |

---

## Detailed Project Structure

```
├── src/
│   ├── main.py                  # FastAPI app, lifespan, router registration
│   ├── config/settings.py       # Pydantic BaseSettings (typed env vars)
│   ├── core/
│   │   ├── auth.py              # JWT encode/decode, bcrypt
│   │   ├── exceptions.py        # Custom exception hierarchy
│   │   ├── middleware.py        # Standardized error response handler
│   │   └── rate_limiter.py      # Token bucket algorithm
│   ├── db/
│   │   ├── postgres.py          # Connection pool, all PG queries
│   │   └── clickhouse.py        # ClickHouse client, log/metrics queries
│   ├── api/
│   │   ├── dependencies.py      # get_current_user, require_permission, rate_limit
│   │   └── routers/             # One file per resource
│   ├── services/
│   │   ├── auth_service.py      # Login, refresh, logout, register
│   │   ├── cache_service.py     # Redis read/write helpers
│   │   ├── s3_service.py        # Warm tier S3 reads
│   │   └── webhook_service.py   # Alert webhook delivery
│   ├── models/                  # Pydantic request/response models
│   └── workers/
│       ├── consumer.py          # Kafka → ClickHouse batch writer
│       ├── stream_processor.py  # 1-min metric windows
│       ├── alert_processor.py   # Rule evaluation + webhook trigger
│       └── archiver.py          # ClickHouse → S3 archival
├── dashboard/                   # React + Vite frontend
│   └── src/
│       ├── pages/               # Logs, Traces, Rules, Users
│       ├── components/          # ServiceCard, AlertsList, MetricsChart
│       └── hooks/useWebSocket.js
├── terraform/                   # AWS EC2, S3, IAM provisioning
├── docker-compose.yml
├── requirements.txt
├── benchmark.py
├── DESIGN_DECISIONS.md
└── README.md
```
