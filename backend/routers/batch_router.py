from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.db.database import get_db
from backend.db.models import Batch, Product, Inspection
from backend.schemas.batch_schema import BatchCreate, BatchResponse
from backend.services.expiry_service import update_all_batch_expiry_statuses, calculate_batch_expiry

router = APIRouter(prefix="/api/batches", tags=["Batches"])

@router.get("", response_model=List[BatchResponse])
def get_batches(db: Session = Depends(get_db)):
    update_all_batch_expiry_statuses(db)
    batches = db.query(Batch).order_by(Batch.id.desc()).all()
    if not batches:
        # Seed default initial batch if empty
        prod = db.query(Product).first()
        if not prod:
            from backend.routers.product_router import get_products
            get_products(db)
            prod = db.query(Product).first()
        
        default_batch = Batch(
            batch_number="BAT-2026-CHIPS-01",
            product_id=prod.id,
            mfg_date="2026-09-01",
            exp_date="2027-03-01",
            manufacture_date="2026-09-01",
            expiry_date="2027-03-01",
            expiry_rule_type="EXPLICIT_DATE",
            expiry_source="USER_MANUAL",
            expiry_status="NORMAL",
            status="ACTIVE"
        )
        db.add(default_batch)
        db.commit()
        batches = db.query(Batch).all()

    result = []
    for b in batches:
        prod_name = b.product.name if b.product else "Unknown Product"
        insp_count = db.query(Inspection).filter(Inspection.batch_id == b.id).count()
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
        result.append(BatchResponse(
            id=b.id,
            batch_number=b.batch_number,
            product_id=b.product_id,
            mfg_date=mfg,
            exp_date=calc["expiry_date"] or exp,
            manufacture_date=mfg,
            expiry_date=calc["expiry_date"] or exp,
            expiry_rule_type=b.expiry_rule_type or "EXPLICIT_DATE",
            expiry_duration_months=b.expiry_duration_months,
            expiry_source=calc["expiry_source"],
            expiry_status=calc["expiry_status"],
            days_remaining=calc["days_remaining"],
            days_remaining_text=calc["days_remaining_text"],
            status=b.status,
            created_at=b.created_at,
            product_name=prod_name,
            inspection_count=insp_count
        ))
    return result

@router.post("", response_model=BatchResponse)
def create_batch(batch_in: BatchCreate, db: Session = Depends(get_db)):
    existing = db.query(Batch).filter(Batch.batch_number == batch_in.batch_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Batch number already exists.")

    product = db.query(Product).filter(Product.id == batch_in.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Selected Product ID not found.")

    mfg_date_val = batch_in.manufacture_date or batch_in.mfg_date
    exp_date_val = batch_in.expiry_date or batch_in.exp_date

    calc = calculate_batch_expiry(
        manufacture_date_str=mfg_date_val,
        expiry_date_str=exp_date_val,
        expiry_rule_type=batch_in.expiry_rule_type,
        expiry_duration_months=batch_in.expiry_duration_months,
        product_name=product.name,
        expiry_source=batch_in.expiry_source or "USER_MANUAL"
    )

    # Mark existing active batches as INACTIVE if creating a new active one
    db.query(Batch).filter(Batch.status == "ACTIVE").update({"status": "INACTIVE"})

    new_batch = Batch(
        batch_number=batch_in.batch_number,
        product_id=batch_in.product_id,
        mfg_date=mfg_date_val,
        exp_date=calc["expiry_date"] or exp_date_val,
        manufacture_date=mfg_date_val,
        expiry_date=calc["expiry_date"] or exp_date_val,
        expiry_rule_type=batch_in.expiry_rule_type or "EXPLICIT_DATE",
        expiry_duration_months=batch_in.expiry_duration_months,
        expiry_source=calc["expiry_source"],
        expiry_status=calc["expiry_status"],
        status="ACTIVE"
    )
    db.add(new_batch)
    db.commit()
    db.refresh(new_batch)
    
    update_all_batch_expiry_statuses(db)

    return BatchResponse(
        id=new_batch.id,
        batch_number=new_batch.batch_number,
        product_id=new_batch.product_id,
        mfg_date=new_batch.manufacture_date,
        exp_date=new_batch.expiry_date,
        manufacture_date=new_batch.manufacture_date,
        expiry_date=new_batch.expiry_date,
        expiry_rule_type=new_batch.expiry_rule_type,
        expiry_duration_months=new_batch.expiry_duration_months,
        expiry_source=new_batch.expiry_source,
        expiry_status=calc["expiry_status"],
        days_remaining=calc["days_remaining"],
        days_remaining_text=calc["days_remaining_text"],
        status=new_batch.status,
        created_at=new_batch.created_at,
        product_name=product.name,
        inspection_count=0
    )

@router.put("/{batch_id}/activate")
def activate_batch(batch_id: int, db: Session = Depends(get_db)):
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")
    
    # Atomically deactivate all active batches and activate selected batch
    db.query(Batch).filter(Batch.status == "ACTIVE").update({"status": "INACTIVE"})
    batch.status = "ACTIVE"
    db.commit()
    return {"message": f"Batch {batch.batch_number} is now ACTIVE."}


