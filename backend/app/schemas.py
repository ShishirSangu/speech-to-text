from datetime import datetime
from pydantic import BaseModel, ConfigDict


class TranscriptionIn(BaseModel):
    title: str = ""
    text: str = ""
    duration_sec: float = 0.0


class TranscriptionUpdate(BaseModel):
    title: str | None = None
    text: str | None = None


class TranscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    text: str
    duration_sec: float
    created_at: datetime
