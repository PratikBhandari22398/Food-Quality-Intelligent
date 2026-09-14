import unittest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.ocr_service import OCRService, OCRPreprocessor
from backend.services.decision_engine import DecisionEngine

class TestStep16OCRWrinkledPackage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_1_clear_nutrition_table(self):
        sample_text = """
        NUTRITION INFORMATION
        Per 100 g
        Energy: 525 kcal
        Protein: 6.4 g
        Carbohydrate: 53.1 g
        Total Sugars: 5.6 g
        Added Sugars: 4.7 g
        Total Fat: 31.9 g
        Sodium: 659 mg
        """
        res = OCRService.parse_extracted_text(sample_text)
        self.assertEqual(res["nutrition_status"], "detected")
        self.assertEqual(res["nutrition_data"]["energy_kcal"], 525.0)
        self.assertEqual(res["nutrition_data"]["protein_g"], 6.4)
        self.assertEqual(res["nutrition_data"]["total_sugars_g"], 5.6)
        self.assertEqual(res["nutrition_data"]["added_sugars_g"], 4.7)

    def test_2_mfd_and_use_by_two_date_format(self):
        sample_text = """
        MFD & USE BY:
        20/07/26 & 02/12/26
        """
        res = OCRService.parse_extracted_text(sample_text)
        self.assertEqual(res["mfg_date"], "2026-07-20")
        self.assertEqual(res["use_by_date"], "2026-12-02")
        self.assertEqual(res["exp_date"], "2026-12-02")
        self.assertEqual(res["date_status"], "detected")

    def test_3_net_quantity_parsing(self):
        sample_text = """
        NET QUANTITY: 30.5 g
        """
        res = OCRService.parse_extracted_text(sample_text)
        self.assertEqual(res["net_weight"], "30.5 g")
        self.assertEqual(res["net_quantity_status"], "detected")

    def test_4_nutrition_plus_missing_batch(self):
        sample_text = """
        NUTRITION INFORMATION: Energy 525 kcal, Protein 6.4 g
        USE BY 02/12/2026
        """
        res = OCRService.parse_extracted_text(sample_text)
        self.assertIn(res["ocr_status"], ["nutrition_detected", "partial_success", "complete"])
        self.assertEqual(res["batch_status"], "not_detected")
        self.assertEqual(res["nutrition_status"], "detected")

    def test_5_nutrition_plus_missing_date(self):
        sample_text = """
        BATCH NO: BATCH-CHIPS-101
        NUTRITION INFORMATION: Energy 525 kcal, Protein 6.4 g
        """
        res = OCRService.parse_extracted_text(sample_text)
        self.assertIn(res["ocr_status"], ["nutrition_detected", "partial_success", "complete"])
        self.assertEqual(res["date_status"], "not_detected")
        self.assertEqual(res["batch_status"], "detected")

    def test_6_completely_unreadable_image(self):
        res = OCRService.parse_extracted_text("")
        self.assertEqual(res["ocr_status"], "unclear")
        self.assertFalse(res["is_label_found"])

    def test_7_ocr_service_empty_payload(self):
        res = OCRService.process_image(b"")
        self.assertEqual(res["ocr_status"], "failed")
        self.assertTrue(res["system_error"])

    def test_8_backend_alias_endpoints(self):
        response = self.client.get("/api/inspections")
        self.assertEqual(response.status_code, 200)

    def test_9_image_validation_empty_bytes(self):
        response = self.client.post(
            "/api/inspect/ocr",
            files={"file": ("test.txt", b"", "text/plain")},
            data={"expected_product": "Chips Packet"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn(data["ocr_status"], ["unclear", "failed"])

    def test_10_real_uploaded_package_image_full_extraction(self):
        sample_real_image_text = """
        DELICIOUS CRISPY CHIPS
        Net Quantity: 30.5 g
        NUTRITION INFORMATION
        Energy 525 kcal
        Protein 6.4 g
        Carbohydrate 53.1 g
        Total Sugars 5.6 g
        Added Sugars 4.7 g
        Total Fat 31.9 g
        Trans Fat 0.1 g
        Sodium 659 mg
        MFD & USE BY:
        20/07/26 & 02/12/26
        """
        res = OCRService.parse_extracted_text(sample_real_image_text)
        self.assertNotEqual(res["ocr_status"], "unclear")
        self.assertEqual(res["mfg_date"], "2026-07-20")
        self.assertEqual(res["use_by_date"], "2026-12-02")
        self.assertEqual(res["net_weight"], "30.5 g")
        self.assertEqual(res["nutrition_data"]["energy_kcal"], 525.0)
        self.assertEqual(res["nutrition_data"]["sodium_mg"], 659.0)
        self.assertEqual(res["nutrition_status"], "detected")

if __name__ == "__main__":
    unittest.main()
