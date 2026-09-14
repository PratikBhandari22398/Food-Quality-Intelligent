from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
import datetime

from backend.db.database import get_db
from backend.db.models import Inspection, Batch, Alert
from backend.services.expiry_service import update_all_batch_expiry_statuses, calculate_batch_expiry

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    expiry_summary = update_all_batch_expiry_statuses(db)

    total = db.query(Inspection).count()
    pass_count = db.query(Inspection).filter(Inspection.final_status == "PASS").count()
    warning_count = db.query(Inspection).filter(Inspection.final_status == "WARNING").count()
    hold_count = db.query(Inspection).filter(Inspection.final_status == "HOLD").count()
    reject_count = db.query(Inspection).filter(Inspection.final_status == "REJECT").count()

    recent_db = db.query(Inspection).order_by(Inspection.id.desc()).limit(5).all()
    recent_list = []
    for r in recent_db:
        b_num = r.batch.batch_number if r.batch else "General Batch"
        recent_list.append({
            "id": r.id,
            "batch_number": b_num,
            "product": r.detected_product,
            "condition": r.packaging_condition,
            "status": r.final_status,
            "created_at": r.created_at.strftime("%H:%M:%S | %d %b %Y")
        })

    # Combined active alerts (includes inspection alerts and expiry alerts)
    alerts_db = db.query(Alert).order_by(Alert.id.desc()).limit(8).all()
    alerts_list = []
    for a in alerts_db:
        alerts_list.append({
            "id": a.id,
            "status": a.status,
            "product": a.product_name,
            "reason": a.reason,
            "recommended_action": a.recommended_action,
            "time": a.created_at.strftime("%H:%M:%S")
        })
        
    # If no explicit Alert records exist, fallback to recent HOLD/REJECT inspections
    if not alerts_list:
        fallback_db = db.query(Inspection).filter(Inspection.final_status.in_(["HOLD", "REJECT"])).order_by(Inspection.id.desc()).limit(5).all()
        for f in fallback_db:
            reasons = f.get_reasons_list()
            reason_text = reasons[0] if reasons else "Quality Threshold Exception"
            alerts_list.append({
                "id": f.id,
                "status": f.final_status,
                "product": f.detected_product,
                "reason": reason_text,
                "recommended_action": "Review quality inspection details",
                "time": f.created_at.strftime("%H:%M:%S")
            })

    # Stock at risk batches (EXPIRING_SOON or EXPIRED)
    at_risk_db = db.query(Batch).filter(Batch.expiry_status.in_(["EXPIRING_SOON", "EXPIRED"])).all()
    at_risk_list = []
    for b in at_risk_db:
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
        at_risk_list.append({
            "id": b.id,
            "batch_number": b.batch_number,
            "product_name": prod_name,
            "expiry_date": calc["expiry_date"] or exp or "Unknown",
            "days_remaining": calc["days_remaining"],
            "days_remaining_text": calc["days_remaining_text"],
            "expiry_status": calc["expiry_status"]
        })
    at_risk_list.sort(key=lambda x: (x["days_remaining"] if x["days_remaining"] is not None else 9999))

    active_batch = db.query(Batch).filter(Batch.status == "ACTIVE").first()
    active_batch_str = active_batch.batch_number if active_batch else "No Active Batch"

    return {
        "total_inspections": total,
        "pass_count": pass_count,
        "warning_count": warning_count,
        "hold_count": hold_count,
        "reject_count": reject_count,
        "active_batch": active_batch_str,
        "recent_inspections": recent_list,
        "active_alerts": alerts_list,
        "expiry_summary": expiry_summary,
        "stock_at_risk": at_risk_list
    }


@router.get("/charts")
def get_dashboard_charts(db: Session = Depends(get_db)):
    pass_c = db.query(Inspection).filter(Inspection.final_status == "PASS").count()
    warn_c = db.query(Inspection).filter(Inspection.final_status == "WARNING").count()
    hold_c = db.query(Inspection).filter(Inspection.final_status == "HOLD").count()
    rejc_c = db.query(Inspection).filter(Inspection.final_status == "REJECT").count()

    pie_data = {
        "labels": ["PASS", "WARNING", "HOLD", "REJECT"],
        "data": [pass_c, warn_c, hold_c, rejc_c],
        "colors": ["#10B981", "#F59E0B", "#6366F1", "#EF4444"]
    }

    # Timeline mock / hourly trend data
    timeline_labels = ["09:00", "11:00", "13:00", "15:00", "17:00", "Current"]
    timeline_data = [
        db.query(Inspection).filter(Inspection.final_status == "PASS").count(),
        db.query(Inspection).filter(Inspection.final_status == "WARNING").count(),
        db.query(Inspection).filter(Inspection.final_status == "HOLD").count(),
        db.query(Inspection).filter(Inspection.final_status == "REJECT").count(),
        db.query(Inspection).count(),
        db.query(Inspection).count()
    ]

    return {
        "pie": pie_data,
        "timeline": {
            "labels": timeline_labels,
            "data": timeline_data
        }
    }
