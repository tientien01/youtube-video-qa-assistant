from typing import Literal

from pydantic import BaseModel


GenerationMode = Literal["llm", "fallback", "cached"]


class GenerationMetadata(BaseModel):
    generation_mode: GenerationMode
    provider: str
    fallback_reason: str | None = None
