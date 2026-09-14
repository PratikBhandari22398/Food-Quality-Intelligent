import base64
import json
import uuid
import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.db.database import get_db
from backend.db.models import Inspection, Batch, Product, NutritionRecord, Alert
from backend.schemas.inspection_schema import (
    InspectionEvaluateRequest,
    InspectionSaveRequest,
    HumanReviewRequest,
    DecisionResult,
    InspectionResponse
)
from backend.services.ocr_service import OCRService
from backend.services.decision_engine import DecisionEngine
from backend.services.nutrition_verifier import NutritionVerifier
from backend.config import UPLOADS_DIR, DEFAULT_NUTRITION_PROFILES

router = APIRouter(prefix="/api/inspect", tags=["Inspection"])

@router.post("/ocr")
async def process_ocr(
    file: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    expected_product: Optional[str] = Form("Chips Packet"),
    ai_detected_product: Optional[str] = Form("Chips Packet"),
    db: Session = Depends(get_db)
):
    """
    Accepts an uploaded image file (back-side label), performs OCR, parses nutrition table,
    and runs database verification vs expected product records.
    """
    upload_file = file or image
    contents = b""
    if upload_file:
        contents = await upload_file.read()
    
    print(f"[OCR UPLOAD RECEIVED]: filename={upload_file.filename if upload_file else None}, content_type={upload_file.content_type if upload_file else None}, size={len(contents)}")

    if not upload_file:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "error_type": "missing_image",
                "message": "No label image was received."
            }
        )
    
    ocr_result = OCRService.process_image(contents)

    # Database Lookup for Verified Nutrition
    db_product = db.query(Product).filter(Product.name == expected_product).first()
    db_nutrition = db_product.get_nutrition_json() if db_product else DEFAULT_NUTRITION_PROFILES.get(expected_product, {})

    # OCR vs Database Verification
    ocr_vs_db = NutritionVerifier.verify_ocr_vs_database(db_nutrition, ocr_result["nutrition_data"])

    # Product Consistency Verification
    consistency = NutritionVerifier.verify_product_consistency(expected_product, ai_detected_product, ocr_result["product_name"])

    # Nutrition Reference Screening
    category = db_product.category if db_product else ("Milk" if "Milk" in expected_product else "Chips")
    reference_check = NutritionVerifier.evaluate_nutrition_reference(ocr_result["nutrition_data"], category=category)

    # Attach mismatch flags to ocr_result
    ocr_result["has_nutrition_mismatch"] = ocr_vs_db.get("has_mismatch", False)
    ocr_result["ocr_vs_db_status"] = ocr_vs_db.get("overall_status")

    return {
        "ocr_status": ocr_result["ocr_status"],
        "ocr_status_display": ocr_result["ocr_status_display"],
        "nutrition_status": ocr_result["nutrition_status"],
        "date_status": ocr_result.get("date_status", "not_detected"),
        "batch_status": ocr_result.get("batch_status", "not_detected"),
        "net_quantity_status": ocr_result.get("net_quantity_status", "not_detected"),
        "fields": ocr_result["fields"],
        "nutrition_data": ocr_result["nutrition_data"],
        "debug_info": ocr_result.get("debug_info", {}),
        "system_error": ocr_result.get("system_error", False),
        "ocr_result": ocr_result,
        "ocr_vs_database": ocr_vs_db,
        "consistency_check": consistency,
        "reference_check": reference_check,
        "source": "OCR From Package",
        "disclaimer": "Nutrition values are checked against configured reference values and product records. This does not independently certify food safety."
    }

import re

@router.get("/product-profile/{variant_name}")
def get_product_profile(variant_name: str, db: Session = Depends(get_db)):
    """
    Fetches exact verified product profile and nutrition record from database.
    Calculates per-serving and per-pack displays.
    """
    prod = db.query(Product).filter(Product.name == variant_name).first()
    profile = DEFAULT_NUTRITION_PROFILES.get(variant_name)

    if not prod and not profile:
        if "Chips" in variant_name:
            profile = DEFAULT_NUTRITION_PROFILES.get("Chips Packet") or DEFAULT_NUTRITION_PROFILES.get("Lay's Classic Salted")
        elif "Milk" in variant_name:
            profile = DEFAULT_NUTRITION_PROFILES.get("Milk Pouch") or DEFAULT_NUTRITION_PROFILES.get("Pure Dairy Toned Milk")
        else:
            raise HTTPException(status_code=404, detail=f"Product profile for '{variant_name}' not found.")

    if not profile:
        profile = {}

    mrp = prod.mrp if (prod and prod.mrp) else profile.get("mrp", "₹20")
    net_weight = prod.net_weight if (prod and prod.net_weight) else profile.get("net_weight", "50 g")
    serving_size = prod.serving_size if (prod and prod.serving_size) else profile.get("serving_size", "20 g")
    category = prod.category if prod else profile.get("category", "Chips")
    basis = profile.get("basis", "Per 100 g")
    nutrition_table = prod.get_nutrition_json() if (prod and prod.standard_nutrition) else profile.get("nutrition_table", {})
    source = profile.get("source", "Verified Product Label")

    def calc_derived(table: dict, factor: float):
        derived = {}
        for k, v in table.items():
            val_match = re.search(r'([\d\.]+)', str(v))
            if val_match:
                num = float(val_match.group(1)) * factor
                unit = re.sub(r'[\d\.\s]+', '', str(v))
                derived[k] = f"{round(num, 1)} {unit}".strip()
            else:
                derived[k] = str(v)
        return derived

    serving_num = 20.0
    s_match = re.search(r'([\d\.]+)', str(serving_size))
    if s_match:
        serving_num = float(s_match.group(1))

    net_num = 50.0
    n_match = re.search(r'([\d\.]+)', str(net_weight))
    if n_match:
        net_num = float(n_match.group(1))

    per_serving_table = calc_derived(nutrition_table, serving_num / 100.0)
    per_pack_table = calc_derived(nutrition_table, net_num / 100.0)

    prof_data = {
        "variant_name": variant_name,
        "category": category,
        "mrp": mrp,
        "net_weight": net_weight,
        "serving_size": serving_size,
        "nutrition_basis": basis,
        "nutrition_source": source,
        "nutrition_per_100g": nutrition_table,
        "nutrition_table": nutrition_table,
        "per_serving_table": per_serving_table,
        "per_pack_table": per_pack_table
    }

    return {
        "success": True,
        "status": "success",
        "profile": prof_data,
        **prof_data
    }

@router.post("/evaluate", response_model=DecisionResult)
def evaluate_inspection(req: InspectionEvaluateRequest):
    """
    Executes automated decision rules given AI classification and lab/OCR parameters.
    """
    result = DecisionEngine.evaluate(
        expected_product=req.expected_product,
        detected_product=req.detected_product,
        product_confidence=req.product_confidence,
        packaging_condition=req.packaging_condition,
        condition_confidence=req.condition_confidence,
        ocr_data=req.ocr_data,
        milk_lab_params=req.milk_lab_params,
        batch_number=req.batch_number
    )
    
    return DecisionResult(
        final_status=result["final_status"],
        reasons=result["reasons"],
        recommended_action=result["recommended_action"],
        detected_product=result["detected_product"],
        product_confidence=result["product_confidence"],
        packaging_condition=result["packaging_condition"],
        condition_confidence=result["condition_confidence"],
        checklist=result["checklist"],
        summary_card=result["summary_card"],
        verified_nutrition=result["verified_nutrition"],
        milk_params_eval=result["milk_params_eval"]
    )

@router.post("/save", response_model=InspectionResponse)
def save_inspection(req: InspectionSaveRequest, db: Session = Depends(get_db)):
    """
    Saves an inspection record into SQLite, stores snapshot image on disk,
    and automatically creates a risk alert if status is WARNING, HOLD, or REJECT.
    """
    eval_res = DecisionEngine.evaluate(
        expected_product=req.expected_product,
        detected_product=req.detected_product,
        product_confidence=req.product_confidence,
        packaging_condition=req.packaging_condition,
        condition_confidence=req.condition_confidence,
        ocr_data=req.ocr_data,
        milk_lab_params=req.milk_lab_params,
        batch_number=req.batch_number
    )

    image_rel_path = None
    if req.image_base64:
        try:
            if "," in req.image_base64:
                header, encoded = req.image_base64.split(",", 1)
            else:
                encoded = req.image_base64
            img_data = base64.b64decode(encoded)
            filename = f"insp_{uuid.uuid4().hex[:8]}.jpg"
            file_path = UPLOADS_DIR / filename
            with open(file_path, "wb") as f:
                f.write(img_data)
            image_rel_path = f"/uploads/{filename}"
        except Exception as e:
            print(f"Error saving image snapshot: {e}")

    batch_id = req.batch_id
    batch_number_val = req.batch_number
    if not batch_id and batch_number_val:
        b = db.query(Batch).filter(Batch.batch_number == batch_number_val).first()
        if b:
            batch_id = b.id

    new_inspection = Inspection(
        batch_id=batch_id,
        image_path=image_rel_path,
        expected_product=req.expected_product,
        detected_product=req.detected_product,
        product_confidence=req.product_confidence,
        packaging_condition=req.packaging_condition,
        condition_confidence=req.condition_confidence,
        ocr_extracted_json=json.dumps(req.ocr_data) if req.ocr_data else None,
        milk_lab_params_json=json.dumps(req.milk_lab_params) if req.milk_lab_params else None,
        final_status=eval_res["final_status"],
        status_reasons=json.dumps(eval_res["reasons"]),
        data_source="LIVE INSPECTION"
    )

    db.add(new_inspection)
    db.commit()
    db.refresh(new_inspection)

    # Requirement 8: Create Risk Alert for WARNING, HOLD, or REJECT status
    if eval_res["final_status"] in ("WARNING", "HOLD", "REJECT"):
        new_alert = Alert(
            inspection_id=new_inspection.id,
            batch_number=batch_number_val or "General Batch",
            product_name=req.expected_product,
            status=eval_res["final_status"],
            reason=eval_res["reasons"][0] if eval_res["reasons"] else "Quality alert triggered.",
            recommended_action=eval_res["recommended_action"]
        )
        db.add(new_alert)
        db.commit()

    return InspectionResponse(
        id=new_inspection.id,
        batch_id=new_inspection.batch_id,
        batch_number=batch_number_val,
        image_path=new_inspection.image_path,
        expected_product=new_inspection.expected_product,
        detected_product=new_inspection.detected_product,
        product_confidence=new_inspection.product_confidence,
        packaging_condition=new_inspection.packaging_condition,
        condition_confidence=new_inspection.condition_confidence,
        ocr_extracted=new_inspection.get_ocr_json(),
        milk_lab_params=new_inspection.get_milk_params_json(),
        final_status=new_inspection.final_status,
        status_reasons=new_inspection.get_reasons_list(),
        recommended_action=eval_res["recommended_action"],
        checklist=eval_res["checklist"],
        human_review_status=new_inspection.human_review_status,
        human_reviewer=new_inspection.human_reviewer,
        human_comment=new_inspection.human_comment,
        human_reviewed_at=new_inspection.human_reviewed_at,
        created_at=new_inspection.created_at
    )

@router.post("/human-review/{inspection_id}", response_model=InspectionResponse)
def submit_human_review(
    inspection_id: int,
    review_req: HumanReviewRequest,
    db: Session = Depends(get_db)
):
    """
    Requirement 9: Records Human Operator Review (APPROVED, REJECTED, REINSPECT_REQUESTED)
    for HOLD or critical quality cases.
    """
    insp = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not insp:
        raise HTTPException(status_code=404, detail="Inspection record not found.")

    insp.human_review_status = review_req.decision
    insp.human_reviewer = review_req.reviewer or "Quality Operator"
    insp.human_comment = review_req.comment
    insp.human_reviewed_at = datetime.datetime.utcnow()

    db.commit()
    db.refresh(insp)

    b_num = insp.batch.batch_number if insp.batch else "General Batch"
    return InspectionResponse(
        id=insp.id,
        batch_id=insp.batch_id,
        batch_number=b_num,
        image_path=insp.image_path,
        expected_product=insp.expected_product,
        detected_product=insp.detected_product,
        product_confidence=insp.product_confidence,
        packaging_condition=insp.packaging_condition,
        condition_confidence=insp.condition_confidence,
        ocr_extracted=insp.get_ocr_json(),
        milk_lab_params=insp.get_milk_params_json(),
        final_status=insp.final_status,
        status_reasons=insp.get_reasons_list(),
        human_review_status=insp.human_review_status,
        human_reviewer=insp.human_reviewer,
        human_comment=insp.human_comment,
        human_reviewed_at=insp.human_reviewed_at,
        created_at=insp.created_at
    )

@router.get("/alerts")
def get_active_alerts(db: Session = Depends(get_db)):
    """
    Returns list of recent risk alerts for the dashboard feed.
    """
    alerts = db.query(Alert).order_by(Alert.id.desc()).limit(20).all()
    return alerts

@router.get("/history", response_model=List[InspectionResponse])
def get_inspections(
    batch_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(Inspection)
    if batch_id:
        query = query.filter(Inspection.batch_id == batch_id)
    if status:
        query = query.filter(Inspection.final_status == status.upper())

    inspections = query.order_by(Inspection.id.desc()).limit(limit).all()

    result = []
    for insp in inspections:
        b_num = insp.batch.batch_number if insp.batch else "General Batch"
        result.append(InspectionResponse(
            id=insp.id,
            batch_id=insp.batch_id,
            batch_number=b_num,
            image_path=insp.image_path,
            expected_product=insp.expected_product,
            detected_product=insp.detected_product,
            product_confidence=insp.product_confidence,
            packaging_condition=insp.packaging_condition,
            condition_confidence=insp.condition_confidence,
            ocr_extracted=insp.get_ocr_json(),
            milk_lab_params=insp.get_milk_params_json(),
            final_status=insp.final_status,
            status_reasons=insp.get_reasons_list(),
            human_review_status=insp.human_review_status,
            human_reviewer=insp.human_reviewer,
            human_comment=insp.human_comment,
            human_reviewed_at=insp.human_reviewed_at,
            created_at=insp.created_at
        ))
    return result

@router.get("/{inspection_id}", response_model=InspectionResponse)
def get_inspection_detail(inspection_id: int, db: Session = Depends(get_db)):
    insp = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not insp:
        raise HTTPException(status_code=404, detail="Inspection record not found.")

    b_num = insp.batch.batch_number if insp.batch else "General Batch"
    return InspectionResponse(
        id=insp.id,
        batch_id=insp.batch_id,
        batch_number=b_num,
        image_path=insp.image_path,
        expected_product=insp.expected_product,
        detected_product=insp.detected_product,
        product_confidence=insp.product_confidence,
        packaging_condition=insp.packaging_condition,
        condition_confidence=insp.condition_confidence,
        ocr_extracted=insp.get_ocr_json(),
        milk_lab_params=insp.get_milk_params_json(),
        final_status=insp.final_status,
        status_reasons=insp.get_reasons_list(),
        human_review_status=insp.human_review_status,
        human_reviewer=insp.human_reviewer,
        human_comment=insp.human_comment,
        human_reviewed_at=insp.human_reviewed_at,
        created_at=insp.created_at
    )

