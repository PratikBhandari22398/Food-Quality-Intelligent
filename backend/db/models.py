import datetime
import json
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.db.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    brand = Column(String, nullable=True, default="Generic Brand")
    category = Column(String, nullable=False)            # e.g., "Chips", "Milk", "General"
    mrp = Column(String, nullable=True, default="₹20")
    barcode = Column(String, nullable=True)
    net_weight = Column(String, nullable=True)
    serving_size = Column(String, nullable=True)
    ingredients = Column(Text, nullable=True)
    allergens = Column(String, nullable=True)
    standard_nutrition = Column(Text, nullable=True)     # JSON string of standard nutrition
    milk_reference = Column(Text, nullable=True)         # JSON string of milk params bounds
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    batches = relationship("Batch", back_populates="product")
    nutrition_records = relationship("NutritionRecord", back_populates="product")

    def get_nutrition_json(self):
        return json.loads(self.standard_nutrition) if self.standard_nutrition else {}

    def get_milk_reference_json(self):
        return json.loads(self.milk_reference) if self.milk_reference else {}


class NutritionRecord(Base):
    __tablename__ = "nutrition_records"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    basis = Column(String, nullable=False, default="per_100g") # per_100g, per_100ml, serving, single_pack
    serving_size = Column(String, nullable=True)
    energy_kcal = Column(Float, nullable=True)
    protein_g = Column(Float, nullable=True)
    carbohydrate_g = Column(Float, nullable=True)
    total_sugars_g = Column(Float, nullable=True)
    added_sugars_g = Column(Float, nullable=True)
    total_fat_g = Column(Float, nullable=True)
    saturated_fat_g = Column(Float, nullable=True)
    trans_fat_g = Column(Float, nullable=True)
    sodium_mg = Column(Float, nullable=True)
    fibre_g = Column(Float, nullable=True)
    calcium_mg = Column(Float, nullable=True)
    source = Column(String, nullable=False, default="Verified Product Label") # "Verified Product Label" or "OCR From Package"
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    product = relationship("Product", back_populates="nutrition_records")


class MilkReferenceRange(Base):
    __tablename__ = "milk_reference_ranges"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False) # e.g., "Toned Milk", "Double Toned Milk", "Skimmed Milk", "Full Cream Milk"
    parameter = Column(String, nullable=False) # fat, snf, ph, temperature, protein, calcium
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    unit = Column(String, nullable=False)
    source = Column(String, default="Configured Reference Standards")
    notes = Column(Text, nullable=True)
    effective_date = Column(String, nullable=True, default="2026-01-01")


class Batch(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    batch_number = Column(String, nullable=False, unique=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    mfg_date = Column(String, nullable=True)
    exp_date = Column(String, nullable=True)
    status = Column(String, default="ACTIVE")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Expiry Monitoring Fields (Requirement Step 19)
    manufacture_date = Column(String, nullable=True)
    expiry_date = Column(String, nullable=True)
    expiry_rule_type = Column(String, default="EXPLICIT_DATE") # EXPLICIT_DATE or MONTHS_FROM_MANUFACTURE
    expiry_duration_months = Column(Integer, nullable=True)
    expiry_source = Column(String, default="LABEL_EXPLICIT") # LABEL_EXPLICIT, PRODUCT_SHELF_LIFE_RULE, USER_MANUAL, DEMO
    expiry_status = Column(String, default="UNKNOWN") # NORMAL, EXPIRING_SOON, EXPIRED, UNKNOWN
    last_expiry_check = Column(DateTime, nullable=True)

    product = relationship("Product", back_populates="batches")
    inspections = relationship("Inspection", back_populates="batch")



class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), nullable=True)
    batch_number = Column(String, nullable=True)
    product_name = Column(String, nullable=False)
    status = Column(String, nullable=False) # WARNING, HOLD, REJECT
    reason = Column(Text, nullable=False)
    recommended_action = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)
    image_path = Column(String, nullable=True)
    expected_product = Column(String, nullable=False)
    detected_product = Column(String, nullable=False)
    product_variant = Column(String, nullable=True)
    mrp = Column(String, nullable=True)
    net_weight = Column(String, nullable=True)
    serving_size = Column(String, nullable=True)
    nutrition_source = Column(String, nullable=True, default="Verified Product Label")
    ocr_status = Column(String, nullable=True)
    product_confidence = Column(Float, default=0.0)
    packaging_condition = Column(String, nullable=False)
    condition_confidence = Column(Float, default=0.0)
    ocr_extracted_json = Column(Text, nullable=True)    # JSON string of extracted label details
    milk_lab_params_json = Column(Text, nullable=True)   # JSON string of lab params
    final_status = Column(String, nullable=False)        # PASS, WARNING, HOLD, REJECT
    status_reasons = Column(Text, nullable=False)        # JSON string of reason strings array
    
    # Human Review Fields (Requirement 9)
    human_review_status = Column(String, nullable=True) # APPROVED, REJECTED, REINSPECT_REQUESTED
    human_reviewer = Column(String, nullable=True)
    human_comment = Column(Text, nullable=True)
    human_reviewed_at = Column(DateTime, nullable=True)
    data_source = Column(String, default="LIVE INSPECTION")

    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    batch = relationship("Batch", back_populates="inspections")

    def get_ocr_json(self):
        return json.loads(self.ocr_extracted_json) if self.ocr_extracted_json else {}

    def get_milk_params_json(self):
        return json.loads(self.milk_lab_params_json) if self.milk_lab_params_json else {}

    def get_reasons_list(self):
        return json.loads(self.status_reasons) if self.status_reasons else []

