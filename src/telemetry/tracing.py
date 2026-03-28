import logging
from src.config import settings

logger = logging.getLogger(__name__)

_initialized = False


def init_telemetry():
    """Initialize OpenTelemetry with Azure Monitor exporter if configured."""
    global _initialized
    if _initialized:
        return
    _initialized = True

    conn_str = settings.appinsights_connection_string
    if not conn_str:
        logger.info("No Application Insights connection string configured; telemetry disabled.")
        return

    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
        configure_azure_monitor(connection_string=conn_str)
        logger.info("Azure Monitor telemetry initialized.")
    except Exception as e:
        logger.warning("Failed to initialize Azure Monitor telemetry: %s", e)


def get_tracer(name: str = "sql-review-agent"):
    """Return an OpenTelemetry tracer for manual span creation."""
    try:
        from opentelemetry import trace
        return trace.get_tracer(name)
    except Exception:
        return None


def trace_agent(agent_name: str, input_sql: str, findings_count: int, verdict: str | None = None):
    """Create a span for an agent invocation."""
    tracer = get_tracer()
    if tracer is None:
        return

    with tracer.start_as_current_span(f"agent.{agent_name}") as span:
        span.set_attribute("agent.name", agent_name)
        span.set_attribute("agent.input_length", len(input_sql))
        span.set_attribute("agent.findings_count", findings_count)
        if verdict:
            span.set_attribute("agent.verdict", verdict)
