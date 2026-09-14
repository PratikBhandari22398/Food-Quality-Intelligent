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

class TestStep17AutoNutrition(unittest.TestCase):

    def test_01_get_product_profile_classic_salted(self):
        """Test fetching Lay's Classic Salted profile with calculated per-serving and per-pack values."""
        response = client.get("/api/inspect/product-profile/Lay's Classic Salted")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        profile = data.get("profile")
        self.assertIsNotNone(profile)
        self.assertEqual(profile["mrp"], "₹20")
        self.assertEqual(profile["net_weight"], "50 g")
        self.assertEqual(profile["serving_size"], "20 g")
        self.assertEqual(profile["nutrition_basis"], "Per 100 g")

        nutrition_100g = profile["nutrition_per_100g"]
        per_serving = profile["per_serving_table"]
        per_pack = profile["per_pack_table"]

        # Check energy: 553 kcal per 100g -> (553 * 20 / 100) = 110.6 kcal serving -> (553 * 50 / 100) = 276.5 kcal pack
        self.assertIn("553 kcal", nutrition_100g.get("energy", ""))
        self.assertIn("110.6 kcal", per_serving.get("energy", ""))
        self.assertIn("276.5 kcal", per_pack.get("energy", ""))

    def test_02_get_product_profile_tomato_tango(self):
        """Test fetching Lay's Spanish Tomato Tango profile."""
        response = client.get("/api/inspect/product-profile/Lay's Spanish Tomato Tango")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        profile = data.get("profile")
        self.assertEqual(profile["mrp"], "₹20")
        self.assertIn("525 kcal", profile["nutrition_per_100g"].get("energy", ""))
        self.assertIn("105", profile["per_serving_table"].get("energy", ""))

    def test_03_get_product_profile_toned_milk(self):
        """Test fetching Pure Dairy Toned Milk profile."""
        response = client.get("/api/inspect/product-profile/Pure Dairy Toned Milk")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        profile = data.get("profile")
        self.assertEqual(profile["mrp"], "₹31")
        self.assertEqual(profile["net_weight"], "500 ml")
        self.assertEqual(profile["serving_size"], "150 ml")
        self.assertEqual(profile["nutrition_basis"], "Per 100 ml")
        # Energy per 100ml is 69 kcal -> per serving (150ml) = 103.5 kcal -> per pack (500ml) = 345 kcal
        self.assertIn("69 kcal", profile["nutrition_per_100g"].get("energy", ""))
        self.assertIn("103.5", profile["per_serving_table"].get("energy", ""))
        self.assertIn("345", profile["per_pack_table"].get("energy", ""))

    def test_04_fallback_category_profile(self):
        """Test fallback when passing category name like 'Chips Packet'."""
        response = client.get("/api/inspect/product-profile/Chips Packet")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["profile"]["variant_name"], "Chips Packet")

    def test_05_unknown_variant_fallback_to_category(self):
        """Test non-existent variant returns 404."""
        response = client.get("/api/inspect/product-profile/Unknown Nonexistent Variant")
        self.assertEqual(response.status_code, 404)

    def test_06_decision_engine_category_mismatch_hold(self):
        """Test decision engine holds on category mismatch."""
        decision = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="Milk Pouch",
            product_confidence=0.95,
            packaging_condition="Sealed",
            condition_confidence=0.98,
            ocr_data={"ocr_status": "unclear"}
        )
        self.assertEqual(decision["final_status"], "HOLD")
        self.assertTrue(any("mismatch" in r.lower() or "category" in r.lower() or "failed" in r.lower() for r in decision["reasons"]))

    def test_07_decision_engine_other_object_hold(self):
        """Test decision engine holds when detected category is Other Object."""
        decision = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="Other Object",
            product_confidence=0.95,
            packaging_condition="Sealed",
            condition_confidence=0.98
        )
        self.assertEqual(decision["final_status"], "HOLD")

    def test_08_decision_engine_other_food_product_warning(self):
        """Test decision engine gives WARNING when detected category is Other Food Product."""
        decision = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="Other Food Product",
            product_confidence=0.95,
            packaging_condition="Sealed",
            condition_confidence=0.98
        )
        self.assertEqual(decision["final_status"], "WARNING")

    def test_09_decision_engine_variant_mismatch_warning(self):
        """Test decision engine warning when low AI confidence or minor label discrepancy."""
        decision = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="Chips Packet",
            product_confidence=0.60,
            packaging_condition="Sealed",
            condition_confidence=0.98
        )
        self.assertEqual(decision["final_status"], "WARNING")

    def test_10_decision_engine_pass_when_all_valid(self):
        """Test decision engine PASS when category, packaging, and profile match."""
        decision = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="Chips Packet",
            product_confidence=0.95,
            packaging_condition="Sealed",
            condition_confidence=0.98,
            ocr_data={"ocr_status": "complete", "is_label_found": True, "fields": {"batch_number": {"status": "detected"}}}
        )
        self.assertEqual(decision["final_status"], "PASS")

    def test_11_verify_default_nutrition_profiles_config(self):
        """Verify DEFAULT_NUTRITION_PROFILES contains required keys and fields."""
        self.assertIn("Lay's Classic Salted", DEFAULT_NUTRITION_PROFILES)
        self.assertIn("Lay's Spanish Tomato Tango", DEFAULT_NUTRITION_PROFILES)
        self.assertIn("Pure Dairy Toned Milk", DEFAULT_NUTRITION_PROFILES)

        classic = DEFAULT_NUTRITION_PROFILES["Lay's Classic Salted"]
        self.assertEqual(classic["mrp"], "₹20")
        self.assertEqual(classic["net_weight"], "50 g")
        self.assertEqual(classic["serving_size"], "20 g")
        self.assertEqual(classic["basis"], "Per 100 g")
        self.assertEqual(classic["nutrition_table"]["energy"], "553 kcal")

    def test_12_ocr_independence_db_nutrition_persistence(self):
        """Verify DB nutrition profile structure does not rely on OCR fields."""
        profile = DEFAULT_NUTRITION_PROFILES["Pure Dairy Toned Milk"]
        self.assertIsNotNone(profile.get("nutrition_table"))
        self.assertTrue(len(profile["nutrition_table"]) >= 5)

if __name__ == "__main__":
    unittest.main()
