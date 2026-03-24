"""
telemetry.py — OpenTelemetry instrumentation for AWS Bedrock observability.

Traces FastAPI requests and SQLAlchemy queries via OTLP HTTP export.
Set OTEL_EXPORTER_OTLP_ENDPOINT in .env to enable; no-op when unset.

Typical AWS setup: point the endpoint at the AWS Distro for OpenTelemetry
(ADOT) Collector sidecar, which forwards traces to X-Ray and metrics to
CloudWatch for Bedrock to consume.
"""
import logging
import os

logger = logging.getLogger(__name__)


def setup_telemetry(app, db_engine=None) -> None:
    """
    Initialise OpenTelemetry tracing and attach it to the FastAPI app.

    Reads configuration from environment variables:
      OTEL_EXPORTER_OTLP_ENDPOINT  — OTLP HTTP collector URL (required to enable)
      OTEL_SERVICE_NAME            — service name tag  (default: minesweeper.org)
      OTEL_EXPORTER_OTLP_HEADERS   — optional comma-separated key=value auth headers

    When OTEL_EXPORTER_OTLP_ENDPOINT is not set the function returns immediately
    so the app works normally in development without any OTEL infrastructure.
    """
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if not endpoint:
        logger.debug("OTEL_EXPORTER_OTLP_ENDPOINT not set — telemetry disabled")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as exc:
        logger.warning("OpenTelemetry packages not installed — telemetry disabled (%s)", exc)
        return

    service_name = os.environ.get("OTEL_SERVICE_NAME", "minesweeper.org")

    resource = Resource.create({
        "service.name":    service_name,
        "service.version": os.environ.get("OTEL_SERVICE_VERSION", "unknown"),
        "deployment.environment": os.environ.get("ENVIRONMENT", "unknown"),
    })

    provider = TracerProvider(resource=resource)

    # Parse optional auth headers (e.g. "x-api-key=secret,x-tenant=prod")
    raw_headers = os.environ.get("OTEL_EXPORTER_OTLP_HEADERS", "")
    headers = {}
    for pair in raw_headers.split(","):
        pair = pair.strip()
        if "=" in pair:
            k, _, v = pair.partition("=")
            headers[k.strip()] = v.strip()

    exporter = OTLPSpanExporter(endpoint=endpoint, headers=headers or None)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # Instrument FastAPI — captures every request as a span
    FastAPIInstrumentor.instrument_app(app)

    # Instrument SQLAlchemy — captures every DB query as a child span
    if db_engine is not None:
        try:
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
            SQLAlchemyInstrumentor().instrument(engine=db_engine)
        except ImportError:
            logger.warning("opentelemetry-instrumentation-sqlalchemy not installed — DB spans disabled")

    logger.info(
        "OpenTelemetry tracing enabled: service=%s endpoint=%s",
        service_name, endpoint,
    )
