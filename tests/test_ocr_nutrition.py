import unittest
from backend.services.ocr_service import OCRService
from backend.services.nutrition_verifier import NutritionVerifier

class TestOCRAndNutritionIntegration(unittest.TestCase):

    def test_1_clear_chips_nutrition_label(self):
        sample_text = """
        CRISPY CHIPS CLASSIC SALTED
        BATCH NO: BAT-2026-CHIPS-99
        BEST BEFORE: 2027-12-31
        NET WT: 50 g
        SERVING SIZE: 20 g
        NUTRITION INFORMATION PER 100g
        ENERGY: 553 kcal
        PROTEIN: 6.7 g
        CARBOHYDRATE: 52.6 g
        TOTAL SUGARS: 0.6 g
        ADDED SUGARS: 0 g
        TOTAL FAT: 35.1 g
        SATURATED FAT: 15.8 g
        TRANS FAT: 0.1 g
        SODIUM: 500 mg
        """
        parsed = OCRService.parse_extracted_text(sample_text)
        self.assertEqual(parsed["batch_number"], "BAT-2026-CHIPS-99")
        self.assertEqual(parsed["exp_date"], "2027-12-31")
        self.assertEqual(parsed["expiry_status"], "VALID")
        self.assertEqual(parsed["net_weight"], "50 g")
        self.assertEqual(parsed["basis"], "per_100g")
        self.assertEqual(parsed["nutrition_data"]["energy_kcal"], 553.0)
        self.assertEqual(parsed["nutrition_data"]["protein_g"], 6.7)

    def test_2_clear_milk_nutrition_label(self):
        sample_text = """
        PURE TONED MILK
        LOT: BNO-MILK-44
        EXP DATE: 2028-05-15
        NET QTY: 500 ml
        NUTRITIONAL FACTS PER 100ML
        ENERGY: 62 kcal
        PROTEIN: 3.2 g
        CARBOHYDRATE: 4.7 g
        TOTAL SUGARS: 4.7 g
        ADDED SUGARS: 0 g
        TOTAL FAT: 3.5 g
        SATURATED FAT: 2.2 g
        TRANS FAT: 0 g
        SODIUM: 50 mg
        CALCIUM: 120 mg
        """
        parsed = OCRService.parse_extracted_text(sample_text)
        self.assertEqual(parsed["batch_number"], "BNO-MILK-44")
        self.assertEqual(parsed["exp_date"], "2028-05-15")
        self.assertEqual(parsed["basis"], "per_100ml")
        self.assertEqual(parsed["nutrition_data"]["calcium_mg"], 120.0)

    def test_3_batch_number_extraction(self):
        sample_text = "LOT NO: BATCH-8877-XYZ"
        parsed = OCRService.parse_extracted_text(sample_text)
        self.assertEqual(parsed["batch_number"], "BATCH-8877-XYZ")

    def test_4_best_before_date_extraction(self):
        sample_text = "BEST BEFORE: 2029-10-20"
        parsed = OCRService.parse_extracted_text(sample_text)
        self.assertEqual(parsed["exp_date"], "2029-10-20")
        self.assertEqual(parsed["expiry_status"], "VALID")

    def test_5_net_weight_extraction(self):
        sample_text = "NET WEIGHT: 250 g"
        parsed = OCRService.parse_extracted_text(sample_text)
        self.assertEqual(parsed["net_weight"], "250 g")

    def test_6_nutrition_table_extraction(self):
        sample_text = "ENERGY: 450 kcal PROTEIN: 12 g TOTAL FAT: 20 g SODIUM: 300 mg"
        parsed = OCRService.parse_extracted_text(sample_text)
        self.assertEqual(parsed["nutrition_data"]["energy_kcal"], 450.0)
        self.assertEqual(parsed["nutrition_data"]["protein_g"], 12.0)
        self.assertEqual(parsed["nutrition_data"]["total_fat_g"], 20.0)
        self.assertEqual(parsed["nutrition_data"]["sodium_mg"], 300.0)

    def test_7_missing_nutrition_field(self):
        sample_text = "ENERGY: 500 kcal PROTEIN: 5 g"
        parsed = OCRService.parse_extracted_text(sample_text)
        # Requirement 3: Missing nutrient fields must be "Not detected", NOT invented!
        self.assertEqual(parsed["nutrition_data"]["fibre_g"], "Not detected")
        self.assertEqual(parsed["nutrition_data"]["calcium_mg"], "Not detected")
        self.assertEqual(parsed["nutrition_data"]["trans_fat_g"], "Not detected")

    def test_8_blurry_image_or_empty_text(self):
        sample_text = "   "
        parsed = OCRService.parse_extracted_text(sample_text)
        self.assertFalse(parsed["is_label_found"])
        self.assertEqual(parsed["batch_number"], "Not Clearly Read")
        self.assertEqual(parsed["expiry_status_display"], "⚠️ Date Could Not Be Verified")

    def test_9_incorrect_ocr_value_mismatch(self):
        db_nutrition = {"energy_kcal": 553, "protein_g": 6.7}
        ocr_nutrition = {"energy_kcal": 420, "protein_g": 6.7}
        verification = NutritionVerifier.verify_ocr_vs_database(db_nutrition, ocr_nutrition)
        self.assertTrue(verification["has_mismatch"])
        self.assertIn("VALUE MISMATCH", verification["overall_status"])

    def test_10_product_ocr_mismatch(self):
        consistency = NutritionVerifier.verify_product_consistency(
            expected_product="Chips Packet",
            ai_detected_product="Chips Packet",
            ocr_product_name="Fruit Juice Bottle"
        )
        self.assertFalse(consistency["is_consistent"])
        self.assertIn("Mismatch", consistency["status_text"])

    # --- STEP 9 SPECIFIC SCENARIO TESTS (CHIPS & MILK) ---

    def test_C_N1_chips_correct_nutrition(self):
        db_nutrition = {"energy_kcal": 536.0, "protein_g": 7.0, "total_fat_g": 33.0, "sodium_mg": 520.0}
        ocr_nutrition = {"energy_kcal": 536.0, "protein_g": 7.0, "total_fat_g": 33.0, "sodium_mg": 520.0}
        verification = NutritionVerifier.verify_ocr_vs_database(db_nutrition, ocr_nutrition)
        self.assertFalse(verification["has_mismatch"])
        self.assertIn("MATCH", verification["overall_status"])

    def test_C_N2_chips_changed_nutrition_value(self):
        db_nutrition = {"energy_kcal": 536.0, "protein_g": 7.0, "total_fat_g": 33.0}
        ocr_nutrition = {"energy_kcal": 536.0, "protein_g": 7.0, "total_fat_g": 48.0} # altered fat
        verification = NutritionVerifier.verify_ocr_vs_database(db_nutrition, ocr_nutrition)
        self.assertTrue(verification["has_mismatch"])
        self.assertIn("VALUE MISMATCH", verification["overall_status"])

    def test_C_N3_chips_partially_unreadable(self):
        db_nutrition = {"energy_kcal": 536.0, "protein_g": 7.0, "sodium_mg": 520.0}
        ocr_nutrition = {"energy_kcal": 536.0, "protein_g": "Not detected", "sodium_mg": 520.0}
        verification = NutritionVerifier.verify_ocr_vs_database(db_nutrition, ocr_nutrition)
        self.assertEqual(verification["field_comparisons"]["protein_g"]["status"], "❌ UNABLE TO VERIFY")

    def test_C_N4_chips_wrong_product_data(self):
        consistency = NutritionVerifier.verify_product_consistency(
            expected_product="Chips Packet",
            ai_detected_product="Chips Packet",
            ocr_product_name="Orange Juice Pouch"
        )
        self.assertFalse(consistency["is_consistent"])

    def test_M_N1_milk_correct_nutrition(self):
        db_nutrition = {"energy_kcal": 62.0, "protein_g": 3.2, "total_fat_g": 3.5, "calcium_mg": 120.0}
        ocr_nutrition = {"energy_kcal": 62.0, "protein_g": 3.2, "total_fat_g": 3.5, "calcium_mg": 120.0}
        verification = NutritionVerifier.verify_ocr_vs_database(db_nutrition, ocr_nutrition)
        self.assertFalse(verification["has_mismatch"])
        self.assertIn("MATCH", verification["overall_status"])

    def test_M_N2_milk_changed_nutrition_value(self):
        db_nutrition = {"energy_kcal": 62.0, "protein_g": 3.2, "total_fat_g": 3.5}
        ocr_nutrition = {"energy_kcal": 62.0, "protein_g": 1.2, "total_fat_g": 3.5} # altered protein
        verification = NutritionVerifier.verify_ocr_vs_database(db_nutrition, ocr_nutrition)
        self.assertTrue(verification["has_mismatch"])
        self.assertIn("VALUE MISMATCH", verification["overall_status"])

    def test_M_N3_milk_partially_unreadable(self):
        db_nutrition = {"energy_kcal": 62.0, "protein_g": 3.2, "calcium_mg": 120.0}
        ocr_nutrition = {"energy_kcal": 62.0, "protein_g": 3.2, "calcium_mg": "Not detected"}
        verification = NutritionVerifier.verify_ocr_vs_database(db_nutrition, ocr_nutrition)
        self.assertEqual(verification["field_comparisons"]["calcium_mg"]["status"], "❌ UNABLE TO VERIFY")

    def test_M_N4_milk_nutrition_plus_quality_separated(self):
        db_nutrition = {"energy_kcal": 62.0, "protein_g": 3.2, "total_fat_g": 3.5}
        ocr_nutrition = {"energy_kcal": 62.0, "protein_g": 3.2, "total_fat_g": 3.5}
        verification = NutritionVerifier.verify_ocr_vs_database(db_nutrition, ocr_nutrition)
        
        # Verify milk quality params evaluated separately in DecisionEngine without mutating nutrition data
        from backend.services.decision_engine import DecisionEngine
        res = DecisionEngine.evaluate(
            expected_product="Milk Pouch",
            detected_product="Milk Pouch",
            product_confidence=0.95,
            packaging_condition="Normal Package",
            condition_confidence=0.92,
            ocr_data={"is_label_found": True},
            milk_lab_params={"fat": 3.8, "snf": 8.6, "ph": 6.6, "temperature": 5.0}
        )
        self.assertEqual(res["checklist"]["Milk Quality"], "✅")
        self.assertEqual(res["milk_params_eval"]["fat"], 3.8)
        self.assertEqual(res["verified_nutrition"]["protein"], "3.1 g")

if __name__ == "__main__":
    unittest.main()
