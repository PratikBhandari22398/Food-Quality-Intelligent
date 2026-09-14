import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Database
DB_PATH = BASE_DIR / "food_quality.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Uploads directory for snapshots
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# AI Models directory
MODELS_DIR = BASE_DIR / "frontend" / "models"
PRODUCT_MODEL_DIR = MODELS_DIR / "product_model"
CONDITION_MODEL_DIR = MODELS_DIR / "condition_model"

# Static / Frontend directory
FRONTEND_DIR = BASE_DIR / "frontend"

# Expiry Monitoring Configuration
EXPIRY_WARNING_DAYS = 30


# Default Reference Standards
DEFAULT_MILK_REFERENCE = {
    "min_fat": 3.5,
    "max_fat": 4.5,
    "min_snf": 8.5,
    "min_ph": 6.4,
    "max_ph": 6.8,
    "min_temp": 4.0,
    "max_temp": 8.0
}

DEFAULT_NUTRITION_PROFILES = {
    "Lay's Classic Salted": {
        "category": "Chips",
        "mrp": "₹20",
        "net_weight": "50 g",
        "serving_size": "20 g",
        "basis": "Per 100 g",
        "source": "Verified Product Label",
        "nutrition_table": {
            "energy": "553 kcal",
            "protein": "6.7 g",
            "carbohydrates": "52.6 g",
            "total_sugars": "0.6 g",
            "added_sugars": "0 g",
            "total_fat": "35.1 g",
            "saturated_fat": "15.8 g",
            "trans_fat": "0.1 g",
            "sodium": "500 mg"
        }
    },
    "Lay's Classic Salted ₹20": {
        "category": "Chips",
        "mrp": "₹20",
        "net_weight": "50 g",
        "serving_size": "20 g",
        "basis": "Per 100 g",
        "source": "Verified Product Label",
        "nutrition_table": {
            "energy": "553 kcal",
            "protein": "6.7 g",
            "carbohydrates": "52.6 g",
            "total_sugars": "0.6 g",
            "added_sugars": "0 g",
            "total_fat": "35.1 g",
            "saturated_fat": "15.8 g",
            "trans_fat": "0.1 g",
            "sodium": "500 mg"
        }
    },
    "Lay's Spanish Tomato Tango": {
        "category": "Chips",
        "mrp": "₹20",
        "net_weight": "50 g",
        "serving_size": "20 g",
        "basis": "Per 100 g",
        "source": "Verified Product Label",
        "nutrition_table": {
            "energy": "525 kcal",
            "protein": "6.4 g",
            "carbohydrates": "53.1 g",
            "total_sugars": "5.6 g",
            "added_sugars": "4.7 g",
            "total_fat": "31.9 g",
            "saturated_fat": "14.3 g",
            "trans_fat": "0.1 g",
            "sodium": "659 mg"
        }
    },
    "Lay's Spanish Tomato Tango ₹20": {
        "category": "Chips",
        "mrp": "₹20",
        "net_weight": "50 g",
        "serving_size": "20 g",
        "basis": "Per 100 g",
        "source": "Verified Product Label",
        "nutrition_table": {
            "energy": "525 kcal",
            "protein": "6.4 g",
            "carbohydrates": "53.1 g",
            "total_sugars": "5.6 g",
            "added_sugars": "4.7 g",
            "total_fat": "31.9 g",
            "saturated_fat": "14.3 g",
            "trans_fat": "0.1 g",
            "sodium": "659 mg"
        }
    },
    "₹10 Milk Pouch": {
        "category": "Milk",
        "mrp": "₹10",
        "net_weight": "170 ml",
        "serving_size": "150 ml",
        "basis": "Per 100 ml",
        "source": "Verified Product Label",
        "nutrition_table": {
            "energy": "58 kcal",
            "protein": "3.1 g",
            "carbohydrates": "4.7 g",
            "total_sugars": "4.7 g",
            "added_sugars": "0 g",
            "total_fat": "3.0 g",
            "saturated_fat": "1.9 g",
            "trans_fat": "0 g",
            "sodium": "50 mg",
            "calcium": "116 mg"
        }
    },
    "₹31 Milk Pouch": {
        "category": "Milk",
        "mrp": "₹31",
        "net_weight": "500 ml",
        "serving_size": "150 ml",
        "basis": "Per 100 ml",
        "source": "Verified Product Label",
        "nutrition_table": {
            "energy": "69 kcal",
            "protein": "3.1 g",
            "carbohydrates": "4.9 g",
            "total_sugars": "4.9 g",
            "added_sugars": "0 g",
            "total_fat": "4.0 g",
            "saturated_fat": "2.1 g",
            "trans_fat": "0 g",
            "sodium": "50 mg",
            "calcium": "116 mg"
        }
    },
    "Pure Dairy Toned Milk": {
        "category": "Milk",
        "mrp": "₹31",
        "net_weight": "500 ml",
        "serving_size": "150 ml",
        "basis": "Per 100 ml",
        "source": "Verified Product Label",
        "nutrition_table": {
            "energy": "69 kcal",
            "protein": "3.1 g",
            "carbohydrates": "4.9 g",
            "total_sugars": "4.9 g",
            "added_sugars": "0 g",
            "total_fat": "4.0 g",
            "saturated_fat": "2.1 g",
            "trans_fat": "0 g",
            "sodium": "50 mg",
            "calcium": "116 mg"
        }
    },
    "Pure Dairy Toned Milk ₹30": {
        "category": "Milk",
        "mrp": "₹31",
        "net_weight": "500 ml",
        "serving_size": "150 ml",
        "basis": "Per 100 ml",
        "source": "Verified Product Label",
        "nutrition_table": {
            "energy": "69 kcal",
            "protein": "3.1 g",
            "carbohydrates": "4.9 g",
            "total_sugars": "4.9 g",
            "added_sugars": "0 g",
            "total_fat": "4.0 g",
            "saturated_fat": "2.1 g",
            "trans_fat": "0 g",
            "sodium": "50 mg",
            "calcium": "116 mg"
        }
    },
    "Chips Packet": {
        "category": "Chips",
        "mrp": "₹20",
        "net_weight": "50 g",
        "serving_size": "20 g",
        "basis": "Per 100 g",
        "source": "Verified Product Label",
        "nutrition_table": {
            "energy": "553 kcal",
            "protein": "6.7 g",
            "carbohydrates": "52.6 g",
            "total_sugars": "0.6 g",
            "added_sugars": "0 g",
            "total_fat": "35.1 g",
            "saturated_fat": "15.8 g",
            "trans_fat": "0.1 g",
            "sodium": "500 mg"
        }
    },
    "Milk Pouch": {
        "category": "Milk",
        "mrp": "₹31",
        "net_weight": "500 ml",
        "serving_size": "150 ml",
        "basis": "Per 100 ml",
        "source": "Verified Product Label",
        "nutrition_table": {
            "energy": "69 kcal",
            "protein": "3.1 g",
            "carbohydrates": "4.9 g",
            "total_sugars": "4.9 g",
            "added_sugars": "0 g",
            "total_fat": "4.0 g",
            "saturated_fat": "2.1 g",
            "trans_fat": "0 g",
            "sodium": "50 mg",
            "calcium": "116 mg"
        }
    }
}

