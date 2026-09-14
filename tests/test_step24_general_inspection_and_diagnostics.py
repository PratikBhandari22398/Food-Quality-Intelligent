import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.db.database import Base, get_db
from backend.db.models import Product, Batch, Inspection
from backend.services.decision_engine import DecisionEngine

class TestStep24InspectionLogic(unittest.TestCase):
    def setUp(self):
        """Set up an in-memory SQLite database and test client."""
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        TestingSessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = TestingSessionLocal()

        def override_get_db():
            try:
                yield self.db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()

    def test_01_general_inspection_milk_pouch_pass(self):
        """TEST 1: Milk Pouch + Normal Package in General Inspection mode (Not Specified) yields PASS."""
        res = DecisionEngine.evaluate(
            expected_product="Not Specified",
            detected_product="Milk Pouch",
            product_confidence=0.98,
            packaging_condition="Normal Package",
            condition_confidence=0.97
        )
        self.assertEqual(res["final_status"], "PASS")
        self.assertEqual(res["checklist"]["Product Match"], "N/A")
        self.assertTrue(any("Product and package verified" in r or "passed" in r.lower() for r in res["reasons"] or [res["recommended_action"]]))

    def test_02_general_inspection_chips_packet_pass(self):
        """TEST 2: Chips Packet + Normal Package in General Inspection mode (Not Specified) yields PASS."""
        res = DecisionEngine.evaluate(
            expected_product="Not Specified",
            detected_product="Chips Packet",
            product_confidence=0.96,
            packaging_condition="Normal Package",
            condition_confidence=0.95
        )
        self.assertEqual(res["final_status"], "PASS")
        self.assertEqual(res["checklist"]["Product Match"], "N/A")

    def test_03_explicit_batch_linked_mismatch_hold(self):
        """TEST 3: Expected Chips Packet vs Detected Milk Pouch yields HOLD."""
        res = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="Milk Pouch",
            product_confidence=0.95,
            packaging_condition="Normal Package",
            condition_confidence=0.94
        )
        self.assertEqual(res["final_status"], "HOLD")
        self.assertEqual(res["checklist"]["Product Match"], "❌")

    def test_04_damaged_package_reject(self):
        """TEST 4: Packaging condition 'damage package' yields REJECT."""
        res = DecisionEngine.evaluate(
            expected_product="Not Specified",
            detected_product="Chips Packet",
            product_confidence=0.99,
            packaging_condition="damage package",
            condition_confidence=0.645
        )
        self.assertEqual(res["final_status"], "REJECT")
        self.assertEqual(res["checklist"]["Package Condition"], "❌")

    def test_05_unlinked_inspection_saves_batch_id_none(self):
        """TEST 5: Saving an inspection without explicit batch linkage stores batch_id = None."""
        payload = {
            "expected_product": "Not Specified",
            "detected_product": "Milk Pouch",
            "product_confidence": 0.98,
            "packaging_condition": "Normal Package",
            "condition_confidence": 0.96
        }
        res = self.client.post("/api/inspect/save", json=payload)
        self.assertEqual(res.status_code, 200)
        saved_data = res.json()
        self.assertIsNone(saved_data.get("batch_id"))

if __name__ == "__main__":
    unittest.main()
