from fastapi import FastAPI

from rag.config import (
    AzureMonitorTelemetryConfig,
    NoneTelemetryConfig,
    TelemetryConfig,
)


def _instrument_azure_monitor(
    app: FastAPI, config: AzureMonitorTelemetryConfig
) -> None:
    from azure.identity import DefaultAzureCredential
    from azure.monitor.opentelemetry import (
        configure_azure_monitor,  # pyright: ignore[reportUnknownVariableType] — its **kwargs are untyped
    )
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    configure_azure_monitor(
        connection_string=config.CONNECTION_STRING,
        credential=DefaultAzureCredential(),
        sampling_ratio=config.SAMPLING_RATIO,
        enable_performance_counters=False,
        instrumentation_options={"fastapi": {"enabled": False}},
    )
    FastAPIInstrumentor.instrument_app(app)


def instrument_app(app: FastAPI, config: TelemetryConfig) -> None:
    """Export this process's telemetry. Once per process: it sets global providers."""
    match config:
        case NoneTelemetryConfig():
            pass
        case AzureMonitorTelemetryConfig():
            _instrument_azure_monitor(app, config)
