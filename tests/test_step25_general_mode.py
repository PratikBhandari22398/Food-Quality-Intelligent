import unittest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.decision_engine import DecisionEngine
from backend.db.database import get_db, Base, engine
from backend.db.models import Batch, Product, Inspection

class TestStep25GeneralMode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        Base.metadata.create_all(bind=engine)

    def test_1_general_milk_normal(self):
        """TEST 1: General + Milk + Normal -> PASS"""
        res = DecisionEngine.evaluate(
            expected_product="Not Specified",
            detected_product="Milk Pouch",
            product_confidence=1.0,
            packaging_condition="Normal Package",
            condition_confidence=1.0
        )
        self.assertEqual(res["final_status"], "PASS")
        self.assertEqual(res["checklist"]["Product Match"], "N/A")
        self.assertTrue(any("Milk pouch detected" in r for r in res["reasons"]))

    def test_2_general_chips_normal(self):
        """TEST 2: General + Chips + Normal -> PASS"""
        res = DecisionEngine.evaluate(
            expected_product="Not Specified",
            detected_product="Chips Packet",
            product_confidence=1.0,
            packaging_condition="Normal Package",
            condition_confidence=1.0
        )
        self.assertEqual(res["final_status"], "PASS")
        self.assertEqual(res["checklist"]["Product Match"], "N/A")
        self.assertTrue(any("Chips packet detected" in r for r in res["reasons"]))

    def test_3_general_chips_damage(self):
        """TEST 3: General + Chips + Damage -> REJECT"""
        res = DecisionEngine.evaluate(
            expected_product="Not Specified",
            detected_product="Chips Packet",
            product_confidence=1.0,
            packaging_condition="Damaged Package",
            condition_confidence=1.0
        )
        self.assertEqual(res["final_status"], "REJECT")
        self.assertTrue(any("Visible package damage detected" in r for r in res["reasons"]))

    def test_4_general_milk_unclear_package(self):
        """TEST 4: General + Milk + Unclear Package -> WARNING"""
        res = DecisionEngine.evaluate(
            expected_product="Not Specified",
            detected_product="Milk Pouch",
            product_confidence=1.0,
            packaging_condition="Unclear Package",
            condition_confidence=0.5
        )
        self.assertEqual(res["final_status"], "WARNING")
        self.assertTrue(any("Package condition could not be verified" in r for r in res["reasons"]))

    def test_5_general_other_object(self):
        """TEST 5: General + Other Object -> HOLD"""
        res = DecisionEngine.evaluate(
            expected_product="Not Specified",
            detected_product="Other Object",
            product_confidence=1.0,
            packaging_condition="Normal Package",
            condition_confidence=1.0
        )
        self.assertEqual(res["final_status"], "HOLD")
        self.assertTrue(any("No supported food product detected" in r for r in res["reasons"]))

    def test_6_expected_chips_detected_milk(self):
        """TEST 6: Expected Chips + Detected Milk -> HOLD"""
        res = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="Milk Pouch",
            product_confidence=1.0,
            packaging_condition="Normal Package",
            condition_confidence=1.0
        )
        self.assertEqual(res["final_status"], "HOLD")
        self.assertTrue(any("Expected and detected products do not match" in r for r in res["reasons"]))

    def test_7_chips_batch_selected_then_general_milk(self):
        """TEST 7: Select Chips batch, then General Milk inspection -> PASS"""
        # Active batch should NOT leak into General Milk inspection
        res = DecisionEngine.evaluate(
            expected_product="Not Specified",
            detected_product="Milk Pouch",
            product_confidence=1.0,
            packaging_condition="Normal Package",
            condition_confidence=1.0,
            batch_number="CHIPS-BATCH-99"
        )
        self.assertEqual(res["final_status"], "PASS")

    def test_8_general_inspection_batch_id_null(self):
        """TEST 8: General inspection batch_id -> NULL"""
        payload = {
            "expected_product": "Not Specified",
            "detected_product": "Milk Pouch",
            "product_confidence": 1.0,
            "packaging_condition": "Normal Package",
            "condition_confidence": 1.0,
            "batch_number": "CHIPS-BATCH-99"
        }
        resp = self.client.post("/api/inspect/save", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsNone(data["batch_id"])
        self.assertEqual(data["batch_number"], "N/A")

    def test_9_explicit_batch_linked_inspection(self):
        """TEST 9: Explicit batch-linked inspection -> batch_id populated"""
        # First ensure a batch exists in DB
        db = next(get_db())
        p = db.query(Product).first()
        import uuid
        b_num = f"TEST-BATCH-{uuid.uuid4().hex[:6]}"
        b = Batch(batch_number=b_num, product_id=prod_id)
        db.add(b)
        db.commit()
        db.refresh(b)

        payload = {
            "expected_product": "Chips Packet",
            "detected_product": "Chips Packet",
            "product_confidence": 1.0,
            "packaging_condition": "Normal Package",
            "condition_confidence": 1.0,
            "batch_id": b.id,
            "batch_number": b.batch_number
        }
        resp = self.client.post("/api/inspect/save", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["batch_id"], b.id)

    def test_10_previous_expected_product_leakage(self):
        """TEST 10: Previous expected product must not leak into new inspection"""
        res_explicit = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="Milk Pouch",
            product_confidence=1.0,
            packaging_condition="Normal Package",
            condition_confidence=1.0
        )
        self.assertEqual(res_explicit["final_status"], "HOLD")

        res_next_general = DecisionEngine.evaluate(
            expected_product="Not Specified",
            detected_product="Milk Pouch",
            product_confidence=1.0,
            packaging_condition="Normal Package",
            condition_confidence=1.0
        )
        self.assertEqual(res_next_general["final_status"], "PASS")

if __name__ == "__main__":
    unittest.main()
