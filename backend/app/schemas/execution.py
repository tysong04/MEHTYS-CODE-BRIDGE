from typing import Optional
from pydantic import BaseModel, Field


class ExecuteRequest(BaseModel):
    language: str = Field(..., description="Target language ('python' or 'javascript')")
    code: str = Field(..., min_length=1, max_length=32768, description="Code snippet to execute")
    stdin: Optional[str] = Field(default="", max_length=8192, description="Optional standard input to feed to the program")


class ExecuteResponse(BaseModel):
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: float
    timed_out: bool
    status: str
    disclaimer: str = Field(
        default="Executed in an isolated, resource-constrained sandbox with no access to server credentials or network.",
        description="Security disclosure"
    )
