from pydantic import BaseModel


class AutoGenStatus(BaseModel):
    enabled: bool
    framework: str
    version: str
    model: str
    local_only: bool = True
    archived: bool = True
    code_execution_enabled: bool = False

