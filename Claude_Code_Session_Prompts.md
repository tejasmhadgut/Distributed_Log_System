# Claude Code Session Guide
## Ready-to-Paste Prompts for Step-by-Step Project Building

### How to Use This Guide

1. Copy a prompt exactly as written
2. Paste into Claude Code
3. Claude will explain concepts and guide you
4. You write the code based on guidance
5. Move to next prompt

---

## PHASE 1: FOUNDATION (Week 1-2)

### SESSION 1.1: Project Setup & Data Modeling

**Copy and paste this into Claude Code:**

```
I'm building a distributed log analytics platform. Let me start with the foundation.

I need help understanding:
1. What fields should a Log object have? (required vs optional)
2. Should I use Pydantic or dataclasses for validation?
3. How do I validate log data (e.g., log_level must be ERROR/WARN/INFO/DEBUG)?

I'm planning to:
- Ingest 1M logs/sec eventually
- Query logs by service, level, timestamp
- Support structured metadata (JSON)
- Track distributed request IDs

Can you explain the concepts I need, then guide me on implementing a Log class?

Also, what testing strategy makes sense for a data model?
```

**After Claude explains:**

Ask:
```
Now I'll implement the Log class. Here's my structure:

[Show your code]

Is this approach correct? What would I improve?
```

---

### SESSION 1.2: Database Schema & Indexing

**Copy and paste this:**

```
I need to design a PostgreSQL schema for logs. Help me think through:

1. What columns do I absolutely need?
   - timestamp, service_name, log_level, message are obvious
   - What about request_id, user_id, latency_ms, metadata?

2. How do I choose which columns to index?
   - I'll query by: service_name, log_level, timestamp
   - I'll search by: request_id
   - I'll filter by: user_id sometimes
   
   Which 3-4 indexes should I create? Why those and not others?

3. For metadata (JSON), should I use TEXT, JSON, or JSONB?
   - What's the difference?
   - Can I search inside JSON fields?

4. Should I partition the table? (I'll have 1M+ logs/day)

Can you explain the trade-offs, then I'll write the schema?
```

**After Claude explains:**

Ask:
```
Here's my schema.sql:

[Show your code]

Does this handle common queries efficiently?
What indexes am I missing?
Why would these indexes help?
```

---

### SESSION 1.3: API Ingest Endpoint

**Copy and paste this:**

```
I'm building a FastAPI server to ingest logs. Help me design:

1. POST /logs/ingest endpoint
   - Should I accept one log or a batch?
   - What validation should happen at the API layer?
   - What should I return? (success count? inserted IDs?)

2. Database connection
   - Should I use psycopg2 directly or an ORM?
   - How do I handle connection pooling?
   - What happens if DB is down? Should API fail or queue logs?

3. Error handling
   - What if required fields are missing?
   - What if database insert fails?
   - Should I retry or fail fast?

4. Performance considerations
   - Should I insert logs one-by-one or batch them?
   - Why would batching be faster?
   - What batch size makes sense?

Can you explain the principles, then guide me on implementation?
```

**After Claude explains:**

Ask:
```
Here's my /logs/ingest endpoint:

[Show your code]

This approach handles ~100 logs/sec. 
To improve to 1000 logs/sec, what would I change?
Why would that be faster?
```

---

### SESSION 1.4: API Search Endpoint

**Copy and paste this:**

```
Now I need a GET /logs/search endpoint. Help me think through:

1. Query design
   - Query params: service (required), level (optional), hours (optional)
   - Should I include limit and offset for pagination?
   - How do I prevent someone querying all 1M logs?

2. Dynamic WHERE clause
   - How do I build a WHERE clause only with provided filters?
   - Example: if level not provided, don't include it in WHERE
   - If hours not provided, default to 1 hour

3. Query performance
   - I created indexes on (service_name, log_level, timestamp)
   - Will this index help my queries?
   - What's the difference between a sequential scan and index scan?

4. Response format
   - What should I return? (full logs? just IDs?)
   - Should I include metadata like "query_time_ms"?
   - How do I handle "no results"? (empty list or 404?)

5. Pagination
   - Should I use offset/limit or cursor-based pagination?
   - What's the difference?

Can you explain these, then guide implementation?
```

**After Claude explains:**

Ask:
```
Here's my /logs/search endpoint:

[Show your code]

I tested it, and querying 100K logs takes ~200ms.
Is that good? What would I measure to know if it's slow?
Why might it be slow?
```

---

### SESSION 1.5: Redis Caching Layer

**Copy and paste this:**

```
I want to add Redis caching to speed up repeated queries. 

Help me understand:

1. Cache-aside pattern
   - Check cache first
   - If miss, query database
   - Store result in cache
   - Next request uses cache
   
   When should I use cache-aside vs other patterns?

2. Cache keys
   - How do I generate a cache key from query parameters?
   - What makes a good cache key?
   - Should cache keys be deterministic?

3. TTL (Time To Live)
   - How long should search results stay cached?
   - If I cache for 5 minutes, and logs are updated, will cache be stale?
   - Is stale data acceptable?

4. Cache invalidation
   - When do I clear cache?
   - If new logs come in, do I invalidate? How?
   - What if I update a log - do I invalidate search results?

5. Monitoring cache
   - How do I measure cache hit ratio?
   - What's a good hit ratio? (50%? 80%?)
   - How do I know if caching is helping?

6. Failure modes
   - What if Redis is down?
   - Should the API stop working or fall back to DB?

Can you explain the concepts, then guide me on implementation?
```

**After Claude explains:**

Ask:
```
Here's my caching implementation:

[Show your code]

I tested querying the same search twice:
- First query: 200ms (database)
- Second query: 2ms (cache)

Is that the improvement you'd expect?
How do I measure cache hit ratio?
```

---

### SESSION 1.6: Load Testing & Benchmarking

**Copy and paste this:**

```
I want to measure my system's performance. Help me understand:

1. What to measure
   - Throughput (logs/sec or queries/sec)
   - Latency (how long does one operation take?)
   - P50/P95/P99 latencies (percentiles matter)
   - Cache hit ratio

2. Load testing approach
   - Should I test ingest or search or both?
   - How many concurrent clients should I simulate?
   - For 1 minute or 1 hour?
   - What's "realistic" load?

3. Testing with and without cache
   - How do I test the same queries without cache?
   - How do I show the difference?

4. Identifying bottlenecks
   - How do I know if database is slow or network is slow?
   - If ingest is slow, is it because PostgreSQL is slow or network latency?

5. Recording results
   - What format should I save test results in?
   - How do I compare before/after optimizations?

Can you explain the concepts, then guide me?
```

**After Claude explains:**

Ask:
```
Here's my load test:

[Show your code]

Results:
- Ingestion: 500 logs/sec
- Search queries: 800 queries/sec (with cache)
- Cache hit ratio: 72%

Is this good? What would I improve?
What's the bottleneck (database, network, CPU)?
```

---

## PHASE 2: SCALABILITY (Week 3-4)

### SESSION 2.1: Understanding Kafka

**Copy and paste this:**

```
I want to decouple log ingestion from database storage using Kafka.

Help me understand:

1. The problem Kafka solves
   - Right now: POST /logs → INSERT to PostgreSQL (synchronous, blocks if DB is slow)
   - With Kafka: POST /logs → send to Kafka → consumer processes asynchronously
   
   Why is this better? What problems does it solve?

2. Kafka concepts
   - Topic (like a channel or table)
   - Partition (how logs are divided)
   - Producer (sends logs)
   - Consumer (reads logs)
   - Consumer group (multiple consumers reading same topic)
   - Offset (position in the log)
   
   How do these fit together?

3. Partitioning strategy
   - Should I partition by service_name or something else?
   - What does partitioning do?
   - Why would I care which partition a log goes to?

4. Message ordering
   - If I send 100 logs from "auth-service", will they arrive in order?
   - Does it matter?
   - How do I ensure ordering?

5. Consumer implementation
   - How do I consume logs from Kafka?
   - Should I process one at a time or in batches?
   - How do I handle errors? (if one log fails to insert, what happens to others?)

6. Fault tolerance
   - What if the consumer crashes mid-batch?
   - How do I prevent duplicate processing?
   - What if Kafka broker fails?

Can you explain these concepts first?
```

**After Claude explains:**

Ask:
```
Now I want to implement:
1. KafkaProducer - sends logs to Kafka
2. KafkaConsumer - reads logs from Kafka
3. StorageWorker - inserts batches to PostgreSQL

What's the implementation approach? What should I code first?
```

---

### SESSION 2.2: Stream Processing & Real-Time Metrics

**Copy and paste this:**

```
I want to process logs in real-time to compute metrics.

Help me understand:

1. Stream processing concepts
   - What does "streaming" mean vs "batch"?
   - Why can't I just query the database every minute for metrics?
   - Why would real-time processing be better?

2. Windowing
   - I want to compute metrics for each minute (10:00-10:01, 10:01-10:02, etc)
   - This is a "tumbling window"
   - What logs go in which window?
   - What happens to logs that arrive 1 second late?

3. Metrics to compute (per service, per minute)
   - error_count: how many ERROR level logs
   - request_count: total logs
   - error_rate: error_count / request_count
   - p95_latency: 95th percentile of latency_ms values

   How do I compute these efficiently?
   Can I do this in real-time or only after the minute ends?

4. Storing metrics
   - Where should I store computed metrics?
   - Database? Redis? Both?
   - For how long? (1 hour? 24 hours?)

5. Leaderboards
   - I want to know which services have highest error rates
   - Should I compute this per window?
   - How would I store a leaderboard (sorted by error_rate)?

6. Implementation approach
   - Should I use asyncio? Threading? Separate process?
   - How do I consume from Kafka AND update metrics?
   - How do I know when a window is "closed" so I can emit metrics?

Can you explain these concepts?
```

**After Claude explains:**

Ask:
```
Here's my stream processor design:

[Show your approach/code]

Issues I'm thinking about:
1. How do I know when a minute ends?
2. What if logs arrive out of order?
3. How do I handle errors in stream processing?

What would you change?
```

---

### SESSION 2.3: Distributed Tracing

**Copy and paste this:**

```
I want to correlate logs across multiple services using request IDs.

Help me understand:

1. The problem
   - A user request flows through multiple services
   - Each service logs independently
   - How do I know which logs belong to the same request?

2. Request ID / Trace ID
   - Every request gets a unique ID (UUID)
   - Every service logs this ID with each log
   - Later, I can query: show me all logs with request_id=abc-123

   Is this sufficient? What else might I need?

3. Implementation
   - When does a request get an ID? (at API gateway)
   - How does it propagate? (HTTP header? Kafka message?)
   - How do I query by request_id efficiently?
   - Do I need a separate database index?

4. Visualization
   - If I have 5 logs with the same request_id from 3 services
   - How would I visualize this? (text list? timeline? DAG?)
   - What insights would I show? (total duration? slowest service?)

5. Sampling
   - If I log 1M requests/sec, should I trace all of them?
   - Should I only trace 1% of requests?
   - What's the trade-off?

Can you explain these concepts?
```

**After Claude explains:**

Ask:
```
I want to implement a trace retrieval endpoint:
GET /traces/{request_id}

Should return all logs with that request_id, ordered by timestamp.

How would I code this? What's the SQL query?
```

---

### SESSION 2.4: Alert System

**Copy and paste this:**

```
I want to detect anomalies and send alerts.

Help me understand:

1. Alert triggers
   - I computed error_rate per service per minute
   - If error_rate > 5%, I should alert
   - How do I detect this? (in stream processor? separate service?)

2. Alert deduplication
   - If error_rate is high for 10 minutes, should I send 10 alerts?
   - Or just 1 alert when it becomes high?
   - Or 1 alert when it first becomes high, then 1 when it recovers?

   This is "deduplication" - why is it important?

3. Alert state machine
   - State 1: OK (error_rate < 5%)
   - State 2: ALERTING (error_rate > 5%)
   
   I should only alert when state CHANGES (OK → ALERTING or ALERTING → OK)
   
   How do I track state?

4. Alert rules
   - Error rate > 5%
   - Latency p95 > 1000ms
   - Error count > 100 per minute
   
   How do I define these rules? Should it be code or configuration?

5. Alert delivery
   - Where do alerts go? (Slack? PagerDuty? Email? Log file?)
   - Is delivery guaranteed? (what if Slack is down?)
   - Should I retry?

6. Alert history
   - Where do I store alerts? (for auditing)
   - How long do I keep them?

Can you explain these concepts?
```

**After Claude explains:**

Ask:
```
Here's my alert system design:

[Show your approach]

I want to store alert state in Redis:
- Key: alert:state:{service}:{rule_name}
- Value: "active" or "inactive"

Is this right? How would I update state when a rule triggers?
```

---

## PHASE 3: DATA MANAGEMENT (Week 5-6)

### SESSION 3.1: S3 Archival & Tiered Storage

**Copy and paste this:**

```
I want to move old logs to S3 for cheap storage.

Help me understand:

1. Cost optimization
   - PostgreSQL costs ~$100/month for 1TB
   - S3 costs ~$0.02/month for 1TB
   - S3 Glacier costs ~$0.004/month for 1TB (cold storage)
   
   When should I move logs where?

2. Tiered storage strategy
   - Tier 1 (Hot): PostgreSQL, 0-7 days, fast queries, expensive
   - Tier 2 (Warm): S3 Standard, 7-90 days, slower queries, cheaper
   - Tier 3 (Cold): S3 Glacier, 90-365 days, very slow queries, cheapest
   
   Why this split? Is 7 and 90 days arbitrary?

3. Data format
   - I'm storing logs as individual database rows
   - For S3, should I use same format?
   - What about Parquet (columnar format)?
   - Why would Parquet be better for storage?

4. Archival process
   - Daily job: query PostgreSQL for logs > 7 days old
   - Convert to Parquet
   - Upload to S3
   - Delete from PostgreSQL
   
   What could go wrong? How do I ensure no data loss?

5. Querying cold storage
   - How do I query S3? (can't use SQL directly)
   - Should I use Athena? (AWS service that queries S3 via SQL)
   - How long does an Athena query take vs PostgreSQL?

6. Query routing
   - If user queries last 1 hour: use Redis cache
   - If user queries last 7 days: use PostgreSQL
   - If user queries last 90 days: use S3 Athena
   
   How do I decide? How do I implement?

Can you explain these concepts?
```

**After Claude explains:**

Ask:
```
I want to implement an archival job:

1. Query PostgreSQL for logs > 7 days old
2. Convert to Parquet
3. Upload to S3
4. Delete from PostgreSQL

What libraries do I need?
What could go wrong?
How do I handle partial failures?
```

---

## PHASE 4: PRODUCTION (Week 7-8)

### SESSION 4.1: Monitoring & Observability

**Copy and paste this:**

```
I want to monitor my system in production.

Help me understand:

1. Three pillars of observability
   - Logs (what happened?)
   - Metrics (how much? how fast?)
   - Traces (where did the request go?)
   
   Why do I need all three?

2. Metrics to track
   - Ingest throughput (logs/sec)
   - Query latency (p50, p95, p99)
   - Cache hit ratio (%)
   - Database connections (current count)
   - Kafka consumer lag (how far behind)
   - API error rate (errors/sec)
   
   Which are most important? Why?

3. Alerting strategy
   - If query latency p99 > 1 second, alert
   - If cache hit ratio < 50%, alert
   - If database connections > 80%, alert
   
   How do I know these thresholds are right?

4. Dashboard
   - What should I display in real-time?
   - What should I show historically?
   - Who's the audience? (me? operations team? executives?)

5. Health checks
   - GET /health endpoint (liveness - is the service running?)
   - GET /ready endpoint (readiness - can it serve requests?)
   
   What's the difference? When do I use each?

6. Logging levels
   - DEBUG (detailed, for development)
   - INFO (normal operation)
   - WARN (something unexpected, but not error)
   - ERROR (something failed)
   
   How do I decide what level to log at?

Can you explain these concepts?
```

**After Claude explains:**

Ask:
```
I want to add CloudWatch monitoring to my Python API.

I need:
1. Custom metrics: logs_ingested, query_latency, cache_hits
2. Alarms: alert if query_latency_p99 > 1000ms
3. Dashboard: showing key metrics

How would I implement this using boto3?
What's the simplest approach?
```

---

### SESSION 4.2: Security & Compliance

**Copy and paste this:**

```
I want to secure my system.

Help me understand:

1. API authentication
   - How do I restrict access to my logs?
   - Should I use API keys? JWT tokens? Both?
   - How do I store API keys securely?

2. Database security
   - Should PostgreSQL be exposed to the internet? (no)
   - Should it require authentication? (yes)
   - Should connections be encrypted? (yes)

3. Data at rest vs in transit
   - Data at rest: encrypted on disk
   - Data in transit: encrypted on wire (HTTPS/TLS)
   
   Why do I need both?

4. Audit logging
   - Who accessed which logs?
   - When did they access them?
   - Should I log failed access attempts?

5. Secrets management
   - Database passwords
   - AWS credentials
   - API keys
   
   Should I store these in code? (NO)
   Where should I store them? (AWS Secrets Manager)

6. Rate limiting
   - Should I limit how many requests per user per second?
   - How do I implement this?

Can you explain these concepts?
```

**After Claude explains:**

Ask:
```
I want to add API key authentication to my endpoints.

Implementation:
1. User requests with header: X-API-Key: abc123
2. I check if key exists in database
3. If valid, allow request; if not, return 401

How would I code this as FastAPI middleware?
Should I cache the key validation?
```

---

### SESSION 4.3: Disaster Recovery

**Copy and paste this:**

```
I want my system to survive failures.

Help me understand:

1. Types of failures
   - Database down (main failure)
   - Cache down (loss of performance)
   - Kafka down (loss of ingest)
   - API server down (can't serve requests)
   - Entire region down (AWS region failure)
   
   Which are most likely? Which are worst?

2. Backup strategy
   - PostgreSQL: automated daily backups
   - S3: versioning enabled (all objects have versions)
   - Can I restore from backup? How long does it take?

3. Replication
   - Should PostgreSQL have a standby replica?
   - If primary fails, does replica take over automatically?
   - How long is the failover?

4. Disaster recovery testing
   - Should I test restoring from backup periodically?
   - Should I practice failure scenarios?
   - Why would I do this?

5. Recovery time objectives (RTO)
   - If database dies at 10:00 AM, when should it be back up?
   - 1 minute? 1 hour? 1 day?
   - This affects architecture choices

6. Recovery point objective (RPO)
   - If database dies, how much data am I willing to lose?
   - 0 seconds (no loss)? 1 minute? 1 hour?
   - This affects architecture choices

Can you explain these concepts?
```

**After Claude explains:**

Ask:
```
I want to set up automated PostgreSQL backups.

Using RDS:
1. Automated backups enabled
2. 7-day retention
3. Point-in-time recovery

How do I configure this with Terraform?
How do I restore from a backup?
```

---

### SESSION 4.4: Performance Tuning

**Copy and paste this:**

```
I want to optimize my system.

Help me understand:

1. Profiling
   - Where is time spent? (API processing? Database? Network?)
   - How do I measure where time goes?
   - What tools can I use?

2. Database optimization
   - Are my queries using indexes?
   - How do I check? (EXPLAIN ANALYZE in PostgreSQL)
   - What does "sequential scan" mean?
   - How do I fix it?

3. Caching strategy
   - Should I cache at API level? Redis level? Both?
   - What's the hit ratio currently?
   - Could I cache more aggressively?

4. Batch sizes
   - Currently inserting logs 500 at a time
   - Would 1000 be faster? 100?
   - How do I find the optimal size?

5. Connection pooling
   - How many database connections should I maintain?
   - Too few: too many new connections (slow)
   - Too many: waste resources
   - What's the right number?

6. Compression
   - Logs are text, compress well
   - Should I compress logs before sending to Kafka?
   - Should I compress before storing in S3?
   - Trade-off: CPU vs bandwidth

Can you explain these concepts?
```

**After Claude explains:**

Ask:
```
My current system:
- Ingest: 10,000 logs/sec
- Query latency p99: 200ms
- Cache hit ratio: 65%

Bottleneck analysis:
- Database CPU: 40%
- Network: 30%
- API processing: 30%

Where should I optimize first?
```

---

## BONUS: Code Review Sessions

### When You Complete a Component

**Copy and paste this for code review:**

```
I just completed [component name].

Here's my code:
[Paste your code]

Questions for review:
1. Is this approach correct?
2. What would you improve?
3. Are there edge cases I'm missing?
4. Is this production-ready or just MVP?
5. What would I measure to verify it works?
6. How would I scale this if throughput doubles?
```

---

## How to Proceed

### Day 1:
1. Copy SESSION 1.1 prompt
2. Paste into Claude Code
3. Follow Claude's explanation
4. Write your Log model
5. Show Claude your code
6. Ask for review

### Day 2:
1. Copy SESSION 1.2 prompt
2. Same process
3. Write database schema
4. Test it works

### Continue this pattern for each session

---

## Pro Tips for Claude Code Sessions

1. **Be specific**: Show Claude what you wrote, not just ask general questions
2. **Ask why**: "Why would this be faster?" not just "Is this right?"
3. **Test first**: Run code, then ask Claude to explain results
4. **Iterate**: Show Claude v1, get feedback, show Claude v2
5. **Record learnings**: Write down why each decision matters

---

## Expected Timeline

- **Session 1.1-1.6**: 6-8 hours (Phase 1)
- **Session 2.1-2.4**: 10-12 hours (Phase 2)
- **Session 3.1**: 4-6 hours (Phase 3)
- **Session 4.1-4.4**: 8-10 hours (Phase 4)

**Total: 30-40 hours over 2-4 weeks**

---

## You're Ready

Start with Session 1.1. Copy the prompt exactly. Follow Claude's guidance. Write your code.

**You've got this. 🚀**
