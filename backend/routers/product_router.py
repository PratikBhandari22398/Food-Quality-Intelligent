import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.db.database import get_db
from backend.db.models import Product, NutritionRecord, MilkReferenceRange
from backend.schemas.product_schema import ProductCreate, ProductResponse
from backend.config import DEFAULT_NUTRITION_PROFILES, DEFAULT_MILK_REFERENCE

router = APIRouter(prefix="/api/products", tags=["Products"])

@router.get("", response_model=List[ProductResponse])
def get_products(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    if not products:
        # Seed default products if empty
        p1 = Product(
            name="Chips Packet",
            brand="Crispy Crunch",
            category="Chips",
            net_weight="50 g",
            serving_size="20 g",
            ingredients="Potatoes, Vegetable Oil, Salt",
            allergens="None",
            standard_nutrition=json.dumps(DEFAULT_NUTRITION_PROFILES["Chips Packet"])
        )
        p2 = Product(
            name="Milk Pouch",
            brand="Pure Dairy",
            category="Milk",
            net_weight="500 ml",
            serving_size="100 ml",
            ingredients="Pasteurized Toned Milk",
            allergens="Milk",
            standard_nutrition=json.dumps(DEFAULT_NUTRITION_PROFILES["Milk Pouch"]),
            milk_reference=json.dumps(DEFAULT_MILK_REFERENCE)
        )
        db.add_all([p1, p2])
        db.commit()

        # Seed NutritionRecords
        n1 = NutritionRecord(
            product_id=p1.id,
            basis="per_100g",
            serving_size="20 g",
            energy_kcal=536.0,
            protein_g=7.0,
            carbohydrate_g=53.0,
            total_sugars_g=1.5,
            added_sugars_g=0.0,
            total_fat_g=33.0,
            saturated_fat_g=14.0,
            trans_fat_g=0.1,
            sodium_mg=520.0,
            source="Verified Product Label"
        )
        n2 = NutritionRecord(
            product_id=p2.id,
            basis="per_100ml",
            serving_size="100 ml",
            energy_kcal=62.0,
            protein_g=3.2,
            carbohydrate_g=4.7,
            total_sugars_g=4.7,
            added_sugars_g=0.0,
            total_fat_g=3.5,
            saturated_fat_g=2.2,
            trans_fat_g=0.0,
            sodium_mg=50.0,
            source="Verified Product Label"
        )
        db.add_all([n1, n2])

        # Seed MilkReferenceRanges
        m_refs = [
            MilkReferenceRange(category="Toned Milk", parameter="fat", min_value=3.0, max_value=3.5, unit="%", notes="Standard Toned Milk Fat Range"),
            MilkReferenceRange(category="Toned Milk", parameter="snf", min_value=8.5, max_value=10.0, unit="%", notes="Minimum SNF requirement"),
            MilkReferenceRange(category="Toned Milk", parameter="ph", min_value=6.4, max_value=6.8, unit="pH", notes="Normal fresh milk pH bounds"),
            MilkReferenceRange(category="Toned Milk", parameter="temperature", min_value=4.0, max_value=8.0, unit="°C", notes="Target cold chain storage temp"),
            MilkReferenceRange(category="Full Cream Milk", parameter="fat", min_value=6.0, max_value=7.0, unit="%", notes="Full Cream Fat Range")
        ]
        db.add_all(m_refs)
        db.commit()

        products = db.query(Product).all()
    
    result = []
    for p in products:
        result.append(ProductResponse(
            id=p.id,
            name=p.name,
            category=p.category,
            barcode=p.barcode,
            standard_nutrition=p.get_nutrition_json(),
            milk_reference=p.get_milk_reference_json()
        ))
    return result

@router.get("/milk-references")
def get_milk_references(db: Session = Depends(get_db)):
    refs = db.query(MilkReferenceRange).all()
    return [
        {
            "id": r.id,
            "category": r.category,
            "parameter": r.parameter,
            "min_value": r.min_value,
            "max_value": r.max_value,
            "unit": r.unit,
            "source": r.source,
            "notes": r.notes,
            "effective_date": r.effective_date
        }
        for r in refs
    ]

@router.get("/{product_id}/nutrition")
def get_product_nutrition(product_id: str, db: Session = Depends(get_db)):
    prod = None
    if product_id.isdigit():
        prod = db.query(Product).filter(Product.id == int(product_id)).first()
    if not prod:
        prod = db.query(Product).filter(
            (Product.name.ilike(f"%{product_id}%")) | 
            (Product.category.ilike(f"%{product_id}%"))
        ).first()
    
    if not prod:
        p_id_lower = product_id.lower()
        if "chip" in p_id_lower:
            prod = db.query(Product).filter(Product.category == "Chips").first()
        elif "milk" in p_id_lower:
            prod = db.query(Product).filter(Product.category == "Milk").first()

    if not prod:
        # Trigger default product seeding if empty
        get_products(db)
        if "chip" in product_id.lower():
            prod = db.query(Product).filter(Product.category == "Chips").first()
        elif "milk" in product_id.lower():
            prod = db.query(Product).filter(Product.category == "Milk").first()
        else:
            prod = db.query(Product).first()

    if not prod:
        raise HTTPException(status_code=404, detail="Product nutrition record not found.")

    standard = prod.get_nutrition_json()
    if not standard:
        p_name = prod.name if prod.name in DEFAULT_NUTRITION_PROFILES else ("Milk Pouch" if prod.category == "Milk" else "Chips Packet")
        standard = DEFAULT_NUTRITION_PROFILES.get(p_name, {})

    return {
        "product_id": prod.id,
        "product_name": prod.name,
        "category": prod.category,
        "nutrition": standard
    }

