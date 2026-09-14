import unittest
from backend.services.decision_engine import DecisionEngine

class TestDecisionEngine(unittest.TestCase):
    def test_decision_pass(self):
        res = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="Chips Packet",
            product_confidence=0.95,
            packaging_condition="Normal Package",
            condition_confidence=0.98,
            ocr_data={"exp_date": "2028-12-31", "is_label_found": True}
        )
        self.assertEqual(res["final_status"], "PASS")
        self.assertTrue(len(res["reasons"]) > 0)

    def test_decision_product_mismatch_hold(self):
        res = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="Milk Pouch",
            product_confidence=0.92,
            packaging_condition="Normal Package",
            condition_confidence=0.95
        )
        self.assertEqual(res["final_status"], "HOLD")
        self.assertTrue(any("Product Verification Failed" in r for r in res["reasons"]))

    def test_decision_damaged_package_reject(self):
        res = DecisionEngine.evaluate(
            expected_product="Milk Pouch",
            detected_product="Milk Pouch",
            product_confidence=0.91,
            packaging_condition="Damaged Package",
            condition_confidence=0.88
        )
        self.assertEqual(res["final_status"], "REJECT")
        self.assertTrue(any("Package Defect" in r for r in res["reasons"]))

    def test_decision_milk_ph_failure_reject(self):
        res = DecisionEngine.evaluate(
            expected_product="Milk Pouch",
            detected_product="Milk Pouch",
            product_confidence=0.95,
            packaging_condition="Normal Package",
            condition_confidence=0.95,
            milk_lab_params={"ph": 5.8, "temperature": 4.0, "fat": 3.8, "snf": 8.6}
        )
        self.assertEqual(res["final_status"], "REJECT")
        self.assertTrue(any("Critical Milk Quality Failure" in r for r in res["reasons"]))

    def test_decision_milk_low_fat_hold(self):
        res = DecisionEngine.evaluate(
            expected_product="Milk Pouch",
            detected_product="Milk Pouch",
            product_confidence=0.95,
            packaging_condition="Normal Package",
            condition_confidence=0.95,
            milk_lab_params={"ph": 6.6, "temperature": 5.0, "fat": 2.5, "snf": 8.6}
        )
        self.assertEqual(res["final_status"], "HOLD")
        self.assertTrue(any("Sub-standard Fat Content" in r for r in res["reasons"]))

if __name__ == "__main__":
    unittest.main()
