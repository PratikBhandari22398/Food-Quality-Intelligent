from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from backend.db import models
    from backend.config import DEFAULT_NUTRITION_PROFILES
    import json

    try:
        Base.metadata.create_all(bind=engine)
        
        # SQLite Column Migrations for Inspections, Products, and Batches Tables
        with engine.connect() as conn:
            columns = [c[1] for c in conn.execute(text("PRAGMA table_info(inspections)")).fetchall()]
            if "human_review_status" not in columns:
                conn.execute(text("ALTER TABLE inspections ADD COLUMN human_review_status VARCHAR"))
            if "human_reviewer" not in columns:
                conn.execute(text("ALTER TABLE inspections ADD COLUMN human_reviewer VARCHAR"))
            if "human_comment" not in columns:
                conn.execute(text("ALTER TABLE inspections ADD COLUMN human_comment TEXT"))
            if "human_reviewed_at" not in columns:
                conn.execute(text("ALTER TABLE inspections ADD COLUMN human_reviewed_at DATETIME"))
            if "product_variant" not in columns:
                conn.execute(text("ALTER TABLE inspections ADD COLUMN product_variant VARCHAR"))
            if "mrp" not in columns:
                conn.execute(text("ALTER TABLE inspections ADD COLUMN mrp VARCHAR"))
            if "net_weight" not in columns:
                conn.execute(text("ALTER TABLE inspections ADD COLUMN net_weight VARCHAR"))
            if "serving_size" not in columns:
                conn.execute(text("ALTER TABLE inspections ADD COLUMN serving_size VARCHAR"))
            if "nutrition_source" not in columns:
                conn.execute(text("ALTER TABLE inspections ADD COLUMN nutrition_source VARCHAR"))
            if "ocr_status" not in columns:
                conn.execute(text("ALTER TABLE inspections ADD COLUMN ocr_status VARCHAR"))
            if "data_source" not in columns:
                conn.execute(text("ALTER TABLE inspections ADD COLUMN data_source VARCHAR"))

            prod_cols = [c[1] for c in conn.execute(text("PRAGMA table_info(products)")).fetchall()]
            if "mrp" not in prod_cols:
                conn.execute(text("ALTER TABLE products ADD COLUMN mrp VARCHAR"))

            batch_cols = [c[1] for c in conn.execute(text("PRAGMA table_info(batches)")).fetchall()]
            if "manufacture_date" not in batch_cols:
                conn.execute(text("ALTER TABLE batches ADD COLUMN manufacture_date VARCHAR"))
            if "expiry_date" not in batch_cols:
                conn.execute(text("ALTER TABLE batches ADD COLUMN expiry_date VARCHAR"))
            if "expiry_rule_type" not in batch_cols:
                conn.execute(text("ALTER TABLE batches ADD COLUMN expiry_rule_type VARCHAR"))
            if "expiry_duration_months" not in batch_cols:
                conn.execute(text("ALTER TABLE batches ADD COLUMN expiry_duration_months INTEGER"))
            if "expiry_source" not in batch_cols:
                conn.execute(text("ALTER TABLE batches ADD COLUMN expiry_source VARCHAR"))
            if "expiry_status" not in batch_cols:
                conn.execute(text("ALTER TABLE batches ADD COLUMN expiry_status VARCHAR"))
            if "last_expiry_check" not in batch_cols:
                conn.execute(text("ALTER TABLE batches ADD COLUMN last_expiry_check DATETIME"))
            conn.commit()

        # Seed / Update initial product records
        db = SessionLocal()
        try:
            for p_name, p_data in DEFAULT_NUTRITION_PROFILES.items():
                existing = db.query(models.Product).filter(models.Product.name == p_name).first()
                if existing:
                    existing.mrp = p_data.get("mrp", existing.mrp)
                    existing.net_weight = p_data.get("net_weight", existing.net_weight)
                    existing.serving_size = p_data.get("serving_size", existing.serving_size)
                    existing.standard_nutrition = json.dumps(p_data.get("nutrition_table", {}))
                else:
                    new_prod = models.Product(
                        name=p_name,
                        brand="Lay's" if "Lay's" in p_name else ("Pure Dairy" if "Dairy" in p_name else "Generic"),
                        category=p_data.get("category", "Chips" if "Chips" in p_name else "Milk"),
                        mrp=p_data.get("mrp", "₹20"),
                        net_weight=p_data.get("net_weight", "50 g"),
                        serving_size=p_data.get("serving_size", "20 g"),
                        standard_nutrition=json.dumps(p_data.get("nutrition_table", {}))
                    )
                    db.add(new_prod)
            db.commit()            # Seed demo batches for Expiry Monitoring if none exist
            if db.query(models.Batch).filter(models.Batch.batch_number.like("%DEMO%")).count() == 0:
                import datetime as dt
                today = dt.date.today()
                chips_prod = db.query(models.Product).filter(models.Product.category == "Chips").first()
                milk_prod = db.query(models.Product).filter(models.Product.category == "Milk").first()
                p_id_chips = chips_prod.id if chips_prod else 1
                p_id_milk = milk_prod.id if milk_prod else 1

                demo_batches = [
                    models.Batch(
                        batch_number="BAT-DEMO-CHIPS-01",
                        product_id=p_id_chips,
                        mfg_date=(today - dt.timedelta(days=10)).strftime("%Y-%m-%d"),
                        exp_date=(today + dt.timedelta(days=110)).strftime("%Y-%m-%d"),
                        manufacture_date=(today - dt.timedelta(days=10)).strftime("%Y-%m-%d"),
                        expiry_date=(today + dt.timedelta(days=110)).strftime("%Y-%m-%d"),
                        expiry_rule_type="MONTHS_FROM_MANUFACTURE",
                        expiry_duration_months=4,
                        expiry_source="DEMO",
                        expiry_status="NORMAL",
                        status="ACTIVE"
                    ),
                    models.Batch(
                        batch_number="BAT-DEMO-CHIPS-02",
                        product_id=p_id_chips,
                        mfg_date=(today - dt.timedelta(days=105)).strftime("%Y-%m-%d"),
                        exp_date=(today + dt.timedelta(days=15)).strftime("%Y-%m-%d"),
                        manufacture_date=(today - dt.timedelta(days=105)).strftime("%Y-%m-%d"),
                        expiry_date=(today + dt.timedelta(days=15)).strftime("%Y-%m-%d"),
                        expiry_rule_type="MONTHS_FROM_MANUFACTURE",
                        expiry_duration_months=4,
                        expiry_source="DEMO",
                        expiry_status="EXPIRING_SOON",
                        status="INACTIVE"
                    ),
                    models.Batch(
                        batch_number="BAT-DEMO-MILK-01",
                        product_id=p_id_milk,
                        mfg_date=(today - dt.timedelta(days=5)).strftime("%Y-%m-%d"),
                        exp_date=(today + dt.timedelta(days=60)).strftime("%Y-%m-%d"),
                        manufacture_date=(today - dt.timedelta(days=5)).strftime("%Y-%m-%d"),
                        expiry_date=(today + dt.timedelta(days=60)).strftime("%Y-%m-%d"),
                        expiry_rule_type="EXPLICIT_DATE",
                        expiry_source="DEMO",
                        expiry_status="NORMAL",
                        status="INACTIVE"
                    ),
                    models.Batch(
                        batch_number="BAT-DEMO-MILK-02",
                        product_id=p_id_milk,
                        mfg_date=(today - dt.timedelta(days=130)).strftime("%Y-%m-%d"),
                        exp_date=(today - dt.timedelta(days=5)).strftime("%Y-%m-%d"),
                        manufacture_date=(today - dt.timedelta(days=130)).strftime("%Y-%m-%d"),
                        expiry_date=(today - dt.timedelta(days=5)).strftime("%Y-%m-%d"),
                        expiry_rule_type="EXPLICIT_DATE",
                        expiry_source="DEMO",
                        expiry_status="EXPIRED",
                        status="INACTIVE"
                    ),
                    models.Batch(
                        batch_number="DEMO-EXP-001",
                        product_id=p_id_chips,
                        mfg_date=(today - dt.timedelta(days=10)).strftime("%Y-%m-%d"),
                        exp_date=(today + dt.timedelta(days=90)).strftime("%Y-%m-%d"),
                        manufacture_date=(today - dt.timedelta(days=10)).strftime("%Y-%m-%d"),
                        expiry_date=(today + dt.timedelta(days=90)).strftime("%Y-%m-%d"),
                        expiry_rule_type="MONTHS_FROM_MANUFACTURE",
                        expiry_duration_months=4,
                        expiry_source="DEMO",
                        expiry_status="NORMAL",
                        status="INACTIVE"
                    ),
                    models.Batch(
                        batch_number="DEMO-EXP-002",
                        product_id=p_id_milk,
                        mfg_date=(today - dt.timedelta(days=5)).strftime("%Y-%m-%d"),
                        exp_date=(today + dt.timedelta(days=15)).strftime("%Y-%m-%d"),
                        manufacture_date=(today - dt.timedelta(days=5)).strftime("%Y-%m-%d"),
                        expiry_date=(today + dt.timedelta(days=15)).strftime("%Y-%m-%d"),
                        expiry_rule_type="EXPLICIT_DATE",
                        expiry_source="DEMO",
                        expiry_status="EXPIRING_SOON",
                        status="INACTIVE"
                    ),
                    models.Batch(
                        batch_number="DEMO-EXP-003",
                        product_id=p_id_chips,
                        mfg_date=(today - dt.timedelta(days=130)).strftime("%Y-%m-%d"),
                        exp_date=(today - dt.timedelta(days=10)).strftime("%Y-%m-%d"),
                        manufacture_date=(today - dt.timedelta(days=130)).strftime("%Y-%m-%d"),
                        expiry_date=(today - dt.timedelta(days=10)).strftime("%Y-%m-%d"),
                        expiry_rule_type="EXPLICIT_DATE",
                        expiry_source="DEMO",
                        expiry_status="EXPIRED",
                        status="INACTIVE"
                    ),
                    models.Batch(
                        batch_number="DEMO-EXP-004",
                        product_id=p_id_milk,
                        mfg_date=None,
                        exp_date=None,
                        manufacture_date=None,
                        expiry_date=None,
                        expiry_rule_type="EXPLICIT_DATE",
                        expiry_source="DEMO",
                        expiry_status="UNKNOWN",
                        status="INACTIVE"
                    )
                ]
                db.add_all(demo_batches)
                db.commit()

            # Enforce strictly SINGLE active batch in database
            active_batches = db.query(models.Batch).filter(models.Batch.status == "ACTIVE").order_by(models.Batch.id.desc()).all()
            if len(active_batches) > 1:
                for b in active_batches[1:]:
                    b.status = "INACTIVE"
                db.commit()

            # Seed demo inspection records ONLY when inspections table is completely empty
            if db.query(models.Inspection).count() == 0:
                demo_seeds = [
                    models.Inspection(expected_product="Chips Packet", detected_product="Chips Packet", product_confidence=0.964, packaging_condition="Normal Package", condition_confidence=0.931, final_status="PASS", status_reasons=json.dumps(["Product and package verified."]), data_source="DEMO"),
                    models.Inspection(expected_product="Chips Packet", detected_product="Chips Packet", product_confidence=0.925, packaging_condition="Damage Package", condition_confidence=0.910, final_status="REJECT", status_reasons=json.dumps(["Visible packaging damage detected."]), data_source="DEMO"),
                    models.Inspection(expected_product="Milk Pouch", detected_product="Milk Pouch", product_confidence=0.962, packaging_condition="Normal Package", condition_confidence=0.941, final_status="PASS", status_reasons=json.dumps(["Milk product and package verified."]), data_source="DEMO"),
                    models.Inspection(expected_product="Milk Pouch", detected_product="Milk Pouch", product_confidence=0.620, packaging_condition="Unclear", condition_confidence=0.610, final_status="WARNING", status_reasons=json.dumps(["Low AI Product Confidence."]), data_source="DEMO"),
                    models.Inspection(expected_product="Chips Packet", detected_product="Milk Pouch", product_confidence=0.915, packaging_condition="Normal Package", condition_confidence=0.950, final_status="HOLD", status_reasons=json.dumps(["Expected product category does not match detected product category."]), data_source="DEMO"),
                    models.Inspection(expected_product="Chips Packet", detected_product="Chips Packet", product_confidence=0.971, packaging_condition="Normal Package", condition_confidence=0.952, final_status="PASS", status_reasons=json.dumps(["Product and package verified."]), data_source="DEMO"),
                    models.Inspection(expected_product="Milk Pouch", detected_product="Milk Pouch", product_confidence=0.958, packaging_condition="Normal Package", condition_confidence=0.939, final_status="PASS", status_reasons=json.dumps(["Milk product and package verified."]), data_source="DEMO")
                ]
                db.add_all(demo_seeds)
                db.commit()

            # Synchronize expiry statuses on startup
            from backend.services.expiry_service import update_all_batch_expiry_statuses
            update_all_batch_expiry_statuses(db)



        except Exception as se:
            db.rollback()
            print(f"Product seed notice: {se}")
        finally:
            db.close()

    except Exception as e:
        print(f"Database init notice: {e}")

# Run init_db on load to guarantee migrations & seeding
try:
    init_db()
except Exception:
    pass


