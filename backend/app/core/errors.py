from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ApiError(Exception):
    status_code: int
    code: str
    message: str
    stage: str | None = None
    retryable: bool = False
    details: dict[str, Any] = field(default_factory=dict)
