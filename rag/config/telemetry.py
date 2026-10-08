from typing import Annotated, Literal

from pydantic import BaseModel, Field


class NoneTelemetryConfig(BaseModel):
    BACKEND: Literal["none"] = "none"


class AzureMonitorTelemetryConfig(BaseModel):
    """Sends requests, outbound calls, warnings and exceptions to Application Insights.

    Authenticates with DefaultAzureCredential: the resource has local auth off, so the
    connection string alone can't send anything and isn't a secret.
    """

    BACKEND: Literal["azure_monitor"] = "azure_monitor"
    CONNECTION_STRING: str
    # Share of request traces kept, to stay in the free 5 GB a month (free version :). Logged warnings
    # and exceptions are always sent.
    SAMPLING_RATIO: float = Field(default=0.25, gt=0, le=1)


TelemetryConfig = Annotated[
    NoneTelemetryConfig | AzureMonitorTelemetryConfig, Field(discriminator="BACKEND")
]
