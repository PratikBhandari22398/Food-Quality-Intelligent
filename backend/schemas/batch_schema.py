from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class BatchBase(BaseModel):
    batch_number: str
    product_id: int
    mfg_date: Optional[str] = None
    exp_date: Optional[str] = None
    manufacture_date: Optional[str] = None
    expiry_date: Optional[str] = None
    expiry_rule_type: Optional[str] = "EXPLICIT_DATE"
    expiry_duration_months: Optional[int] = None
    expiry_source: Optional[str] = "LABEL_EXPLICIT"

class BatchCreate(BatchBase):
    pass

class BatchResponse(BatchBase):
    id: int
    status: str
    created_at: datetime
    product_name: Optional[str] = None
    inspection_count: Optional[int] = 0
    expiry_status: Optional[str] = "UNKNOWN"
    days_remaining: Optional[int] = None
    days_remaining_text: Optional[str] = "Unknown expiry"

    class Config:
        from_attributes = True

