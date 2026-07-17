from typing import Literal

from pydantic import BaseModel


class RuntimeComponentResponse(BaseModel):
    status: Literal["available", "unavailable"]
    label: str
    provider: str | None = None
    model: str | None = None
    detail: str | None = None


class RuntimeHealthResponse(BaseModel):
    status: Literal["operational", "degraded"]
    api: RuntimeComponentResponse
    sqlite: RuntimeComponentResponse
    vector_index: RuntimeComponentResponse
    llm: RuntimeComponentResponse
    database_size_bytes: int | None = None
