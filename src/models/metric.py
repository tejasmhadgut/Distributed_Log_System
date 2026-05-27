from pydantic import BaseModel
from datetime import datetime

class Metric(BaseModel):
    timestamp: datetime
    service_name: str
    request_count: int
    error_count: int
    error_rate: float
    latency_p95: int

    