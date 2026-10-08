"""The deployments set every upload limit (nginx needs them all), so their values must
match the backend's defaults, which a run without them (e.g. `uv run rag`) falls back to.
"""

import re
from pathlib import Path

import yaml

from rag.config import UploadsConfig

ROOT = Path(__file__).parents[2]
DEFAULTS = {
    f"UPLOADS__{name}": value for name, value in UploadsConfig().model_dump().items()
}


def test_docker_compose_sets_the_default_upload_limits() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())

    assert compose["x-upload-limits"] == DEFAULTS


def test_bicep_sets_the_default_upload_limits() -> None:
    bicep = (ROOT / "infra/azure/main.bicep").read_text()
    limits = re.findall(r"^\s*(UPLOADS__\w+): '(\d+)'$", bicep, re.MULTILINE)

    assert {name: int(value) for name, value in limits} == DEFAULTS
