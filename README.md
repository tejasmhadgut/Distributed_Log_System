# Distributed Log Analytics Platform

A production-grade log analytics platform built from scratch. Ingests logs via Kafka, stores them in a three-tier architecture (ClickHouse → S3 → Glacier), computes real-time metrics, fires alerts, and provides a React dashboard for live observability.

---

## Features

| Feature | Description |
|---------|-------------|
| **Log Ingestion** | Batch ingest via REST API → Kafka → ClickHouse (fire-and-forget) |
| **Log Search** | Query by service, level, and time window across hot/warm tiers |
| **Distributed Tracing** | Hierarchical span trees reconstructed from correlated logs |
| **Stream Processing** | 1-minute tumbling windows with 30s grace period, per-service metrics |
| **Alert System** | Rule-based alerting with multi-window confirmation and webhook delivery |
| **Tiered Storage** | Hot (ClickHouse <7d) → Warm (S3 7-90d) → Cold (Glacier 90-365d via lifecycle policy) |
| **JWT Auth** | Access tokens (15min) + refresh tokens (7 days) with rotation |
| **RBAC** | Role-based permissions (admin / user / viewer) enforced per endpoint |
| **Rate Limiting** | Token bucket algorithm per user in Redis (60 req/min, fail-open) |
| **WebSocket Dashboard** | Live metrics, active alerts with expandable error logs |
| **React UI** | Log search, trace viewer, alert rule management, user management |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        INGESTION                            │
│                                                             │
│   REST API  ──►  Kafka (topic: logs)  ──►  Consumer        │
│   (FastAPI)       fire-and-forget         batch 100 / 5s   │
│                                               │             │
│                                               ▼             │
│                                          ClickHouse         │
│                                          (hot: <7 days)     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                       PROCESSING                            │
│                                                             │
│   Stream Processor  ──►  1-min windows  ──►  metrics table │
│   (polls ClickHouse)      30s grace          per service   │
│                                                             │
│   Alert Processor   ──►  check rules   ──►  webhook POST   │
│   (polls every 2min)      2-window confirm   PostgreSQL     │
│                                                             │
│   Archiver          ──►  S3 JSONL      ──►  delete from CH │
│   (every 5min)            warm/YYYY/MM/DD    if confirmed   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                        STORAGE                              │
│                                                             │
│   ClickHouse  ── hot ──  <7 days   fast queries            │
│   S3          ── warm ── 7-90 days JSONL, queryable        │
│   Glacier     ── cold ── 90-365d   lifecycle policy        │
│                                                             │
│   PostgreSQL  ── alert rules, alerts, users, archive meta  │
│   Redis       ── search/trace cache, rate limit buckets    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                         API + UI                            │
│                                                             │
│   FastAPI  ──  REST endpoints (auth, logs, traces,         │
│                alerts, rules, users)                        │
│           ──  WebSocket /ws/metrics  ──►  React Dashboard  │
│                                                             │
│   React Dashboard (Vite)                                    │
│   ├── Dashboard  live metrics + alerts (WebSocket)         │
│   ├── Logs       search with filters, click → trace        │
│   ├── Traces     span tree viewer per request ID           │
│   ├── Rules      create / enable / delete alert rules      │
│   └── Users      role management, deactivate accounts      │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| API | FastAPI (Python) | Async, fast, automatic OpenAPI docs |
| Message queue | Apache Kafka | Decouples ingestion from storage, handles spikes |
| Hot storage | ClickHouse | Columnar DB, 10-100x faster than PostgreSQL for log queries |
| Warm storage | AWS S3 (JSONL) | Cheap, durable, queryable without restore |
| Cold storage | AWS Glacier | Lifecycle policy from S3, near-zero cost for rarely accessed data |
| Relational DB | PostgreSQL | Transactional data: users, alert rules, alerts, archive metadata |
| Cache | Redis | Query cache (5-10 min TTL) + token bucket rate limiting |
| Frontend | React + Vite | Component-based UI, fast dev server |
| Charts | Recharts | Lightweight React chart library |
| Real-time | WebSocket (native) | Server pushes metrics every 5s, no polling overhead |
| Auth | JWT + bcrypt | Stateless access tokens, bcrypt password hashing |
| Infra | Docker Compose | Single command local setup for all 8 services |

---

## Running Locally

**Prerequisites:** Docker, Docker Compose, Node.js 18+

```bash
# 1. Clone and set up environment
git clone <repo-url>
cd Distributed_Log_Analytics
cp .env.example .env  # edit with your AWS credentials if using S3

# 2. Start all backend services
docker-compose up -d

# 3. Verify everything is running
curl http://localhost:8000/health
# → {"status": "healthy"}

# 4. Start the React dashboard
cd dashboard
npm install
npm run dev
# → http://localhost:5173
```

**Default credentials:** `admin` / `admin123` — change immediately in any real deployment.

**Services started by docker-compose:**

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

## API Reference

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

## Project Structure

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
├── docker-compose.yml
├── requirements.txt
├── DESIGN_DECISIONS.md          # Detailed reasoning behind every design choice
└── README.md
```

---

## Design Decisions

See [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) for detailed reasoning behind every major architectural and implementation choice — from why ClickHouse over PostgreSQL for logs, to how token bucket rate limiting works, to why self-registration was chosen over invite-only.

---

## Future Improvements

- Cold tier query with Glacier restore (initiate restore → poll status → download)
- WebSocket authentication (token as query param on connect)
- Log search within trace view (filter logs by request_id without leaving trace viewer)
- Multi-tenant support (isolate data per organization)
- Kafka partition scaling (currently single partition)
