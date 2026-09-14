import unittest
from fastapi.testclient import TestClient
from backend.main import app
from backend.db.database import init_db

class TestAPIEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def test_products_endpoint(self):
        response = self.client.get("/api/products")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    def test_batches_endpoint(self):
        response = self.client.get("/api/batches")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_dashboard_summary_endpoint(self):
        response = self.client.get("/api/dashboard/summary")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_inspections", data)
        self.assertIn("pass_count", data)

    def test_inspection_evaluate_endpoint(self):
        payload = {
            "expected_product": "Chips Packet",
            "detected_product": "Chips Packet",
            "product_confidence": 0.95,
            "packaging_condition": "Normal Package",
            "condition_confidence": 0.96,
            "ocr_data": {"is_label_found": True}
        }
        response = self.client.post("/api/inspect/evaluate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["final_status"], "PASS")

    def test_ocr_endpoint_upload_success(self):
        # Simulated 1x1 GIF image byte stream
        img_bytes = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        response = self.client.post(
            "/api/inspect/ocr",
            files={"file": ("test_label.gif", img_bytes, "image/gif")},
            data={"expected_product": "Chips Packet", "ai_detected_product": "Chips Packet"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("ocr_result", data)
        self.assertIn("ocr_vs_database", data)
        self.assertIn("consistency_check", data)

    def test_ocr_endpoint_empty_file_unreadable(self):
        response = self.client.post(
            "/api/inspect/ocr",
            files={"file": ("empty.jpg", b"", "image/jpeg")},
            data={"expected_product": "Chips Packet", "ai_detected_product": "Chips Packet"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["ocr_result"]["is_label_found"])
        self.assertEqual(data["ocr_result"]["batch_number"], "Not Clearly Read")

    def test_ocr_endpoint_with_image_field(self):
        img_bytes = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        response = self.client.post(
            "/api/inspect/ocr",
            files={"image": ("test_label.gif", img_bytes, "image/gif")},
            data={"expected_product": "Chips Packet", "ai_detected_product": "Chips Packet"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("ocr_result", data)

    def test_inspections_alias_endpoint(self):
        response = self.client.get("/api/inspections")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_alerts_alias_endpoint(self):
        response = self.client.get("/api/alerts")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_product_nutrition_endpoint(self):
        response = self.client.get("/api/products/CHIP001/nutrition")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("nutrition", data)

        response_milk = self.client.get("/api/products/MILK001/nutrition")
        self.assertEqual(response_milk.status_code, 200)
        data_milk = response_milk.json()
        self.assertIn("nutrition", data_milk)

if __name__ == "__main__":
    unittest.main()

