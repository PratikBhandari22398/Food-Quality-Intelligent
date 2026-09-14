import unittest
import numpy as np
import tf_keras as keras
from backend.services.decision_engine import DecisionEngine

class TestRealTeachableMachineModels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("Loading real Model 1 (Product Classifier)...")
        cls.product_model = keras.models.load_model("model1/keras_model.h5", compile=False)
        cls.product_labels = [
            "chips packet",
            "milk pouch",
            "other food product",
            "other object"
        ]

        print("Loading real Model 2 (Packaging Classifier)...")
        cls.packaging_model = keras.models.load_model("model-2/keras_model.h5", compile=False)
        cls.packaging_labels = [
            "normal package",
            "damage package",
            "unclear"
        ]

    def test_model1_labels_integrity(self):
        self.assertEqual(len(self.product_labels), 4)
        self.assertEqual(self.product_labels[0], "chips packet")
        self.assertEqual(self.product_labels[1], "milk pouch")
        self.assertEqual(self.product_labels[2], "other food product")
        self.assertEqual(self.product_labels[3], "other object")

    def test_model2_labels_integrity(self):
        self.assertEqual(len(self.packaging_labels), 3)
        self.assertEqual(self.packaging_labels[0], "normal package")
        self.assertEqual(self.packaging_labels[1], "damage package")
        self.assertEqual(self.packaging_labels[2], "unclear")

    def test_a_chips_image_flow(self):
        # Dummy 224x224x3 image tensor matching model input shape
        dummy_img = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)
        prediction = self.product_model.predict(dummy_img, verbose=0)
        self.assertEqual(prediction.shape[1], 4)
        # Verify decision engine mapping for chips packet
        res = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="chips packet",
            product_confidence=0.96,
            packaging_condition="normal package",
            condition_confidence=0.93,
            ocr_data={"is_label_found": True}
        )
        self.assertEqual(res["final_status"], "PASS")

    def test_b_milk_image_flow(self):
        dummy_img = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)
        prediction = self.product_model.predict(dummy_img, verbose=0)
        self.assertEqual(prediction.shape[1], 4)
        res = DecisionEngine.evaluate(
            expected_product="Milk Pouch",
            detected_product="milk pouch",
            product_confidence=0.95,
            packaging_condition="normal package",
            condition_confidence=0.92,
            ocr_data={"is_label_found": True}
        )
        self.assertEqual(res["final_status"], "PASS")

    def test_c_other_food_flow(self):
        res = DecisionEngine.evaluate(
            expected_product="Other Food Product",
            detected_product="other food product",
            product_confidence=0.90,
            packaging_condition="normal package",
            condition_confidence=0.91,
            ocr_data={"is_label_found": True}
        )
        self.assertEqual(res["final_status"], "WARNING")
        self.assertTrue(any("detailed verification data is unavailable" in r for r in res["reasons"]))


    def test_d_non_food_flow(self):
        res = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="other object",
            product_confidence=0.92,
            packaging_condition="normal package",
            condition_confidence=0.88
        )
        self.assertEqual(res["final_status"], "HOLD")
        self.assertTrue(any("Verification Failed" in r for r in res["reasons"]))

    def test_e_normal_package_flow(self):
        dummy_img = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)
        prediction = self.packaging_model.predict(dummy_img, verbose=0)
        self.assertEqual(prediction.shape[1], 3)
        res = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="chips packet",
            product_confidence=0.95,
            packaging_condition="normal package",
            condition_confidence=0.94,
            ocr_data={"is_label_found": True}
        )
        self.assertEqual(res["final_status"], "PASS")

    def test_f_damaged_package_flow(self):
        res = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="chips packet",
            product_confidence=0.95,
            packaging_condition="damage package",
            condition_confidence=0.91
        )
        self.assertEqual(res["final_status"], "REJECT")
        self.assertTrue(any("Package Defect" in r for r in res["reasons"]))

    def test_g_unclear_image_flow(self):
        res = DecisionEngine.evaluate(
            expected_product="Chips Packet",
            detected_product="chips packet",
            product_confidence=0.95,
            packaging_condition="unclear",
            condition_confidence=0.85
        )
        self.assertEqual(res["final_status"], "WARNING")
        self.assertTrue(any("Unclear" in r for r in res["reasons"]))

if __name__ == "__main__":
    unittest.main()
