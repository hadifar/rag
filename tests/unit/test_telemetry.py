from typing import Any

import pytest
from fastapi import FastAPI

from rag.adapters.telemetry import instrument_app
from rag.config import AzureMonitorTelemetryConfig, NoneTelemetryConfig


def _is_instrumented(app: FastAPI) -> bool:
    return getattr(app, "_is_instrumented_by_opentelemetry", False)


def test_no_telemetry_leaves_the_app_alone() -> None:
    app = FastAPI()

    instrument_app(app, NoneTelemetryConfig())

    assert not _is_instrumented(app)


def test_azure_monitor_exports_sampled_traces_and_instruments_the_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        "azure.monitor.opentelemetry.configure_azure_monitor",
        lambda **kwargs: calls.append(kwargs),  # pyright: ignore[reportUnknownLambdaType]
    )
    app = FastAPI()

    instrument_app(
        app,
        AzureMonitorTelemetryConfig(
            CONNECTION_STRING="InstrumentationKey=00000000-0000-0000-0000-000000000000",
            SAMPLING_RATIO=0.5,
        ),
    )

    [kwargs] = calls
    assert kwargs["sampling_ratio"] == 0.5
    assert kwargs["credential"] is not None
    assert kwargs["instrumentation_options"] == {"fastapi": {"enabled": False}}
    assert _is_instrumented(app)
