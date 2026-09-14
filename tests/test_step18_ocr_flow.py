import unittest
import io
from PIL import Image
from fastapi.testclient import TestClient

try:
    from backend.main import app
except ImportError:
    from main import app


def create_test_image_bytes():
    img = Image.new('RGB', (400, 300), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()


class TestStep18OCRFlow(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_01_upload_file_retained_and_ocr_success(self):
        img_bytes = create_test_image_bytes()
        files = {"image": ("back_label.jpg", img_bytes, "image/jpeg")}
        data = {"expected_product": "Chips Packet", "ai_detected_product": "Chips Packet"}
        response = self.client.post("/api/inspect/ocr", files=files, data=data)
        self.assertEqual(response.status_code, 200)
        json_resp = response.json()
        self.assertIn("ocr_status", json_resp)
        self.assertIn("fields", json_resp)

    def test_02_camera_blob_retained_and_ocr_success(self):
        img_bytes = create_test_image_bytes()
        files = {"file": ("camera_capture.jpg", img_bytes, "image/jpeg")}
        data = {"expected_product": "Chips Packet", "ai_detected_product": "Chips Packet"}
        response = self.client.post("/api/inspect/ocr", files=files, data=data)
        self.assertEqual(response.status_code, 200)
        json_resp = response.json()
        self.assertIn("ocr_status", json_resp)

    def test_03_missing_image_returns_400(self):
        response = self.client.post("/api/inspect/ocr", data={"expected_product": "Chips Packet"})
        self.assertEqual(response.status_code, 400)
        json_resp = response.json()
        self.assertEqual(json_resp.get("status"), "error")
        self.assertEqual(json_resp.get("error_type"), "missing_image")
        self.assertIn("No label image was received", json_resp.get("message", ""))

    def test_04_empty_file_handling(self):
        files = {"image": ("empty.jpg", b"", "image/jpeg")}
        response = self.client.post("/api/inspect/ocr", files=files)
        self.assertEqual(response.status_code, 200)
        json_resp = response.json()
        self.assertIn("ocr_status", json_resp)

    def test_05_milk_back_image(self):
        img_bytes = create_test_image_bytes()
        files = {"image": ("milk_back.jpg", img_bytes, "image/jpeg")}
        data = {"expected_product": "Milk Pouch", "ai_detected_product": "Milk Pouch"}
        response = self.client.post("/api/inspect/ocr", files=files, data=data)
        self.assertEqual(response.status_code, 200)
        json_resp = response.json()
        self.assertEqual(json_resp.get("source"), "OCR From Package")

    def test_06_response_json_structure(self):
        img_bytes = create_test_image_bytes()
        files = {"image": ("label.jpg", img_bytes, "image/jpeg")}
        response = self.client.post("/api/inspect/ocr", files=files)
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertIn("nutrition_status", res_data)
        self.assertIn("date_status", res_data)
        self.assertIn("batch_status", res_data)
        self.assertIn("net_quantity_status", res_data)
        self.assertIn("nutrition_data", res_data)
        self.assertIn("debug_info", res_data)


if __name__ == '__main__':
    unittest.main()
