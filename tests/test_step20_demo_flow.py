import unittest
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.main import app
from backend.config import DEFAULT_NUTRITION_PROFILES
from backend.services.decision_engine import DecisionEngine

client = TestClient(app)

class TestStep20DemoFlow(unittest.TestCase):

    def test_01_lays_classic_salted_profile(self):
        """Test Lay's Classic Salted profile lookup & per-serving/per-pack math."""
        response = client.get("/api/inspect/product-profile/Lay's Classic Salted")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        profile = data.get("profile", {})
        self.assertEqual(profile["mrp"], "₹20")
        self.assertEqual(profile["net_weight"], "50 g")
        self.assertEqual(profile["serving_size"], "20 g")
        self.assertEqual(profile["nutrition_basis"], "Per 100 g")

        nutr = profile["nutrition_per_100g"]
        self.assertEqual(nutr.get("energy"), "553 kcal")
        self.assertEqual(nutr.get("protein"), "6.7 g")
        self.assertEqual(nutr.get("carbohydrates"), "52.6 g")
        self.assertEqual(nutr.get("total_sugars"), "0.6 g")
        self.assertEqual(nutr.get("added_sugars"), "0 g")
        self.assertEqual(nutr.get("total_fat"), "35.1 g")
        self.assertEqual(nutr.get("saturated_fat"), "15.8 g")
        self.assertEqual(nutr.get("trans_fat"), "0.1 g")
        self.assertEqual(nutr.get("sodium"), "500 mg")

        per_serving = profile["per_serving_table"]
        # 553 * 20 / 100 = 110.6 kcal
        self.assertIn("110.6 kcal", per_serving.get("energy", ""))

    def test_02_lays_spanish_tomato_tango_profile(self):
        """Test Lay's Spanish Tomato Tango profile lookup & per-serving math."""
        response = client.get("/api/inspect/product-profile/Lay's Spanish Tomato Tango")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        profile = data.get("profile", {})
        self.assertEqual(profile["mrp"], "₹20")
        nutr = profile["nutrition_per_100g"]
        self.assertEqual(nutr.get("energy"), "525 kcal")
        self.assertEqual(nutr.get("protein"), "6.4 g")
        self.assertEqual(nutr.get("carbohydrates"), "53.1 g")
        self.assertEqual(nutr.get("total_sugars"), "5.6 g")
        self.assertEqual(nutr.get("added_sugars"), "4.7 g")
        self.assertEqual(nutr.get("total_fat"), "31.9 g")
        self.assertEqual(nutr.get("saturated_fat"), "14.3 g")
        self.assertEqual(nutr.get("sodium"), "659 mg")

    def test_03_10_rupees_milk_pouch_profile(self):
        """Test ₹10 Milk Pouch profile lookup."""
        response = client.get("/api/inspect/product-profile/₹10 Milk Pouch")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        profile = data.get("profile", {})
        self.assertEqual(profile["mrp"], "₹10")
        self.assertEqual(profile["net_weight"], "170 ml")
        self.assertEqual(profile["nutrition_basis"], "Per 100 ml")
        nutr = profile["nutrition_per_100g"]
        self.assertEqual(nutr.get("energy"), "58 kcal")
        self.assertEqual(nutr.get("protein"), "3.1 g")
        self.assertEqual(nutr.get("calcium"), "116 mg")

    def test_04_31_rupees_milk_pouch_profile(self):
        """Test ₹31 Milk Pouch profile lookup."""
        response = client.get("/api/inspect/product-profile/₹31 Milk Pouch")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        profile = data.get("profile", {})
        self.assertEqual(profile["mrp"], "₹31")
        self.assertEqual(profile["net_weight"], "500 ml")
        self.assertEqual(profile["nutrition_basis"], "Per 100 ml")
        nutr = profile["nutrition_per_100g"]
        self.assertEqual(nutr.get("energy"), "69 kcal")
        self.assertEqual(nutr.get("protein"), "3.1 g")
        self.assertEqual(nutr.get("total_fat"), "4.0 g")

    def test_05_decision_engine_pass_without_ocr(self):
        """Verify decision engine PASS when OCR data is omitted (ocr_data=None)."""
        decision = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="Chips Packet",
            product_confidence=0.95,
            packaging_condition="Normal Package",
            condition_confidence=0.98,
            ocr_data=None
        )
        self.assertEqual(decision["final_status"], "PASS")

    def test_06_decision_engine_damaged_package_reject(self):
        """Verify decision engine REJECT when package is damaged."""
        decision = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="Chips Packet",
            product_confidence=0.95,
            packaging_condition="Damaged Package",
            condition_confidence=0.98,
            ocr_data=None
        )
        self.assertEqual(decision["final_status"], "REJECT")

    def test_07_decision_engine_category_mismatch_hold(self):
        """Verify decision engine HOLD on category mismatch."""
        decision = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="Milk Pouch",
            product_confidence=0.95,
            packaging_condition="Normal Package",
            condition_confidence=0.98,
            ocr_data=None
        )
        self.assertEqual(decision["final_status"], "HOLD")

    def test_08_decision_engine_other_object_hold(self):
        """Verify decision engine HOLD when detected product is Other Object."""
        decision = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="Other Object",
            product_confidence=0.95,
            packaging_condition="Normal Package",
            condition_confidence=0.98,
            ocr_data=None
        )
        self.assertEqual(decision["final_status"], "HOLD")

    def test_09_decision_engine_other_food_product_warning(self):
        """Verify decision engine WARNING when detected product is Other Food Product."""
        decision = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="Other Food Product",
            product_confidence=0.95,
            packaging_condition="Normal Package",
            condition_confidence=0.98,
            ocr_data=None
        )
        self.assertEqual(decision["final_status"], "WARNING")

if __name__ == "__main__":
    unittest.main()
