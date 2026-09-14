import unittest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.ocr_service import OCRService
from backend.services.decision_engine import DecisionEngine

class TestStep15OCRPartialSuccess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_1_nutrition_only_chips_image(self):
        sample_text = """
        NUTRITION INFORMATION
        Per 100 g
        Energy: 553 kcal
        Protein: 6.7 g
        Carbohydrate: 52.6 g
        Total Sugars: 0.6 g
        Total Fat: 35.1 g
        Saturated Fat: 15.8 g
        Sodium: 500 mg
        """
        res = OCRService.parse_extracted_text(sample_text)
        self.assertEqual(res["ocr_status"], "nutrition_detected")
        self.assertEqual(res["nutrition_status"], "detected")
        self.assertEqual(res["nutrition_data"]["energy_kcal"], 553.0)
        self.assertEqual(res["nutrition_data"]["protein_g"], 6.7)
        self.assertEqual(res["fields"]["batch_number"]["status"], "not_detected")
        self.assertEqual(res["fields"]["best_before"]["status"], "not_detected")

    def test_2_full_chips_back_image_missing_batch(self):
        sample_text = """
        Lay's Classic Salted Chips
        NET WT: 50 g
        NUTRITION FACTS
        Energy: 536 kcal
        Protein: 7.0 g
        Total Fat: 33.0 g
        Sodium: 520 mg
        BEST BEFORE 25/12/2026
        """
        res = OCRService.parse_extracted_text(sample_text)
        self.assertIn(res["ocr_status"], ["nutrition_detected", "partial_success", "complete"])
        self.assertEqual(res["fields"]["batch_number"]["status"], "not_detected")
        self.assertEqual(res["fields"]["net_weight"]["status"], "detected")
        self.assertEqual(res["fields"]["best_before"]["status"], "detected")

    def test_3_relative_best_before_statement_without_mfg_date(self):
        sample_text = """
        Crispy Potato Chips
        NET WT: 50 g
        BEST BEFORE FOUR MONTHS FROM MANUFACTURE
        NUTRITION FACTS: Energy 536 kcal, Protein 7.0 g, Total Fat 33.0 g
        """
        res = OCRService.parse_extracted_text(sample_text)
        self.assertEqual(res["fields"]["best_before"]["status"], "relative_statement")
        self.assertIsNotNone(res["fields"]["best_before"]["notice"])
        self.assertIn("relative to the manufacturing date", res["fields"]["best_before"]["notice"])
        self.assertIsNone(res["exp_date"])

    def test_4_nutrition_only_milk_image(self):
        sample_text = """
        NUTRITION FACTS
        Per 100 ml
        Energy: 62 kcal
        Protein: 3.2 g
        Total Fat: 3.5 g
        Calcium: 120 mg
        """
        res = OCRService.parse_extracted_text(sample_text)
        self.assertEqual(res["ocr_status"], "nutrition_detected")
        self.assertEqual(res["nutrition_status"], "detected")
        self.assertEqual(res["nutrition_data"]["calcium_mg"], 120.0)

    def test_5_full_milk_label(self):
        sample_text = """
        Pure Dairy Toned Milk
        BATCH NO: BATCH-MILK-99
        BEST BEFORE 30/11/2026
        NET QTY: 500 ml
        NUTRITION FACTS: Energy 62 kcal, Protein 3.2 g
        """
        res = OCRService.parse_extracted_text(sample_text)
        self.assertEqual(res["fields"]["batch_number"]["value"], "BATCH-MILK-99")
        self.assertIn(res["fields"]["best_before"]["value"], ["2026-11-30", "30/11/2026"])
        self.assertEqual(res["fields"]["net_weight"]["value"], "500 ml")
        self.assertEqual(res["nutrition_status"], "detected")

    def test_6_completely_blank_image(self):
        res = OCRService.parse_extracted_text("")
        self.assertEqual(res["ocr_status"], "unclear")
        self.assertFalse(res["is_label_found"])
        self.assertFalse(res["system_error"])

    def test_7_ocr_payload_empty_corrupted(self):
        res = OCRService.process_image(b"")
        self.assertEqual(res["ocr_status"], "failed")
        self.assertTrue(res["system_error"])

    def test_8_decision_engine_partial_ocr_evaluation(self):
        sample_ocr_res = OCRService.parse_extracted_text("""
        NUTRITION FACTS
        Energy: 536 kcal, Protein: 7.0 g
        """)
        eval_result = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="Chips Packet",
            product_confidence=0.95,
            packaging_condition="Normal Package",
            condition_confidence=0.95,
            ocr_data=sample_ocr_res
        )
        self.assertEqual(eval_result["final_status"], "WARNING")
        self.assertIn("Batch number not detected on package label.", eval_result["reasons"])
        self.assertEqual(eval_result["checklist"]["Nutrition"], "✅")

if __name__ == "__main__":
    unittest.main()
