from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any

class Log(BaseModel):
    timestamp: datetime
    service_name: str
    log_level: str = Field(...,pattern="^(DEBUG|INFO|WARN|ERROR)$")
    message: str
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    latency_ms: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None