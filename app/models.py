from typing import Any, Dict, Optional

from pydantic import BaseModel


class CodeRequest(BaseModel):
    code: str


class CommandRequestModel(BaseModel):
    command: str
    parameters: Optional[Dict[str, Any]] = None
