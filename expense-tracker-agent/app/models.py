from typing import Literal

from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: str
    user_id: int
    message: str


class ChatResponse(BaseModel):
    reply: str


class IntentResult(BaseModel):
    """What the intent classifier must return (the LLM is forced to fill this)."""
    intent: Literal["domain", "non_domain"]
