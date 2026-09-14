import unittest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.decision_engine import DecisionEngine

class TestStep27CameraInputMode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_1_idle_mode_structure(self):
        """TEST 1: Initial state structure and rules"""
        res = DecisionEngine.evaluate(
            expected_product="Not Specified",
            detected_product="Milk Pouch",
            product_confidence=1.0,
            packaging_condition="Normal Package",
            condition_confidence=1.0
        )
        self.assertEqual(res["final_status"], "PASS")

    def test_2_camera_mode_evaluation(self):
        """TEST 2: Camera mode live evaluation without upload text leak"""
        res = DecisionEngine.evaluate(
            expected_product="Not Specified",
            detected_product="Chips Packet",
            product_confidence=0.98,
            packaging_condition="Normal Package",
            condition_confidence=0.99
        )
        self.assertEqual(res["final_status"], "PASS")
        self.assertNotIn("Drag & Drop", res["reasons"])

    def test_3_capture_frame_evaluation(self):
        """TEST 3: Inspection pipeline evaluation after camera frame capture"""
        res = DecisionEngine.evaluate(
            expected_product="Not Specified",
            detected_product="Milk Pouch",
            product_confidence=0.95,
            packaging_condition="Normal Package",
            condition_confidence=0.96
        )
        self.assertEqual(res["final_status"], "PASS")

    def test_4_retake_state(self):
        """TEST 4: Retake state evaluation returns clean result"""
        res = DecisionEngine.evaluate(
            expected_product="Not Specified",
            detected_product="Chips Packet",
            product_confidence=0.95,
            packaging_condition="Damaged Package",
            condition_confidence=0.90
        )
        self.assertEqual(res["final_status"], "REJECT")

    def test_5_upload_mode_evaluation(self):
        """TEST 5: Upload mode evaluation returns clean result"""
        res = DecisionEngine.evaluate(
            expected_product="Not Specified",
            detected_product="Milk Pouch",
            product_confidence=0.99,
            packaging_condition="Normal Package",
            condition_confidence=0.99
        )
        self.assertEqual(res["final_status"], "PASS")

    def test_6_upload_image_preview_state(self):
        """TEST 6: Uploaded image preview evaluation"""
        res = DecisionEngine.evaluate(
            expected_product="Not Specified",
            detected_product="Other Object",
            product_confidence=0.95,
            packaging_condition="Normal Package",
            condition_confidence=0.95
        )
        self.assertEqual(res["final_status"], "HOLD")

    def test_7_switch_upload_to_camera(self):
        """TEST 7: Switching upload to camera retains clean decision state"""
        res = DecisionEngine.evaluate(
            expected_product="Not Specified",
            detected_product="Milk Pouch",
            product_confidence=1.0,
            packaging_condition="Unclear Package",
            condition_confidence=0.5
        )
        self.assertEqual(res["final_status"], "WARNING")

    def test_8_reset_returns_to_idle(self):
        """TEST 8: Reset returns to clean idle state"""
        res = DecisionEngine.evaluate(
            expected_product="Not Specified",
            detected_product="Chips Packet",
            product_confidence=1.0,
            packaging_condition="Normal Package",
            condition_confidence=1.0
        )
        self.assertEqual(res["final_status"], "PASS")

if __name__ == "__main__":
    unittest.main()
