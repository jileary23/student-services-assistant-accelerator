from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=4_000)
    conversation_id: str | None = Field(default=None, max_length=100)


class Citation(BaseModel):
    id: str
    title: str
    source_url: str | None = None
    excerpt: str


class Escalation(BaseModel):
    required: bool
    reason: str | None = None
    destination: str | None = None


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"]
    escalation: Escalation
    conversation_id: str


class RouteDecision(BaseModel):
    action: Literal["answer", "clarify", "escalate"]
    reason: str
