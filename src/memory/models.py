"""
YeyoOS — Modelos de Flash Memory
Micro-fase 2.1 — Capa 2: Cerebro
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class Memory(BaseModel):
    """Representa una memoria individual en Flash Memory."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    type: str = Field(..., pattern="^(conversation|preference|fact|correction|skill)$")
    tier: str = Field(default="WARM", pattern="^(HOT|WARM|COLD)$")
    embedding: Optional[list[float]] = None
    checksum: str = ""
    access_count: int = 0
    metadata: dict = Field(default_factory=dict)
    source: str = "user"
    namespace: str = "chat:usuario"
    created_at: Optional[datetime] = None
    accessed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
