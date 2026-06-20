# Distributed Log Analytics Platform

A self-hosted observability system built to explore high-throughput log ingestion, stream processing, distributed tracing, tiered storage, and real-time analytics — the kind of problems that sit at the core of systems like the ELK stack.

Built entirely from scratch, solo, and deployed on AWS EC2.

**Live demo:** `http://18.191.36.209` — login with `admin` / `admin123`
*(hosted on AWS EC2 free tier — may be stopped to avoid costs; run locally with docker-compose in under 2 minutes)*

---

## What it does

- Ingests logs via a fire-and-forget Kafka pipeline and stores them across a hot-warm-cold tier (ClickHouse → S3 → Glacier)
- Aggregates per-service metrics in real-time using 1-minute tumbling windows with late-event handling
- Reconstructs distributed request traces from correlated logs across services
- Fires alerts via webhooks when metrics breach configurable thresholds, with noise-reduction logic to prevent false positives
- Serves a live React dashboard over WebSockets with search, trace viewer, and alert management

---

## Architecture

![Architecture Diagram](assets/Architecture.png)

---

## Performance

Measured on a local machine using `benchmark.py` against a running docker-compose stack:

- Sustained ingestion above **5,200 logs/sec** via Kafka batching
- Hot-tier search latency: **~51ms** uncached (ClickHouse columnar scan), **~34ms** cached (Redis)
- Trace lookup: **~18ms** average


---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| API | FastAPI (Python) | Async, automatic OpenAPI docs |
| Message queue | Apache Kafka | Decouples ingestion from storage, absorbs traffic spikes |
| Hot storage | ClickHouse | Columnar DB optimized for analytical log queries |
| Warm storage | AWS S3 (JSONL) | Cheap, durable, queryable without restore |
| Cold storage | AWS Glacier | Lifecycle policy from S3, near-zero cost |
| Relational DB | PostgreSQL | Transactional data: users, alert rules, archive metadata |
| Cache | Redis | Query cache + token bucket rate limiting |
| Frontend | React + Vite | Component-based UI, fast dev server |
| Real-time | WebSocket (native) | Server pushes metrics every 5s, no polling |
| Auth | JWT + bcrypt | Stateless access tokens, bcrypt password hashing |
| Infra | Docker Compose + Terraform | Local setup + AWS provisioning |

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

**Default credentials:** `admin` / `admin123`

---

## API

Full OpenAPI docs available at `http://localhost:8000/docs` when running locally.

Core endpoints:

- `POST /logs/ingest` — batch ingest logs
- `GET /logs/search` — search by service, level, time window, tier
- `GET /traces/{request_id}` — full span tree for a request
- `POST /alert_rules` / `GET /alert_rules` — manage alert rules
- `GET /alerts` — list firing and resolved alerts
- `ws://host/ws/metrics` — live metrics over WebSocket

---

## Project Structure

```
src/
├── api/          # FastAPI routers + dependency chain (auth, rate limit)
├── core/         # JWT, exceptions, middleware, rate limiter
├── db/           # ClickHouse + PostgreSQL clients
├── services/     # Cache, S3, webhook, auth logic
├── workers/      # Consumer, stream processor, alert processor, archiver
└── models/       # Pydantic request/response models

dashboard/        # React + Vite frontend
docker-compose.yml
terraform/        # AWS EC2, S3, IAM provisioning
```

---



## Key Design Decisions

**Why Kafka?**
The API publishes logs to Kafka and returns immediately — it never waits for the database. This decouples ingestion from storage, absorbs traffic spikes without backpressure on the API, and lets the consumer scale independently.

**Why ClickHouse?**
Log search is aggregation-heavy and read-heavy across millions of rows. ClickHouse's columnar storage scans only the columns needed and compresses data per-column — significantly faster than PostgreSQL for this workload.

**Why tiered storage?**
Storing everything in ClickHouse indefinitely is expensive. Logs older than 7 days are archived to S3 (cheap, queryable), then transitioned to Glacier via lifecycle policy after 90 days. The application manages the hot→warm transition; AWS manages warm→cold automatically.

**Why reconstruct traces from logs instead of using Jaeger?**
Logs are already the source of truth. Adding a dedicated tracing system would duplicate data and add infrastructure. Instead, traces are reconstructed by correlating logs using `request_id` and `span_id/parent_span_id` — simpler architecture, same end-to-end visibility.

---

## Engineering Tradeoffs

- **ClickHouse over Elasticsearch** — Elasticsearch supports full-text search but adds significant operational overhead. ClickHouse covers the analytical query patterns (filter by service, level, time window) with less complexity.
- **Custom stream processor over Flink/Kafka Streams** — A polling-based Python service computing 1-minute windows is sufficient at this scale and far simpler to reason about than a distributed stream processing framework.
- **Traces from logs over Jaeger** — Avoided a dedicated tracing system by reusing the existing log data. The tradeoff is less flexibility for sampling and trace export, which matters at production scale but not here.
- **Single EC2 over managed services** — Running everything on one instance with Docker Compose keeps the architecture demonstrable and cost-free. The same design decisions apply regardless of whether services run on EC2 or ECS.

---

## Future Improvements

- Cold tier query with Glacier restore (initiate restore → poll → download)
- WebSocket authentication (token as query param on connect)
- Log search within trace view (filter by request_id without leaving trace viewer)
- Multi-tenant support (isolate data per organization)
- Kafka partition scaling (currently single partition)
