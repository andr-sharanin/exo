import uuid

from pydantic import BaseModel, ConfigDict, field_validator

# Default types still validated at schema level.
# Dynamic DB-based types are checked in AgentService.is_valid_entity_type()
# for sessions created via API — schema allows any string, service validates.
_VALID_SESSION_MODES = frozenset(["advisory", "reflection", "planning", "focus"])


class AgentSessionCreate(BaseModel):
    entity_type: str
    session_mode: str

    @field_validator("session_mode")
    @classmethod
    def validate_session_mode(cls, v: str) -> str:
        if v not in _VALID_SESSION_MODES:
            raise ValueError(f"session_mode must be one of {sorted(_VALID_SESSION_MODES)}")
        return v


class AgentSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entity_type: str
    session_mode: str
    status: str


class AgentMessageCreate(BaseModel):
    content: str
    # Optional: inject current task context (for LifeWorm in-task advisor calls)
    task_context: dict | None = None


class AgentMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    message_order: int
    model_used: str | None
