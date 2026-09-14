from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from backend.db.database import get_db
from backend.db.models import Batch
from backend.services.expiry_service import update_all_batch_expiry_statuses, calculate_batch_expiry

router = APIRouter(prefix="/api/expiry", tags=["Expiry Monitoring"])

@router.get("/summary")
def get_expiry_summary(db: Session = Depends(get_db)):
    """Returns total batch counts grouped by expiry status: NORMAL, EXPIRING_SOON, EXPIRED, UNKNOWN."""
    summary = update_all_batch_expiry_statuses(db)
    return summary

@router.get("/at-risk")
def get_stock_at_risk(db: Session = Depends(get_db)):
    """Returns batches that are EXPIRING_SOON or EXPIRED, sorted by earliest expiry date."""
    update_all_batch_expiry_statuses(db)
    batches = db.query(Batch).filter(Batch.expiry_status.in_(["EXPIRING_SOON", "EXPIRED"])).all()
    
    result = []
    for b in batches:
        prod_name = b.product.name if b.product else "Unknown Product"
        mfg = b.manufacture_date or b.mfg_date
        exp = b.expiry_date or b.exp_date
        calc = calculate_batch_expiry(
            manufacture_date_str=mfg,
            expiry_date_str=exp,
            expiry_rule_type=b.expiry_rule_type,
            expiry_duration_months=b.expiry_duration_months,
            product_name=prod_name,
            expiry_source=b.expiry_source
        )
        result.append({
            "id": b.id,
            "batch_number": b.batch_number,
            "product_name": prod_name,
            "manufacture_date": mfg,
            "expiry_date": calc["expiry_date"] or exp,
            "days_remaining": calc["days_remaining"],
            "days_remaining_text": calc["days_remaining_text"],
            "expiry_status": calc["expiry_status"],
            "expiry_source": calc["expiry_source"]
        })

    # Sort by days_remaining ascending (earliest expiry date first)
    result.sort(key=lambda x: (x["days_remaining"] if x["days_remaining"] is not None else 9999))
    return result

@router.get("/expired")
def get_expired_batches(db: Session = Depends(get_db)):
    """Returns list of EXPIRED batches."""
    update_all_batch_expiry_statuses(db)
    batches = db.query(Batch).filter(Batch.expiry_status == "EXPIRED").all()
    
    result = []
    for b in batches:
        prod_name = b.product.name if b.product else "Unknown Product"
        mfg = b.manufacture_date or b.mfg_date
        exp = b.expiry_date or b.exp_date
        calc = calculate_batch_expiry(
            manufacture_date_str=mfg,
            expiry_date_str=exp,
            expiry_rule_type=b.expiry_rule_type,
            expiry_duration_months=b.expiry_duration_months,
            product_name=prod_name,
            expiry_source=b.expiry_source
        )
        result.append({
            "id": b.id,
            "batch_number": b.batch_number,
            "product_name": prod_name,
            "expiry_date": calc["expiry_date"] or exp,
            "days_remaining_text": calc["days_remaining_text"],
            "expiry_status": "EXPIRED"
        })
    return result
