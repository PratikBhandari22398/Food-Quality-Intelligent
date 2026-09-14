import re
import io
import time
import datetime
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np

try:
    from paddleocr import PaddleOCR
except Exception:
    PaddleOCR = None

try:
    import easyocr
    easyocr_reader = easyocr.Reader(['en'], gpu=False)
except Exception:
    easyocr_reader = None

try:
    import pytesseract
except Exception:
    pytesseract = None

try:
    import cv2
except Exception:
    cv2 = None

_PADDLE_INSTANCE = None

def get_paddle_ocr_instance():
    global _PADDLE_INSTANCE
    if _PADDLE_INSTANCE is None and PaddleOCR is not None:
        try:
            # Initialize local CPU PaddleOCR instance
            try:
                _PADDLE_INSTANCE = PaddleOCR(use_angle_cls=True, lang='en')
            except Exception:
                _PADDLE_INSTANCE = PaddleOCR(lang='en')
        except Exception as e:
            print(f"[DEBUG PADDLEOCR INIT ERROR]: {e}")
            _PADDLE_INSTANCE = None
    return _PADDLE_INSTANCE


class PaddleOCRPreprocessor:
    @staticmethod
    def generate_variants(image_bytes: bytes) -> dict:
        """
        Generates 5 image variants for OCR:
        1. original
        2. grayscale
        3. upscaled
        4. contrast_enhanced
        5. adaptive_threshold
        """
        variants = {}
        if not image_bytes:
            return variants

        try:
            pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            variants["original"] = pil_img

            # Grayscale
            gray = pil_img.convert("L")
            variants["grayscale"] = gray

            # Upscaled (2x resize using LANCZOS)
            w, h = pil_img.size
            upscaled = pil_img.resize((w * 2, h * 2), Image.Resampling.LANCZOS)
            variants["upscaled"] = upscaled

            # Contrast enhanced
            enh_contrast = ImageEnhance.Contrast(gray).enhance(2.2)
            variants["contrast_enhanced"] = enh_contrast

            # Adaptive threshold
            if cv2 is not None:
                np_gray = np.array(gray)
                blurred = cv2.bilateralFilter(np_gray, 9, 75, 75)
                adaptive_thresh = cv2.adaptiveThreshold(
                    blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY, 11, 2
                )
                variants["adaptive_threshold"] = Image.fromarray(adaptive_thresh)
        except Exception as e:
            print(f"[DEBUG PADDLEOCR PREPROC NOTICE]: {e}")

        return variants if variants else {"original": None}


class PaddleOCRService:
    @staticmethod
    def process_image(image_bytes: bytes) -> dict:
        """
        Processes raw image bytes using local PaddleOCR.
        Falls back to EasyOCR if PaddleOCR is unavailable or returns no text.
        """
        start_time = time.time()
        if not image_bytes or len(image_bytes) == 0:
            return PaddleOCRService._build_error_response("Empty image payload provided.", "failed")

        variants = PaddleOCRPreprocessor.generate_variants(image_bytes)
        
        # Primary OCR run using PaddleOCR
        paddle_ocr = get_paddle_ocr_instance()
        text_lines = []
        full_text_parts = []
        engine_used = "PaddleOCR"
        variant_used = "contrast_enhanced"

        if paddle_ocr is not None:
            target_img = variants.get("contrast_enhanced") or variants.get("original")
            try:
                np_img = np.array(target_img)
                try:
                    ocr_res = paddle_ocr.ocr(np_img)
                except Exception as ex:
                    print(f"[DEBUG PADDLEOCR CALL EXCEPTION]: {ex}")
                    ocr_res = None

                if ocr_res and isinstance(ocr_res, list) and len(ocr_res) > 0 and ocr_res[0]:
                    items = ocr_res[0] if isinstance(ocr_res[0], list) else ocr_res
                    for line in items:
                        if isinstance(line, (list, tuple)) and len(line) >= 2:
                            box = line[0]
                            val_pair = line[1]
                            if isinstance(val_pair, (list, tuple)) and len(val_pair) >= 2:
                                txt, conf = val_pair[0], val_pair[1]
                                text_lines.append({
                                    "text": txt,
                                    "confidence": float(conf),
                                    "box": box
                                })
                                full_text_parts.append(txt)
            except Exception as e:
                print(f"[DEBUG PADDLEOCR RUN ERROR]: {e}")

        # Fallback to EasyOCR if PaddleOCR yielded no text lines
        if not text_lines and easyocr_reader is not None:
            engine_used = "EasyOCR (Fallback)"
            target_img = variants.get("original")
            try:
                np_img = np.array(target_img)
                easy_res = easyocr_reader.readtext(np_img)
                for item in easy_res:
                    box = [[float(p[0]), float(p[1])] for p in item[0]]
                    txt = item[1]
                    conf = float(item[2])
                    text_lines.append({
                        "text": txt,
                        "confidence": conf,
                        "box": box
                    })
                    full_text_parts.append(txt)
            except Exception as e:
                print(f"[DEBUG EASYOCR FALLBACK ERROR]: {e}")

        # PyTesseract secondary fallback if still empty
        if not text_lines and pytesseract is not None:
            engine_used = "PyTesseract (Fallback)"
            try:
                target_img = variants.get("original")
                txt = pytesseract.image_to_string(target_img)
                if txt.strip():
                    for line in txt.splitlines():
                        if line.strip():
                            text_lines.append({
                                "text": line.strip(),
                                "confidence": 0.85,
                                "box": []
                            })
                            full_text_parts.append(line.strip())
            except Exception as e:
                print(f"[DEBUG PYTESSERACT FALLBACK ERROR]: {e}")

        full_text = "\n".join(full_text_parts)
        processing_time_ms = int((time.time() - start_time) * 1000)

        if not full_text.strip():
            return PaddleOCRService._build_unclear_response(engine_used, processing_time_ms)

        # Spatial nutrition table and field parsing
        parsed = PaddleOCRService.parse_extracted_content(text_lines, full_text)
        
        parsed["engine"] = engine_used
        parsed["text_lines"] = text_lines
        parsed["full_text"] = full_text
        parsed["processing_time_ms"] = processing_time_ms
        parsed["debug_info"] = {
            "ocr_engine": engine_used,
            "preproc_variant": variant_used,
            "raw_text": full_text,
            "normalized_text": parsed.get("normalized_text", full_text.upper()),
            "processing_time_ms": processing_time_ms,
            "detected_line_count": len(text_lines)
        }

        return parsed

    @staticmethod
    def parse_extracted_content(text_lines: list, full_text: str) -> dict:
        """
        Extracts structured fields using bounding box spatial analysis and regular expressions.
        """
        if not full_text or not full_text.strip():
            return PaddleOCRService._build_unclear_response("PaddleOCR", 0)

        normalized_text = full_text.upper()
        
        # 1. Date Extraction (Dual-date + Single-date formats)
        mfg_date = None
        use_by_date = None
        best_before_date = None
        
        # Dual date pattern e.g. MFD & USE BY: 20/07/26 & 02/12/26 or 20/07/2026 & 02/12/2026
        dual_date_match = re.search(
            r'(?:MFD|MFG|MANUFACTURED)?\s*[\&\+AND]*\s*(?:USE\s*BY|EXP|EXPIRY|BEST\s*BEFORE)[\s:]*(\d{1,2}[\/\.-]\d{1,2}[\/\.-]\d{2,4})\s*[\&\+\,\s]+\s*(\d{1,2}[\/\.-]\d{1,2}[\/\.-]\d{2,4})',
            normalized_text
        )
        if dual_date_match:
            d1_raw, d2_raw = dual_date_match.group(1), dual_date_match.group(2)
            mfg_date = PaddleOCRService.normalize_date(d1_raw)
            use_by_date = PaddleOCRService.normalize_date(d2_raw)

        # Explicit Use By / Expiry search if dual date didn't capture it
        if not use_by_date:
            exp_match = re.search(
                r'(?:USE\s*BY|EXPIRY|EXP|USE-BY)[\s:]*(\d{1,2}[\/\.-]\d{1,2}[\/\.-]\d{2,4})',
                normalized_text
            )
            if exp_match:
                use_by_date = PaddleOCRService.normalize_date(exp_match.group(1))

        # Explicit Best Before search
        if not best_before_date:
            bb_match = re.search(
                r'(?:BEST\s*BEFORE|BEST-BEFORE)[\s:]*(\d{1,2}[\/\.-]\d{1,2}[\/\.-]\d{2,4})',
                normalized_text
            )
            if bb_match:
                best_before_date = PaddleOCRService.normalize_date(bb_match.group(1))

        # Explicit Manufacturing date search if not captured
        if not mfg_date:
            mfd_match = re.search(
                r'(?:MFD|MFG|MANUFACTURED|MFD\s*DATE)[\s:]*(\d{1,2}[\/\.-]\d{1,2}[\/\.-]\d{2,4})',
                normalized_text
            )
            if mfd_match:
                mfg_date = PaddleOCRService.normalize_date(mfd_match.group(1))

        # Fallback date search if dates still missing
        if not use_by_date and not best_before_date:
            generic_dates = re.findall(r'\b(\d{1,2}[\/\.-]\d{1,2}[\/\.-]\d{2,4})\b', normalized_text)
            if len(generic_dates) >= 2 and not mfg_date:
                mfg_date = PaddleOCRService.normalize_date(generic_dates[0])
                use_by_date = PaddleOCRService.normalize_date(generic_dates[1])
            elif len(generic_dates) == 1:
                use_by_date = PaddleOCRService.normalize_date(generic_dates[0])

        effective_expiry_date = use_by_date or best_before_date

        # 2. Batch Number Extraction
        batch_number = None
        batch_match = re.search(
            r'(?:BATCH\s*NO\.?|BATCH\s*NUMBER|BATCH\s*NUM|B\.\s*NO\.?|B\.NO\.?|LOT\s*NO\.?|LOT|BATCH)[\s:\-]+([A-Z0-9\-\/]{3,25})',
            normalized_text
        )
        if batch_match:
            candidate = batch_match.group(1).strip()
            candidate = re.sub(r'^(?:NO\.?|NUM\.?|NUMBER|[:\s]+)', '', candidate)
            if candidate and candidate not in ["AND", "USE", "BY", "FOR", "NET", "QTY"]:
                batch_number = candidate

        # 3. Net Quantity Extraction
        net_quantity = None
        net_match = re.search(
            r'(?:NET\s*QTY|NET\s*QUANTITY|NET\s*WT|NET\s*WEIGHT)[\s:]*([\d\.]+\s*(?:g|mg|kg|ml|l))\b',
            full_text, re.IGNORECASE
        )
        if not net_match:
            net_match = re.search(r'\b([\d\.]+\s*(?:g|mg|kg|ml|l))\b', full_text, re.IGNORECASE)
        
        if net_match:
            val = net_match.group(1).strip()
            # Normalize units to lowercase (e.g. "30.5 g", "500 ml")
            net_quantity = re.sub(r'([A-Za-z]+)', lambda m: m.group(1).lower(), val)

        # 4. Product Name Extraction
        product_name = None
        prod_match = re.search(
            r'(?:PRODUCT\s*NAME|PRODUCT|BRAND)[\s:]*([A-Z0-9\s]{3,30})',
            normalized_text
        )
        if prod_match:
            product_name = prod_match.group(1).strip()

        # 5. Spatial Row & Regex Nutrition Table Extraction
        nutrition_table, nutrition_basis = PaddleOCRService.extract_nutrition_table(text_lines, full_text)

        # Field Status Evaluation
        date_status = "detected" if (mfg_date or effective_expiry_date) else "not_detected"
        batch_status = "detected" if batch_number else "not_detected"
        net_quantity_status = "detected" if net_quantity else "not_detected"
        nutrition_status = "detected" if (nutrition_table and len(nutrition_table) > 0) else "not_detected"

        # Overall OCR Status Determination
        if nutrition_status == "detected" and date_status == "detected" and batch_status == "detected" and net_quantity_status == "detected":
            ocr_status = "complete"
        elif nutrition_status == "detected" or date_status == "detected" or batch_status == "detected" or net_quantity_status == "detected":
            ocr_status = "partial_success"
        else:
            ocr_status = "unclear"

        display_map = {
            "complete": "✅ COMPLETE",
            "partial_success": "🟡 PARTIAL SUCCESS",
            "unclear": "⚠️ UNCLEAR",
            "failed": "❌ FAILED"
        }

        return {
            "status": "success",
            "ocr_status": ocr_status,
            "ocr_status_display": display_map.get(ocr_status, "⚠️ UNCLEAR"),
            "nutrition_status": nutrition_status,
            "date_status": date_status,
            "batch_status": batch_status,
            "net_quantity_status": net_quantity_status,
            "is_label_found": True,
            "product_name": product_name,
            "fields": {
                "product_name": {"value": product_name, "status": "detected" if product_name else "not_detected"},
                "batch_number": {"value": batch_number, "status": batch_status},
                "mfg_date": {"value": mfg_date, "status": "detected" if mfg_date else "not_detected"},
                "use_by_date": {"value": use_by_date, "status": "detected" if use_by_date else "not_detected"},
                "best_before": {"value": effective_expiry_date, "status": "detected" if effective_expiry_date else "not_detected"},
                "net_weight": {"value": net_quantity, "status": net_quantity_status}
            },
            "nutrition_table": nutrition_table,
            "nutrition_data": nutrition_table,
            "nutrition_basis": nutrition_basis,
            "system_error": False
        }

    @staticmethod
    def extract_nutrition_table(text_lines: list, full_text: str) -> tuple:
        """
        Parses nutrition table using bounding-box spatial row alignment and text regular expressions.
        Ignores RDA percentage values (%RDA) and retains exact nutrient values and units in lowercase.
        """
        table = {}
        basis = "Per 100 g"

        # Basis detection
        upper_text = full_text.upper()
        if "PER 100 ML" in upper_text:
            basis = "Per 100 ml"
        elif "PER 100 G" in upper_text or "PER 100G" in upper_text:
            basis = "Per 100 g"
        elif "PER SERVING" in upper_text:
            basis = "Per Serving"
        elif "SINGLE PACK" in upper_text:
            basis = "Single Pack"

        # Standard nutrient definitions
        nutrient_definitions = [
            ("energy", r'ENERGY|CALORIES'),
            ("protein", r'PROTEIN'),
            ("carbohydrates", r'TOTAL\s*CARBOHYDRATE|CARBOHYDRATE|CARBS'),
            ("total_sugars", r'TOTAL\s*SUGARS|TOTAL\s*SUGAR|SUGARS'),
            ("added_sugars", r'ADDED\s*SUGARS|ADDED\s*SUGAR'),
            ("total_fat", r'TOTAL\s*FAT|FAT'),
            ("saturated_fat", r'SATURATED\s*FAT|SAT\s*FAT'),
            ("trans_fat", r'TRANS\s*FAT'),
            ("sodium", r'SODIUM'),
            ("fibre", r'DIETARY\s*FIBRE|FIBRE|FIBER'),
            ("calcium", r'CALCIUM')
        ]

        def normalize_unit(val: str, default_unit: str = "g") -> str:
            val_clean = val.strip()
            # Normalize units to lowercase
            val_clean = re.sub(r'([A-Za-z]+)', lambda m: m.group(1).lower(), val_clean)
            if not re.search(r'[a-z]', val_clean):
                val_clean += f" {default_unit}"
            return val_clean

        # Method 1: Bounding-box spatial row grouping (if box coordinates are present)
        if text_lines and any(l.get("box") for l in text_lines):
            rows = []
            for item in text_lines:
                box = item.get("box", [])
                if len(box) >= 4:
                    y_center = sum([p[1] for p in box]) / len(box)
                    x_center = sum([p[0] for p in box]) / len(box)
                    matched_row = None
                    for row in rows:
                        if abs(row["y_center"] - y_center) < 18:
                            matched_row = row
                            break
                    if matched_row:
                        matched_row["items"].append((x_center, item["text"]))
                    else:
                        rows.append({"y_center": y_center, "items": [(x_center, item["text"])]})

            for row in rows:
                row["items"].sort(key=lambda x: x[0])
                row_text = " ".join([it[1] for it in row["items"]]).upper()

                for key, pat in nutrient_definitions:
                    if key in table:
                        continue
                    if re.search(pat, row_text):
                        val_match = re.search(r'([\d\.]+\s*(?:kcal|g|mg|ml))\b(?!\s*%)', row_text, re.IGNORECASE)
                        if not val_match:
                            val_match = re.search(r'\b([\d\.]+)\b(?!\s*%)', row_text)
                        if val_match:
                            default_unit = "kcal" if key == "energy" else ("mg" if key == "sodium" else "g")
                            table[key] = normalize_unit(val_match.group(1), default_unit)

        # Method 2: Regex fallback over full text for any missing nutrients
        for key, pat in nutrient_definitions:
            if key in table:
                continue
            match = re.search(
                rf'(?:{pat})[\s\|:\#_\-]*([\d\.]+\s*(?:kcal|g|mg|ml)?)\b(?!\s*%)',
                upper_text
            )
            if match:
                default_unit = "kcal" if key == "energy" else ("mg" if key == "sodium" else "g")
                table[key] = normalize_unit(match.group(1), default_unit)

        return table, basis

    @staticmethod
    def normalize_date(date_str: str) -> str:
        """
        Normalizes DD/MM/YY, DD-MM-YYYY, etc. to ISO standard YYYY-MM-DD.
        """
        if not date_str:
            return None
        cleaned = date_str.replace('.', '/').replace('-', '/').strip()
        parts = cleaned.split('/')
        if len(parts) == 3:
            day, month, year = parts[0].zfill(2), parts[1].zfill(2), parts[2]
            if len(year) == 2:
                year = "20" + year
            try:
                dt = datetime.date(int(year), int(month), int(day))
                return dt.strftime("%Y-%m-%d")
            except Exception:
                return cleaned
        return cleaned

    @staticmethod
    def _build_error_response(msg: str, status_code: str = "failed") -> dict:
        return {
            "status": "error",
            "ocr_status": status_code,
            "nutrition_status": "not_detected",
            "date_status": "not_detected",
            "batch_status": "not_detected",
            "net_quantity_status": "not_detected",
            "is_label_found": False,
            "fields": {},
            "nutrition_table": {},
            "system_error": True,
            "message": msg
        }

    @staticmethod
    def _build_unclear_response(engine_used: str, processing_time_ms: int) -> dict:
        return {
            "status": "success",
            "ocr_status": "unclear",
            "nutrition_status": "not_detected",
            "date_status": "not_detected",
            "batch_status": "not_detected",
            "net_quantity_status": "not_detected",
            "is_label_found": False,
            "fields": {
                "product_name": {"value": None, "status": "not_detected"},
                "batch_number": {"value": None, "status": "not_detected"},
                "best_before": {"value": None, "status": "not_detected"},
                "net_weight": {"value": None, "status": "not_detected"}
            },
            "nutrition_table": {},
            "system_error": False,
            "engine": engine_used,
            "text_lines": [],
            "full_text": "",
            "processing_time_ms": processing_time_ms,
            "debug_info": {
                "ocr_engine": engine_used,
                "raw_text": "",
                "normalized_text": "",
                "processing_time_ms": processing_time_ms
            }
        }
