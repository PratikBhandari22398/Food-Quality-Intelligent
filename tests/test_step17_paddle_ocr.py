import unittest
import io
from PIL import Image, ImageDraw, ImageFont
import numpy as np

try:
    from backend.services.paddle_ocr_service import PaddleOCRService
except ImportError:
    from services.paddle_ocr_service import PaddleOCRService


def create_mock_label_image(text_lines):
    img = Image.new('RGB', (800, 600), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    y = 20
    for line in text_lines:
        draw.text((30, y), line, fill=(0, 0, 0), font=font)
        y += 35

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


class TestStep17PaddleOCR(unittest.TestCase):

    def test_01_clear_chips_label(self):
        sample_text = """
        LAYS POTATO CHIPS
        BATCH NO: BATCH-CHIPS-101
        MFD & USE BY: 15/06/26 & 15/12/26
        NET QTY: 50 g
        NUTRITION FACTS PER 100 G:
        Energy 535 kcal
        Protein 7.0 g
        Carbohydrate 52.0 g
        Total Fat 33.0 g
        Sodium 550 mg
        """
        parsed = PaddleOCRService.parse_extracted_content([], sample_text)
        self.assertEqual(parsed["status"], "success")
        self.assertIn(parsed["ocr_status"], ["complete", "partial_success"])
        self.assertEqual(parsed["nutrition_status"], "detected")
        self.assertEqual(parsed["fields"]["batch_number"]["value"], "BATCH-CHIPS-101")
        self.assertEqual(parsed["fields"]["mfg_date"]["value"], "2026-06-15")
        self.assertEqual(parsed["fields"]["use_by_date"]["value"], "2026-12-15")
        self.assertEqual(parsed["fields"]["net_weight"]["value"], "50 g")
        self.assertIn("energy", parsed["nutrition_table"])

    def test_02_current_failing_real_package_image(self):
        real_package_text = """
        REAL CHIPS PACK
        MFD & USE BY: 20/07/26 & 02/12/26
        NET QTY: 30.5 g
        NUTRITIONAL INFORMATION PER 100 g:
        Energy 525 kcal
        Protein 6.4 g
        Carbohydrate 53.1 g
        Total Sugars 5.6 g
        Added Sugars 4.7 g
        Total Fat 31.9 g
        Trans Fat 0.1 g
        Sodium 659 mg
        """
        parsed = PaddleOCRService.parse_extracted_content([], real_package_text)
        self.assertIn(parsed["ocr_status"], ["complete", "partial_success"])
        self.assertEqual(parsed["nutrition_status"], "detected")
        self.assertEqual(parsed["date_status"], "detected")
        self.assertEqual(parsed["net_quantity_status"], "detected")
        self.assertEqual(parsed["fields"]["mfg_date"]["value"], "2026-07-20")
        self.assertEqual(parsed["fields"]["use_by_date"]["value"], "2026-12-02")
        self.assertEqual(parsed["fields"]["net_weight"]["value"], "30.5 g")
        self.assertEqual(parsed["nutrition_table"]["energy"], "525 kcal")
        self.assertEqual(parsed["nutrition_table"]["protein"], "6.4 g")
        self.assertEqual(parsed["nutrition_table"]["sodium"], "659 mg")

    def test_03_nutrition_only_image(self):
        text = """
        NUTRITION VALUES PER 100 G:
        Energy 450 kcal
        Protein 12.0 g
        Fat 18.0 g
        """
        parsed = PaddleOCRService.parse_extracted_content([], text)
        self.assertEqual(parsed["nutrition_status"], "detected")
        self.assertEqual(parsed["ocr_status"], "partial_success")

    def test_04_milk_nutrition_label(self):
        text = """
        AMUL TONED MILK
        BATCH NO: B-MILK-88
        BEST BEFORE: 30/11/2026
        NET QUANTITY: 500 ml
        NUTRITION PER 100 ML:
        Energy 62 kcal
        Protein 3.2 g
        Total Fat 3.5 g
        Calcium 120 mg
        """
        parsed = PaddleOCRService.parse_extracted_content([], text)
        self.assertEqual(parsed["nutrition_status"], "detected")
        self.assertEqual(parsed["fields"]["net_weight"]["value"], "500 ml")
        self.assertEqual(parsed["fields"]["best_before"]["value"], "2026-11-30")
        self.assertEqual(parsed["nutrition_basis"], "Per 100 ml")

    def test_05_mfd_plus_use_by_two_dates(self):
        text = "MFD & USE BY: 10/01/26 & 10/07/26"
        parsed = PaddleOCRService.parse_extracted_content([], text)
        self.assertEqual(parsed["fields"]["mfg_date"]["value"], "2026-01-10")
        self.assertEqual(parsed["fields"]["use_by_date"]["value"], "2026-07-10")

    def test_06_net_quantity(self):
        text = "NET WEIGHT: 250 g"
        parsed = PaddleOCRService.parse_extracted_content([], text)
        self.assertEqual(parsed["fields"]["net_weight"]["value"], "250 g")
        self.assertEqual(parsed["net_quantity_status"], "detected")

    def test_07_missing_batch(self):
        text = """
        NUTRITION FACTS: Energy 500 kcal, Protein 5 g
        BEST BEFORE 12/12/2026
        NET QTY: 100 g
        """
        parsed = PaddleOCRService.parse_extracted_content([], text)
        self.assertEqual(parsed["batch_status"], "not_detected")
        self.assertEqual(parsed["ocr_status"], "partial_success")
        self.assertNotEqual(parsed["ocr_status"], "unclear")

    def test_08_unreadable_label(self):
        parsed = PaddleOCRService.parse_extracted_content([], "   \n  ")
        self.assertEqual(parsed["ocr_status"], "unclear")
        self.assertFalse(parsed["is_label_found"])

    def test_09_invalid_image(self):
        res = PaddleOCRService.process_image(b"")
        self.assertEqual(res["ocr_status"], "failed")
        self.assertTrue(res["system_error"])

    def test_10_backend_unavailable(self):
        # Frontend logic check: backend error produces system_error flag
        err_res = PaddleOCRService._build_error_response("Connection refused", "failed")
        self.assertTrue(err_res["system_error"])
        self.assertEqual(err_res["ocr_status"], "failed")

    def test_11_ocr_engine_failure_fallback(self):
        # Ensures build_unclear_response handles empty fallback gracefully
        res = PaddleOCRService._build_unclear_response("EasyOCR (Fallback)", 150)
        self.assertEqual(res["ocr_status"], "unclear")
        self.assertEqual(res["engine"], "EasyOCR (Fallback)")

    def test_12_nutrition_value_extraction_rda_filter(self):
        # Spatial text lines with RDA percentage to be filtered out
        text_lines = [
            {"text": "Energy", "box": [[10, 10], [100, 10], [100, 30], [10, 30]]},
            {"text": "525 kcal", "box": [[120, 10], [200, 10], [200, 30], [120, 30]]},
            {"text": "26%", "box": [[220, 10], [260, 10], [260, 30], [220, 30]]},
            {"text": "Sodium", "box": [[10, 40], [100, 40], [100, 60], [10, 60]]},
            {"text": "659 mg", "box": [[120, 40], [200, 40], [200, 60], [120, 60]]},
            {"text": "33%", "box": [[220, 40], [260, 40], [260, 60], [220, 60]]},
        ]
        full_text = "Energy 525 kcal 26%\nSodium 659 mg 33%"
        table, basis = PaddleOCRService.extract_nutrition_table(text_lines, full_text)
        self.assertEqual(table.get("energy"), "525 kcal")
        self.assertEqual(table.get("sodium"), "659 mg")
        self.assertNotIn("26%", table.values())


if __name__ == '__main__':
    unittest.main()
