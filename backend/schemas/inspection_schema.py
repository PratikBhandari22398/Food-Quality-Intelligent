from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class InspectionEvaluateRequest(BaseModel):
    expected_product: str
    detected_product: str
    product_confidence: float
    packaging_condition: str
    condition_confidence: float
    ocr_data: Optional[Dict[str, Any]] = None
    milk_lab_params: Optional[Dict[str, Any]] = None
    batch_number: Optional[str] = None

class InspectionSaveRequest(InspectionEvaluateRequest):
    batch_id: Optional[int] = None
    image_base64: Optional[str] = None

class HumanReviewRequest(BaseModel):
    decision: str  # APPROVED, REJECTED, REINSPECT_REQUESTED
    reviewer: Optional[str] = "Quality Operator"
    comment: Optional[str] = None

class DecisionResult(BaseModel):
    final_status: str  # PASS, WARNING, HOLD, REJECT
    reasons: List[str]
    recommended_action: str
    detected_product: str
    product_confidence: float
    packaging_condition: str
    condition_confidence: float
    checklist: Dict[str, str]
    summary_card: Dict[str, Any]
    verified_nutrition: Optional[Dict[str, Any]] = None
    milk_params_eval: Optional[Dict[str, Any]] = None

class InspectionResponse(BaseModel):
    id: int
    batch_id: Optional[int] = None
    batch_number: Optional[str] = None
    image_path: Optional[str] = None
    expected_product: str
    detected_product: str
    product_confidence: float
    packaging_condition: str
    condition_confidence: float
    ocr_extracted: Optional[Dict[str, Any]] = None
    milk_lab_params: Optional[Dict[str, Any]] = None
    final_status: str
    status_reasons: List[str]
    recommended_action: Optional[str] = None
    checklist: Optional[Dict[str, str]] = None
    human_review_status: Optional[str] = None
    human_reviewer: Optional[str] = None
    human_comment: Optional[str] = None
    human_reviewed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

