import logging
from typing import Optional

from fastapi import FastAPI

from app.core.config import settings

logger = logging.getLogger("app.tracing")


def configure_tracing(app: FastAPI) -> None:
    """Initialize OpenTelemetry tracing for the FastAPI application."""
    try:
        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SpanExporter
    except ImportError:
        logger.warning("OpenTelemetry dependencies are not installed; tracing is disabled.")
        return

    if not getattr(settings, "ENABLE_TRACING", True):
        logger.info("Tracing is disabled via settings.ENABLE_TRACING.")
        return

    resource = Resource.create({
        "service.name": getattr(settings, "OTEL_SERVICE_NAME", settings.PROJECT_NAME),
        "service.version": settings.VERSION,
        "deployment.environment": settings.ENVIRONMENT,
    })

    provider = TracerProvider(resource=resource)

    try:
        from opentelemetry.sdk.trace.export import OTLPSpanExporter

        endpoint = getattr(settings, "OTEL_EXPORTER_OTLP_ENDPOINT", None) or None
        if endpoint:
            exporter: SpanExporter = OTLPSpanExporter(endpoint=endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        else:
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    except Exception:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)

    try:
        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    except Exception:
        logger.exception("Failed to instrument FastAPI app for tracing.")

    try:
        SQLAlchemyInstrumentor().instrument(enable_commenter=True, tracer_provider=provider)
    except Exception:
        logger.exception("Failed to instrument SQLAlchemy for tracing.")

    try:
        RequestsInstrumentor().instrument(tracer_provider=provider)
    except Exception:
        logger.exception("Failed to instrument requests for tracing.")

    logger.info("Tracing initialized for %s", getattr(settings, "OTEL_SERVICE_NAME", settings.PROJECT_NAME))
