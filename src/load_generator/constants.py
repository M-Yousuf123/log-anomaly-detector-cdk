DEFAULT_LAMBDA_NAME = "anomaly-detector-log-ingestor"
MAX_BATCH_SIZE = 100

SERVICES = ("payment-api", "auth-service", "inventory-worker", "notification-svc")
NORMAL_MESSAGES = (
    "Request processed successfully",
    "Cache hit for session key",
    "Health check passed",
    "Background job completed",
    "User profile fetched",
    "Metrics flushed to aggregator",
)
ERROR_MESSAGES = (
    "Connection timeout to db-primary",
    "HTTP 503 Service unavailable from upstream",
    "Fatal: unhandled exception in request handler",
    "Access denied for resource /admin/reports",
    "Gateway timeout after 30s waiting for payment provider",
)
RARE_MESSAGES = (
    "CRITICAL: checksum mismatch in shard replica 7",
    "Unknown opcode 0xDEAD in wire protocol v3",
    "Entropy pool depletion detected during token mint",
    "Invariant violation: negative inventory count for SKU-{sku}",
    "Ghost consumer lag spike on partition {partition}",
)
