import datetime
import calendar
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from backend.config import EXPIRY_WARNING_DAYS
from backend.db.models import Batch, Alert, Product

def parse_date_string(date_str: Optional[str]) -> Optional[datetime.date]:
    """Parse various date string formats safely into datetime.date."""
    if not date_str or not isinstance(date_str, str):
        return None
    
    clean_str = date_str.strip()
    if not clean_str:
        return None
    
    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%d %b %Y",
        "%d %B %Y"
    ]
    
    for fmt in formats:
        try:
            return datetime.datetime.strptime(clean_str, fmt).date()
        except ValueError:
            continue
            
    return None

def format_date_iso(date_obj: datetime.date) -> str:
    """Format datetime.date into standard YYYY-MM-DD string."""
    return date_obj.strftime("%Y-%m-%d")

def add_months(start_date: datetime.date, months: int) -> datetime.date:
    """Add a specified number of months to a date, preserving valid calendar days."""
    month = start_date.month - 1 + months
    year = start_date.year + month // 12
    month = month % 12 + 1
    day = min(start_date.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)

def calculate_batch_expiry(
    manufacture_date_str: Optional[str],
    expiry_date_str: Optional[str],
    expiry_rule_type: Optional[str] = "EXPLICIT_DATE",
    expiry_duration_months: Optional[int] = None,
    product_name: Optional[str] = None,
    expiry_source: Optional[str] = None,
    today_override: Optional[datetime.date] = None
) -> Dict[str, Any]:
    """
    Evaluates batch expiry date, status, days remaining, and text representation.
    
    Precedence:
    1. Explicit expiry date (USE BY / BEST BEFORE / EXPIRY on package label or batch input)
    2. Relative rule (Manufacture date + expiry_duration_months)
    3. Product-specific demo rule (e.g. Chips demo = 4 months from manufacture)
    4. UNKNOWN if date cannot be resolved.
    """
    today = today_override or datetime.date.today()
    resolved_expiry_date: Optional[datetime.date] = None
    resolved_source = expiry_source or "LABEL_EXPLICIT"

    # Step 1: Explicit Date Priority
    explicit_obj = parse_date_string(expiry_date_str)
    if explicit_obj:
        resolved_expiry_date = explicit_obj
        resolved_source = expiry_source or "LABEL_EXPLICIT"
    else:
        # Step 2: Relative Rule (Months from manufacture)
        mfg_obj = parse_date_string(manufacture_date_str)
        if mfg_obj:
            if expiry_rule_type == "MONTHS_FROM_MANUFACTURE" and expiry_duration_months and expiry_duration_months > 0:
                resolved_expiry_date = add_months(mfg_obj, int(expiry_duration_months))
                resolved_source = "PRODUCT_SHELF_LIFE_RULE"
            elif product_name and "Chips" in product_name and (expiry_duration_months == 4 or not expiry_duration_months):
                # Product-specific demo rule for Chips: 4 months
                resolved_expiry_date = add_months(mfg_obj, 4)
                resolved_source = "PRODUCT_SHELF_LIFE_RULE"

    if not resolved_expiry_date:
        return {
            "expiry_date": None,
            "expiry_status": "UNKNOWN",
            "days_remaining": None,
            "days_remaining_text": "Unknown expiry",
            "expiry_source": "UNKNOWN"
        }

    delta_days = (resolved_expiry_date - today).days
    expiry_iso = format_date_iso(resolved_expiry_date)

    # Status Rules
    if delta_days > EXPIRY_WARNING_DAYS:
        status = "NORMAL"
    elif 0 <= delta_days <= EXPIRY_WARNING_DAYS:
        status = "EXPIRING_SOON"
    else:
        status = "EXPIRED"

    # Days Remaining Text (Never negative in display)
    if delta_days > 1:
        days_text = f"{delta_days} days remaining"
    elif delta_days == 1:
        days_text = "1 day remaining"
    elif delta_days == 0:
        days_text = "Expires today"
    elif delta_days == -1:
        days_text = "Expired by 1 day"
    else:
        days_text = f"Expired by {abs(delta_days)} days"

    return {
        "expiry_date": expiry_iso,
        "expiry_status": status,
        "days_remaining": delta_days,
        "days_remaining_text": days_text,
        "expiry_source": resolved_source
    }

def update_all_batch_expiry_statuses(db: Session, today_override: Optional[datetime.date] = None) -> Dict[str, int]:
    """
    Evaluates all active batches in database, updates expiry statuses, and creates
    deduplicated alerts for EXPIRING_SOON and EXPIRED batches.
    """
    batches = db.query(Batch).all()
    summary = {
        "NORMAL": 0,
        "EXPIRING_SOON": 0,
        "EXPIRED": 0,
        "UNKNOWN": 0,
        "TOTAL": len(batches)
    }

    now = datetime.datetime.utcnow()

    for batch in batches:
        prod_name = batch.product.name if batch.product else "Unknown Product"
        mfg = batch.manufacture_date or batch.mfg_date
        exp = batch.expiry_date or batch.exp_date
        
        calc = calculate_batch_expiry(
            manufacture_date_str=mfg,
            expiry_date_str=exp,
            expiry_rule_type=batch.expiry_rule_type,
            expiry_duration_months=batch.expiry_duration_months,
            product_name=prod_name,
            expiry_source=batch.expiry_source,
            today_override=today_override
        )

        status = calc["expiry_status"]
        summary[status] = summary.get(status, 0) + 1

        # Sync batch fields
        batch.expiry_status = status
        batch.last_expiry_check = now
        if calc["expiry_date"]:
            batch.expiry_date = calc["expiry_date"]
            batch.exp_date = calc["expiry_date"]
        if mfg:
            batch.manufacture_date = mfg
            batch.mfg_date = mfg

        # Alert Deduplication & Persistence
        if status == "EXPIRING_SOON":
            existing_alert = db.query(Alert).filter(
                Alert.batch_number == batch.batch_number,
                Alert.status == "WARNING",
                Alert.reason.like("%EXPIRING SOON%")
            ).first()

            if not existing_alert:
                new_alert = Alert(
                    batch_number=batch.batch_number,
                    product_name=prod_name,
                    status="WARNING",
                    reason=f"⚠ PRODUCT EXPIRING SOON - {prod_name} ({batch.batch_number}) expires on {calc['expiry_date']} ({calc['days_remaining_text']})",
                    recommended_action="Review and prioritize this stock according to company procedure.",
                    created_at=now
                )
                db.add(new_alert)

        elif status == "EXPIRED":
            existing_alert = db.query(Alert).filter(
                Alert.batch_number == batch.batch_number,
                Alert.status == "REJECT",
                Alert.reason.like("%EXPIRED%")
            ).first()

            if not existing_alert:
                new_alert = Alert(
                    batch_number=batch.batch_number,
                    product_name=prod_name,
                    status="REJECT",
                    reason=f"🚨 EXPIRED BATCH - {prod_name} ({batch.batch_number}) expired on {calc['expiry_date']} ({calc['days_remaining_text']})",
                    recommended_action="Inspect and quarantine/remove according to company procedure.",
                    created_at=now
                )
                db.add(new_alert)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error committing batch expiry update: {e}")

    return summary
