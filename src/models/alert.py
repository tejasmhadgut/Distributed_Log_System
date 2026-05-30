from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AlertRuleCreate(BaseModel):
    service_name: str
    metric_type: str 
    threshold: float
    enabled: bool = True

class AlertRuleUpdate(BaseModel):
    threshold: Optional[float] = None
    enabled: Optional[bool] = None

class AlertRuleResponse(BaseModel):
    rule_id: int
    service_name: str
    metric_type: str
    threshold: float
    enabled: bool
    created_at: datetime
    updated_at: datetime

class AlertResponse(BaseModel):
    alert_id: int
    rule_id: int
    service_name: str
    trace_id: Optional[str]
    metric_type: str
    threshold: float
    actual_value: float
    state: str  # "FIRING" or "RESOLVED"
    created_at: datetime
    resolved_at: Optional[datetime]
    acknowledged_at: Optional[datetime]
    webhook_status: str

    