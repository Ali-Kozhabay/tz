from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class StorageSignRequest(BaseModel):
    key: str
    method: Literal["get", "put"] = "get"


class StorageSignResponse(BaseModel):
    url: str
    expires_at: datetime
