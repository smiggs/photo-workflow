"""Configuration precedence: defaults, JSON file, explicit overrides."""

import json
from pathlib import Path
from typing import Annotated

from pydantic import Field

from .models import Record


class Configuration(Record):
    tool_timeout_seconds: Annotated[float, Field(gt=0, le=600)] = 30
    raw_extensions: tuple[str, ...] = ('.arw', '.cr2', '.cr3', '.dng', '.nef', '.orf', '.pef', '.raf', '.rw2', '.srw')
    representatives_per_cohort: Annotated[int, Field(ge=1, le=100)] = 1


def load_config(path: Path | None = None, overrides: dict | None = None) -> Configuration:
    try:
        values = json.loads(Path(path).read_text(encoding='utf-8')) if path is not None else {}
    except OSError as error:
        raise ValueError('configuration file is missing or unreadable') from error
    if not isinstance(values, dict):
        raise ValueError('configuration must be a JSON object')
    return Configuration.model_validate({**values, **(overrides or {})})
