import unittest
from backend.services.decision_engine import DecisionEngine

class TestEndToEndInspectionWorkflow(unittest.TestCase):

    def test_1_good_chips_packet(self):
        """TEST 1: Good chips packet -> Expected PASS"""
        res = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="Chips Packet",
            product_confidence=0.96,
            packaging_condition="Normal Package",
            condition_confidence=0.98,
            ocr_data={
                "batch_number": "BAT-2026-CHIPS-01",
                "exp_date": "2028-12-31",
                "expiry_status": "VALID",
                "is_label_found": True,
                "has_nutrition_mismatch": False
            }
        )
        self.assertEqual(res["final_status"], "PASS")
        self.assertEqual(res["checklist"]["Product Match"], "✅")
        self.assertEqual(res["checklist"]["Package Condition"], "✅")

    def test_2_good_milk_pouch(self):
        """TEST 2: Good milk pouch -> Expected PASS"""
        res = DecisionEngine.evaluate(
            expected_product="Milk Pouch",
            detected_product="Milk Pouch",
            product_confidence=0.95,
            packaging_condition="Normal Package",
            condition_confidence=0.97,
            ocr_data={
                "batch_number": "LOT-MILK-99",
                "exp_date": "2028-10-15",
                "expiry_status": "VALID",
                "is_label_found": True
            },
            milk_lab_params={
                "fat": 3.8,
                "snf": 8.7,
                "ph": 6.6,
                "temperature": 5.0
            }
        )
        self.assertEqual(res["final_status"], "PASS")
        self.assertEqual(res["checklist"]["Milk Quality"], "✅")

    def test_3_wrong_product_mismatch(self):
        """TEST 3: Wrong product (Expected Chips, AI detected Milk) -> Expected HOLD"""
        res = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="Milk Pouch",
            product_confidence=0.92,
            packaging_condition="Normal Package",
            condition_confidence=0.95
        )
        self.assertEqual(res["final_status"], "HOLD")
        self.assertEqual(res["checklist"]["Product Match"], "❌")
        self.assertTrue(any("Product Verification Failed" in r for r in res["reasons"]))

    def test_4_damaged_package(self):
        """TEST 4: Damaged package -> Expected REJECT"""
        res = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="Chips Packet",
            product_confidence=0.94,
            packaging_condition="damage package",
            condition_confidence=0.91
        )
        self.assertEqual(res["final_status"], "REJECT")
        self.assertEqual(res["checklist"]["Package Condition"], "❌")
        self.assertTrue(any("damage" in r.lower() for r in res["reasons"]))

    def test_5_unclear_image(self):
        """TEST 5: Unclear image / low confidence -> Expected WARNING"""
        res = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="Chips Packet",
            product_confidence=0.55, # below 0.65 threshold
            packaging_condition="unclear",
            condition_confidence=0.50
        )
        self.assertEqual(res["final_status"], "WARNING")
        self.assertEqual(res["checklist"]["Package Condition"], "⚠")

    def test_6_expired_best_before(self):
        """TEST 6: Expired best-before verification -> Expected REJECT"""
        res = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="Chips Packet",
            product_confidence=0.95,
            packaging_condition="Normal Package",
            condition_confidence=0.96,
            ocr_data={
                "batch_number": "BAT-2022-EXP",
                "exp_date": "2022-01-01",
                "expiry_status": "EXPIRED",
                "is_label_found": True
            }
        )
        self.assertEqual(res["final_status"], "REJECT")
        self.assertEqual(res["checklist"]["Best Before"], "❌")
        self.assertTrue(any("expired" in r.lower() for r in res["reasons"]))

    def test_7_nutrition_mismatch(self):
        """TEST 7: Nutrition OCR vs DB mismatch -> Expected WARNING"""
        res = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="Chips Packet",
            product_confidence=0.96,
            packaging_condition="Normal Package",
            condition_confidence=0.97,
            ocr_data={
                "batch_number": "BAT-MISMATCH-1",
                "exp_date": "2028-12-31",
                "expiry_status": "VALID",
                "is_label_found": True,
                "has_nutrition_mismatch": True
            }
        )
        self.assertEqual(res["final_status"], "WARNING")
        self.assertEqual(res["checklist"]["Nutrition"], "⚠")
        self.assertTrue(any("Nutrition value mismatch" in r for r in res["reasons"]))

    def test_8_missing_ocr_information(self):
        """TEST 8: Missing OCR label information -> Expected WARNING"""
        res = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="Chips Packet",
            product_confidence=0.95,
            packaging_condition="Normal Package",
            condition_confidence=0.96,
            ocr_data={
                "is_label_found": False
            }
        )
        self.assertEqual(res["final_status"], "PASS")

    def test_9_other_food_product(self):
        """TEST 9: Other food product -> Expected WARNING / limited verification"""
        res = DecisionEngine.evaluate(
            expected_product="Other Food Product",
            detected_product="other food product",
            product_confidence=0.90,
            packaging_condition="Normal Package",
            condition_confidence=0.92
        )
        self.assertEqual(res["final_status"], "WARNING")
        self.assertTrue(any("detailed verification data is unavailable" in r for r in res["reasons"]))

    def test_10_other_object(self):
        """TEST 10: Other object (non-food) -> Expected HOLD / unsupported product handling"""
        res = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="other object",
            product_confidence=0.93,
            packaging_condition="Normal Package",
            condition_confidence=0.91
        )
        self.assertEqual(res["final_status"], "HOLD")
        self.assertEqual(res["checklist"]["Product Detection"], "❌")
        self.assertTrue(any("Not a supported food product" in r for r in res["reasons"]))

    def test_11_front_image_only_incomplete_inspection(self):
        """TEST 11: Front image captured without back label -> Expected PASS per Step 20 optional OCR rules"""
        res = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="Chips Packet",
            product_confidence=0.96,
            packaging_condition="Normal Package",
            condition_confidence=0.98,
            ocr_data=None # Back-side label optional
        )
        self.assertEqual(res["final_status"], "PASS")

if __name__ == "__main__":
    unittest.main()
