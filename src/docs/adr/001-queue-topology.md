# ADR 001: Three-Queue Log Ingestion Topology

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-06-21 |
| **Author** | Yousuf |
| **Project** | Logs Anomaly Detector |

---

## 1. Executive Summary

The log ingestor accepts batched log events over HTTP and routes each accepted event to one of two processing queues—**main** or **priority**—based on severity and message content. Each processing queue has a paired **dead-letter queue (DLQ)** for messages that fail repeated delivery attempts.

Together, these form a **three-tier queue topology**:

1. **Main queue** — standard SQS for high-volume, routine logs
2. **Priority queue** — FIFO SQS for time-sensitive and anomaly-prone signals
3. **Dead-letter queues** — isolated holding area for poison messages on either lane

This split lets downstream anomaly detection prioritize WARN/ERROR and alert-pattern traffic without paying FIFO throughput costs on the bulk of INFO-level volume.

---

## 2. Context

### 2.1 Problem

A log anomaly detector must ingest a mixed stream of events:

- **Routine traffic** (INFO/DEBUG health checks, cache hits, successful requests) that is high volume and tolerant of best-effort delivery ordering.
- **Signal traffic** (WARN/ERROR, timeouts, 5xx responses, access denials) that should reach detectors and alerting paths quickly and in a predictable order per service.

A single queue forces a trade-off: optimize for throughput and you sacrifice ordering guarantees on critical events; optimize for ordering (FIFO) and you cap throughput and increase cost on routine logs.

### 2.2 System boundary

At ingest time the pipeline is:

```
HTTP POST /logs
  → validate batch
  → enrich with ingest metadata
  → route (main | priority)
  → publish to SQS
```

Downstream consumers (anomaly scoring, DynamoDB state) are out of scope for this ADR but informed the queue design—especially the need to drain priority traffic first under load.

---

## 3. Decision

Adopt a **dual-lane SQS topology with mirrored DLQs**:

| Queue | Type | Name | Purpose |
|---|---|---|---|
| Main | Standard SQS | `anomaly-detector-main-queue` | Bulk routine logs |
| Priority | FIFO SQS | `anomaly-detector-priority-queue.fifo` | WARN/ERROR and alert-pattern logs |
| Main DLQ | Standard SQS | `anomaly-detector-main-dlq` | Failed main-lane messages |
| Priority DLQ | FIFO SQS | `anomaly-detector-priority-dlq.fifo` | Failed priority-lane messages |

Both processing queues use a **300 s visibility timeout** and redrive to their DLQ after **3** failed receives (`DEAD_LETTER_MAX_RECEIVE_COUNT`).

### 3.1 Routing rules

Routing happens in the ingestor Lambda before publish. A log is sent to the **priority** queue if **either** condition is true:

1. **Log level** is `WARN` or `ERROR`
2. **Message body** matches an alert keyword pattern (case-insensitive):  
   `timeout`, `exception`, `fatal`, `5xx`, `unavailable`, `denied`

All other accepted logs (e.g. `INFO`, `DEBUG` without alert keywords) go to the **main** queue.

```python
PRIORITY_LEVELS = frozenset({LogLevel.WARN, LogLevel.ERROR})

PRIORITY_MESSAGE_PATTERNS = re.compile(
    r"timeout|exception|fatal|5xx|unavailable|denied",
    re.IGNORECASE,
)
```

This two-signal approach catches severity-based anomalies **and** INFO-level messages that describe failure modes (e.g. `"Connection TIMEOUT occurred"` at INFO level still routes to priority).

### 3.2 Why FIFO for priority only

The priority lane uses SQS FIFO because:

- **Per-service ordering** — `MessageGroupId` is set to `service_name`, so events from the same producer are processed in submission order. That preserves causality when correlating a timeout with preceding request logs.
- **Exactly-once deduplication** — `MessageDeduplicationId` is the ingest-scoped UUID (`ingest_id`), preventing duplicate enqueue on client retries of the same accepted batch item.
- **Cost/throughput isolation** — FIFO queues have lower default throughput than standard queues. Restricting FIFO to the ~5–15% priority slice (typical in mixed workloads) keeps aggregate ingest cost down.

The main lane stays on **standard SQS** for higher throughput and lower per-message cost on the long tail of routine logs where strict ordering is unnecessary.

### 3.3 Publish behavior

The publisher groups enriched logs by route, then batch-sends (up to 10 messages per SQS API call) with exponential backoff on retryable errors. Priority and main publishes are independent— a batch can fan out to both queues in a single ingest request.

Each enriched message carries routing metadata (`route`, `ingest_id`, `correlation_id`, `schema_version`) so downstream consumers can branch without re-deriving routing logic.

---

## 4. Architecture diagram

```
                    ┌─────────────────────┐
                    │  API Gateway HTTP   │
                    │   POST /logs        │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Log Ingestor       │
                    │  Lambda             │
                    │                     │
                    │  validate → enrich  │
                    │       → route       │
                    └──────────┬──────────┘
                               │
               ┌───────────────┴───────────────┐
               │                               │
    ┌──────────▼──────────┐         ┌──────────▼──────────┐
    │  Main Queue         │         │  Priority Queue     │
    │  (standard SQS)     │         │  (FIFO SQS)         │
    │                     │         │  group = service    │
    │  INFO, DEBUG,       │         │  WARN, ERROR,       │
    │  routine INFO       │         │  alert keywords     │
    └──────────┬──────────┘         └──────────┬──────────┘
               │ after 3 failures              │ after 3 failures
    ┌──────────▼──────────┐         ┌──────────▼──────────┐
    │  Main DLQ           │         │  Priority DLQ       │
    │  (standard SQS)     │         │  (FIFO SQS)         │
    └─────────────────────┘         └─────────────────────┘
               │                               │
               └───────────────┬───────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Downstream         │
                    │  anomaly consumers  │
                    │  (future)           │
                    └─────────────────────┘
```

---

## 5. Alternatives considered

| Alternative | Why not chosen |
|---|---|
| **Single standard queue** | No per-service ordering; priority signals compete with bulk INFO traffic under backlog. |
| **Single FIFO queue** | FIFO throughput limits (~3,000 msg/s per queue with batching) become a bottleneck at INFO volume; higher cost for routine logs. |
| **SNS topic fan-out to two queues** | Adds an hop and duplicate filtering complexity; ingestor already has full log context for routing—direct SQS publish is simpler and cheaper at this scale. |
| **Kinesis Data Streams** | Strong fit for very high volume and replay, but over-engineered for a portfolio-scale demo; SQS matches Lambda consumer patterns with lower ops surface. |
| **Priority via SQS delay seconds** | Delay does not guarantee faster processing under consumer saturation; separate queues allow independent consumer concurrency. |
| **Shared DLQ for both lanes** | Loses lane attribution when triaging failures; mirrored DLQs keep main and priority poison pills separate. |

---

## 6. Consequences

### 6.1 Positive

- **Latency isolation** — priority consumers can run at higher concurrency without waiting behind INFO backlog.
- **Ordering where it matters** — FIFO per `service_name` on the priority lane supports causal anomaly detection.
- **Operational clarity** — CloudWatch metric `IngestorPriorityRouted` tracks how much traffic hits the fast lane; DLQ depth alarms can be set per lane.
- **Extensible routing** — `LogRouter` is a protocol; keyword lists and level sets can evolve without changing publisher or infrastructure.

### 6.2 Negative / trade-offs

- **Dual consumer fleets** — downstream processing must subscribe to two queues (or a router Lambda), increasing deployment surface.
- **Routing drift risk** — ingest-time keyword routing may diverge from detector logic if not kept in sync; enriched `route` field mitigates but does not eliminate this.
- **FIFO constraints** — priority lane requires `MessageGroupId` and `MessageDeduplicationId` on every send; misconfigured groups can create hot partitions for noisy services.
- **Partial batch failure** — if priority publish succeeds but main publish fails (or vice versa), the HTTP response reports enqueue failure and counts all enriched logs as rejected even though one lane may have received messages. At-least-once client retry can duplicate on the successful lane (mitigated on priority by deduplication ID).

### 6.3 Operational notes

- Visibility timeout (300 s) must remain **greater than** downstream consumer Lambda timeout to prevent duplicate processing.
- DLQ messages should be inspected with lane context; replay tooling should target the correct source queue type (standard vs FIFO).

---

## 7. Observability

The ingestor emits CloudWatch custom metrics (namespace scoped by `SERVICE_NAME`):

| Metric | Meaning |
|---|---|
| `IngestorInvocations` | HTTP ingest requests handled |
| `IngestorLogsAccepted` | Logs successfully validated and enqueued |
| `IngestorValidationErrors` | Per-item validation failures in a batch |
| `IngestorPriorityRouted` | Logs routed to the priority FIFO lane |
| `IngestorEnqueueErrors` | Logs lost to SQS publish failure |

Structured logs include `correlation_id`, per-log `route`, and batch-level `priority_routed` counts for traceability.

---

## 8. Validation

Routing behavior is covered by unit tests:

- `ERROR` and `WARN` → priority
- `INFO` with routine message → main
- `INFO` with `"Connection TIMEOUT occurred"` → priority (keyword override)

Infrastructure tests assert queue types, FIFO settings, redrive policies, and IAM least-privilege (ingestor can `SendMessage`/`SendMessageBatch` only on the two processing queue ARNs).

---

## 9. Future work

- **Downstream consumers** — separate Lambda pollers with higher reserved concurrency on the priority queue.
- **Dynamic routing** — load keyword patterns from SSM Parameter Store instead of hard-coded regex.
- **DLQ replay Lambda** — safe re-drive with lane-aware FIFO group IDs.
- **Routing audit** — sample compare ingest `route` vs post-detection severity to measure keyword precision/recall.

---

## 10. References

- Ingestor routing: `src/lambdas/log_ingestor/router.py`
- SQS publish (FIFO group/dedup): `src/lambdas/log_ingestor/publisher.py`
- Queue infrastructure: `lib/queues/main.ts`, `lib/queues/priority.ts`
- Stack wiring: `lib/logs-anomaly-detector-cdk-stack.ts`
