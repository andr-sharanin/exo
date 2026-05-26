"""
Shared Pydantic base models for all canonical object schemas.
"""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditedResponse(BaseModel):
    """Base response envelope matching AuditedModel fields."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime
    schema_version: int
    sensitivity_class: str


class TransitionRequest(BaseModel):
    action: str
    metadata: dict[str, Any] | None = None


class TransitionResponse(BaseModel):
    id: uuid.UUID
    object_type: str
    previous_status: str
    current_status: str
    allowed_next_actions: list[str]


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    limit: int
    offset: int
