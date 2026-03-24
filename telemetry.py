"""
telemetry.py — OpenTelemetry instrumentation for minesweeper.org

Traces FastAPI requests and SQLAlchemy queries via OTLP HTTP export.
Emits custom game metrics (completions, durations) to CloudWatch via ADOT.

Set OTEL_EXPORTER_OTLP_ENDPOINT in .env to enable; no-op when unset.

AWS setup: point the endpoint at the ADOT Collector (localhost:4318),
which forwards traces → X-Ray and metrics → CloudWatch EMF.
"""
import logging
import os

logger = logging.getLogger(__name__)

# ── Module-level metric handles (populated by setup_telemetry) ────────────────
# Import these in main.py to record game events, e.g.:
#   from telemetry import record_game_complete, record_score_submit
#
#   record_score_submit("minesweeper", "expert")
#   record_game_complete("tentaizu", duration_ms=42000)

_games_completed   = None   # Counter  — puzzle completions by type + difficulty
_scores_submitted  = None   # Counter  — leaderboard submissions by mode
_game_duration     = None   # Histogram — time-to-complete in milliseconds
_active_duels      = None   # UpDownCounter — live PvP rooms
_scheduler_runs    = None   # Counter  — background job executions
_db_errors         = None   # Counter  — database errors caught in routes


def record_score_submit(game_type: str, mode: str) -> None:
    """Call from score submission routes to count leaderboard entries."""
    if _scores_submitted is not None:
        _scores_submitted.add(1, {"game.type": game_type, "game.mode": mode})


def record_game_complete(game_type: str, duration_ms: int | None = None,
                         mode: str = "unknown", won: bool = True) -> None:
    """Call when a puzzle/game is completed (win or loss)."""
    attrs = {"game.type": game_type, "game.mode": mode, "game.won": str(won)}
    if _games_completed is not None:
        _games_completed.add(1, attrs)
    if duration_ms is not None and _game_duration is not None:
        _game_duration.record(duration_ms, attrs)


def record_duel_delta(delta: int) -> None:
    """Call +1 when a duel room opens, -1 when it closes."""
    if _active_duels is not None:
        _active_duels.add(delta)


def record_scheduler_run(job_name: str, success: bool = True) -> None:
    """Call from scheduler jobs (collect_server_stats, reset_scores, etc.)."""
    if _scheduler_runs is not None:
        _scheduler_runs.add(1, {"job.name": job_name, "job.success": str(success)})


def record_db_error(operation: str) -> None:
    """Call from except blocks that catch DB errors."""
    if _db_errors is not None:
        _db_errors.add(1, {"db.operation": operation})


# ── Setup ─────────────────────────────────────────────────────────────────────

def setup_telemetry(app, db_engine=None) -> None:
    """
    Initialise OpenTelemetry tracing + metrics and attach to the FastAPI app.

    Reads configuration from environment / .env:
      OTEL_EXPORTER_OTLP_ENDPOINT  — OTLP HTTP collector URL (required to enable)
      OTEL_SERVICE_NAME            — service name tag  (default: minesweeper.org)
      OTEL_SERVICE_VERSION         — version string    (default: unknown)
      ENVIRONMENT                  — deployment.environment tag
      OTEL_EXPORTER_OTLP_HEADERS   — optional comma-separated key=value auth headers

    When OTEL_EXPORTER_OTLP_ENDPOINT is not set the function returns immediately
    so the app works normally in development without any OTEL infrastructure.
    """
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if not endpoint:
        logger.debug("OTEL_EXPORTER_OTLP_ENDPOINT not set — telemetry disabled")
        return

    # ── Core SDK imports ──────────────────────────────────────────────────────
    try:
        from opentelemetry import trace, metrics
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    except ImportError as exc:
        logger.warning("OpenTelemetry packages not installed — telemetry disabled (%s)", exc)
        return

    service_name = os.environ.get("OTEL_SERVICE_NAME", "minesweeper.org")
    resource = Resource.create({
        "service.name":           service_name,
        "service.version":        os.environ.get("OTEL_SERVICE_VERSION", "unknown"),
        "deployment.environment": os.environ.get("ENVIRONMENT", "unknown"),
    })

    # Parse optional auth headers (e.g. "x-api-key=secret,x-tenant=prod")
    raw_headers = os.environ.get("OTEL_EXPORTER_OTLP_HEADERS", "")
    headers: dict = {}
    for pair in raw_headers.split(","):
        pair = pair.strip()
        if "=" in pair:
            k, _, v = pair.partition("=")
            headers[k.strip()] = v.strip()

    # ── Tracing setup ─────────────────────────────────────────────────────────
    trace_exporter = OTLPSpanExporter(
        endpoint=f"{endpoint.rstrip('/')}/v1/traces",
        headers=headers or None,
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    trace.set_tracer_provider(provider)

    # ── Metrics setup ─────────────────────────────────────────────────────────
    metric_exporter = OTLPMetricExporter(
        endpoint=f"{endpoint.rstrip('/')}/v1/metrics",
        headers=headers or None,
    )
    reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=60_000)
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(meter_provider)

    meter = metrics.get_meter("minesweeper.game")

    # Populate module-level handles so helper functions above work
    global _games_completed, _scores_submitted, _game_duration
    global _active_duels, _scheduler_runs, _db_errors

    _games_completed = meter.create_counter(
        "minesweeper.games.completed",
        unit="1",
        description="Puzzle completions by game type and difficulty",
    )
    _scores_submitted = meter.create_counter(
        "minesweeper.scores.submitted",
        unit="1",
        description="Leaderboard score submissions by game mode",
    )
    _game_duration = meter.create_histogram(
        "minesweeper.game.duration_ms",
        unit="ms",
        description="Time to complete a puzzle in milliseconds",
    )
    _active_duels = meter.create_up_down_counter(
        "minesweeper.duels.active",
        unit="1",
        description="Number of active PvP duel rooms",
    )
    _scheduler_runs = meter.create_counter(
        "minesweeper.scheduler.runs",
        unit="1",
        description="Background scheduler job executions",
    )
    _db_errors = meter.create_counter(
        "minesweeper.db.errors",
        unit="1",
        description="Database errors caught in route handlers",
    )

    # ── FastAPI auto-instrumentation ──────────────────────────────────────────
    FastAPIInstrumentor.instrument_app(app)

    # ── Outbound HTTP spans (httpx / requests) ────────────────────────────────
    try:
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
        RequestsInstrumentor().instrument()
    except ImportError:
        logger.warning("opentelemetry-instrumentation-requests not installed — HTTP spans disabled")

    # ── Log correlation (injects trace_id/span_id into every log record) ──────
    try:
        from opentelemetry.instrumentation.logging import LoggingInstrumentor
        LoggingInstrumentor().instrument(set_logging_format=True)
    except ImportError:
        logger.warning("opentelemetry-instrumentation-logging not installed — log correlation disabled")

    # ── SQLAlchemy query spans ────────────────────────────────────────────────
    if db_engine is not None:
        try:
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
            SQLAlchemyInstrumentor().instrument(engine=db_engine)
        except ImportError:
            logger.warning("opentelemetry-instrumentation-sqlalchemy not installed — DB spans disabled")

    logger.info(
        "OpenTelemetry enabled: service=%s endpoint=%s",
        service_name, endpoint,
    )
