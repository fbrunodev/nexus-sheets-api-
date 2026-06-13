from pydantic import BaseModel
from datetime import datetime


class PlatformCreate(BaseModel):
    """Dados para criar uma nova plataforma."""

    name: str



class PlatformResponse(BaseModel):
    """Dados para criar uma nova plataforma."""
    id:str
    name: str
    created_at: datetime


    model_config = {"from_attributes": True}
    