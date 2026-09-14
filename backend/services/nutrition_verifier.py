from typing import Dict, Any, Optional

class NutritionVerifier:
    @staticmethod
    def verify_ocr_vs_database(db_nutrition: Dict[str, Any], ocr_nutrition: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compares Database Stored Verified Nutrition Facts against OCR Extracted Facts.
        Outputs match or mismatch status without silently overwriting database values.
        """
        field_comparisons = {}
        has_mismatch = False

        for field, db_val in db_nutrition.items():
            ocr_val = ocr_nutrition.get(field)
            
            # Format numbers for clean comparison
            try:
                db_num = float(str(db_val).replace("g", "").replace("kcal", "").replace("mg", "").strip())
            except (ValueError, TypeError):
                db_num = None

            try:
                ocr_num = float(str(ocr_val).replace("g", "").replace("kcal", "").replace("mg", "").strip())
            except (ValueError, TypeError):
                ocr_num = None

            if db_num is not None and ocr_num is not None:
                # 5% tolerance allowance for rounding
                diff = abs(db_num - ocr_num)
                if diff <= (0.05 * max(db_num, 1.0)):
                    field_comparisons[field] = {"db": db_val, "ocr": ocr_val, "status": "✅ MATCH"}
                else:
                    field_comparisons[field] = {"db": db_val, "ocr": ocr_val, "status": "⚠️ VALUE MISMATCH"}
                    has_mismatch = True
            else:
                field_comparisons[field] = {"db": db_val, "ocr": ocr_val or "Not detected", "status": "❌ UNABLE TO VERIFY"}

        overall_status = "⚠️ VALUE MISMATCH - Manual verification required." if has_mismatch else "✅ MATCH"

        return {
            "overall_status": overall_status,
            "has_mismatch": has_mismatch,
            "field_comparisons": field_comparisons,
            "notice": "Do not silently overwrite verified database values using OCR."
        }

    @staticmethod
    def verify_product_consistency(expected_product: str, ai_detected_product: str, ocr_product_name: Optional[str]) -> Dict[str, Any]:
        """
        Compares AI detected product vs OCR product name vs Expected batch product.
        """
        exp_lower = expected_product.strip().lower()
        ai_lower = ai_detected_product.strip().lower()
        ocr_lower = ocr_product_name.strip().lower() if ocr_product_name and ocr_product_name != "Not Clearly Read" else None

        is_consistent = (exp_lower in ai_lower or ai_lower in exp_lower)
        if ocr_lower:
            is_consistent = is_consistent and (exp_lower in ocr_lower or ocr_lower in exp_lower or ai_lower in ocr_lower)

        status_text = "✅ Product Information Consistent" if is_consistent else "⚠️ Product Information Mismatch"

        return {
            "status_text": status_text,
            "is_consistent": is_consistent,
            "expected_product": expected_product,
            "ai_detected_product": ai_detected_product,
            "ocr_product_name": ocr_product_name or "Not Clearly Read"
        }

    @staticmethod
    def evaluate_nutrition_reference(nutrition_data: Dict[str, Any], category: str = "Chips") -> Dict[str, Any]:
        """
        Screens nutrition values against configured reference rules for screening.
        Includes mandatory disclaimer.
        """
        evaluations = {}
        has_deviation = False

        # Configurable reference limits by category
        REF_BOUNDS = {
          "Chips": {
            "energy_kcal": (400, 600),
            "saturated_fat_g": (0, 20.0),
            "sodium_mg": (0, 1000.0)
          },
          "Milk": {
            "energy_kcal": (30, 90),
            "protein_g": (2.5, 5.0),
            "saturated_fat_g": (0, 3.5),
            "sodium_mg": (0, 150.0)
          }
        }

        bounds = REF_BOUNDS.get(category, REF_BOUNDS["Chips"])

        for field, (min_val, max_val) in bounds.items():
            val = nutrition_data.get(field)
            if isinstance(val, (int, float)):
                if min_val <= val <= max_val:
                    evaluations[field] = {"value": val, "range": f"{min_val} - {max_val}", "status": "✅ WITHIN REFERENCE"}
                else:
                    evaluations[field] = {"value": val, "range": f"{min_val} - {max_val}", "status": "⚠️ DEVIATION DETECTED"}
                    has_deviation = True
            else:
                evaluations[field] = {"value": val, "range": f"{min_val} - {max_val}", "status": "❌ UNABLE TO VERIFY"}

        overall_status = "⚠️ DEVIATION DETECTED" if has_deviation else "✅ WITHIN REFERENCE"

        return {
            "overall_status": overall_status,
            "evaluations": evaluations,
            "disclaimer": "Nutrition values are checked against configured reference values and product records. This does not independently certify food safety."
        }
