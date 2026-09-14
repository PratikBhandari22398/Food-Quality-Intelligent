import re
import io
import time
import datetime
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np

try:
    import pytesseract
except Exception:
    pytesseract = None

try:
    import easyocr
    easyocr_reader = easyocr.Reader(['en'], gpu=False)
except Exception:
    easyocr_reader = None

try:
    import cv2
except Exception:
    cv2 = None

try:
    from backend.services.paddle_ocr_service import PaddleOCRService
except ImportError:
    try:
        from services.paddle_ocr_service import PaddleOCRService
    except ImportError:
        PaddleOCRService = None

class OCRPreprocessor:
    @staticmethod
    def generate_variants(image_bytes: bytes) -> dict:
        """
        Generates preprocessed image variants for OCR:
        1. original
        2. grayscale_enhanced
        3. adaptive_threshold
        4. otsu_threshold
        """
        variants = {}
        if not image_bytes:
            return variants

        try:
            pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            pil_img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
            variants["original"] = pil_img

            # Grayscale + Contrast + Sharpening
            gray = pil_img.convert("L")
            enh_contrast = ImageEnhance.Contrast(gray).enhance(2.2)
            enh_sharp = ImageEnhance.Sharpness(enh_contrast).enhance(2.0)
            variants["grayscale_enhanced"] = enh_sharp

            if cv2 is not None:
                np_gray = np.array(gray)
                # Adaptive Thresholding
                blurred = cv2.bilateralFilter(np_gray, 9, 75, 75)
                adaptive_thresh = cv2.adaptiveThreshold(
                    blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                    cv2.THRESH_BINARY, 11, 2
                )
                variants["adaptive_threshold"] = Image.fromarray(adaptive_thresh)

                # Otsu Thresholding
                _, otsu = cv2.threshold(np_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                variants["otsu_threshold"] = Image.fromarray(otsu)

        except Exception as e:
            print(f"[DEBUG OCR PREPROC NOTICE]: {e}")

        return variants if variants else {"original": None}


class OCRService:
    @staticmethod
    def process_image(image_bytes: bytes) -> dict:
        """
        Processes raw image bytes using PaddleOCRService as the primary OCR engine.
        Falls back to legacy PyTesseract/EasyOCR pipeline if needed.
        """
        if PaddleOCRService is not None:
            try:
                res = PaddleOCRService.process_image(image_bytes)
                if res.get("status") == "success" and res.get("ocr_status") in ["complete", "partial_success"]:
                    return res
            except Exception as e:
                print(f"[DEBUG PADDLEOCR SERVICE DELEGATION NOTICE]: {e}")

        start_time = time.time()
        if not image_bytes or len(image_bytes) == 0:
            return OCRService.build_failed_ocr_result("Empty image payload provided.")

        variants = OCRPreprocessor.generate_variants(image_bytes)
        parsed_results = []
        raw_text_runs = []
        engines_used = []

        # Run OCR across preprocessed variants
        for variant_name, img_obj in variants.items():
            if img_obj is None:
                continue

            extracted_text = ""
            confidence = 80.0
            engine_name = "PyTesseract"

            if pytesseract is not None:
                try:
                    extracted_text = pytesseract.image_to_string(img_obj)
                    confidence = 88.0
                    engine_name = "PyTesseract"
                except Exception as e:
                    print(f"[DEBUG OCR PYTESSERACT NOTICE]: {e}")

            if not extracted_text.strip() and easyocr_reader is not None:
                try:
                    np_img = np.array(img_obj)
                    results = easyocr_reader.readtext(np_img, detail=1)
                    texts = [res[1] for res in results]
                    confs = [res[2] for res in results]
                    extracted_text = " ".join(texts)
                    confidence = float(np.mean(confs) * 100) if confs else 80.0
                    engine_name = "EasyOCR"
                except Exception as e:
                    print(f"[DEBUG OCR EASYOCR NOTICE]: {e}")

            if extracted_text.strip():
                print(f"[DEBUG OCR RAW TEXT - Variant '{variant_name}' ({engine_name})]:\n{extracted_text}\n---")
                raw_text_runs.append(f"[{variant_name} / {engine_name}]: {extracted_text.strip()}")
                engines_used.append(engine_name)
                parsed = OCRService.parse_extracted_text(extracted_text, confidence)
                parsed["variant"] = variant_name
                parsed["engine"] = engine_name
                parsed_results.append(parsed)

        # Region-Specific Cropping Pass (Top region for batch/dates vs Bottom region for nutrition)
        if variants.get("original"):
            try:
                orig = variants["original"]
                w, h = orig.size
                # Top 50% region (batch, dates, net weight)
                crop_top = orig.crop((0, 0, w, int(h * 0.55)))
                # Bottom 60% region (nutrition table)
                crop_bottom = orig.crop((0, int(h * 0.40), w, h))

                for region_label, crop_img in [("crop_top", crop_top), ("crop_bottom", crop_bottom)]:
                    reg_text = ""
                    if pytesseract is not None:
                        try:
                            reg_text = pytesseract.image_to_string(crop_img)
                        except Exception:
                            pass
                    if reg_text.strip():
                        parsed_reg = OCRService.parse_extracted_text(reg_text, 85.0)
                        parsed_reg["variant"] = region_label
                        parsed_reg["engine"] = "PyTesseract Region"
                        parsed_results.append(parsed_reg)
                        raw_text_runs.append(f"[{region_label}]: {reg_text.strip()}")
            except Exception as e:
                print(f"[DEBUG OCR REGION CROP NOTICE]: {e}")

        elapsed_ms = round((time.time() - start_time) * 1000, 1)

        if not parsed_results:
            failed_res = OCRService.build_failed_ocr_result("No readable text found across image variants.")
            failed_res["debug_info"] = {
                "engine_used": "None",
                "preprocessing_method": "None",
                "raw_text": "No text extracted.",
                "normalized_text": "",
                "processing_time_ms": elapsed_ms
            }
            return failed_res

        # Merge evidence across all parsed passes to maximize extracted field precision
        merged = OCRService.merge_parsed_evidence(parsed_results, raw_text_runs, elapsed_ms)
        return merged

    @staticmethod
    def build_failed_ocr_result(error_msg: str = "OCR service error") -> dict:
        nutrition_data = {
            "energy_kcal": "Not detected",
            "protein_g": "Not detected",
            "carbohydrate_g": "Not detected",
            "total_sugars_g": "Not detected",
            "added_sugars_g": "Not detected",
            "total_fat_g": "Not detected",
            "saturated_fat_g": "Not detected",
            "trans_fat_g": "Not detected",
            "sodium_mg": "Not detected",
            "fibre_g": "Not detected",
            "calcium_mg": "Not detected",
        }
        fields = {
            "product_name": {"value": None, "status": "not_detected", "confidence": 0.0},
            "batch_number": {"value": None, "status": "not_detected", "confidence": 0.0},
            "best_before": {"value": None, "status": "not_detected", "notice": None, "confidence": 0.0},
            "mfg_date": {"value": None, "status": "not_detected", "confidence": 0.0},
            "use_by_date": {"value": None, "status": "not_detected", "confidence": 0.0},
            "net_weight": {"value": None, "status": "not_detected", "confidence": 0.0},
            "serving_size": {"value": None, "status": "not_detected", "confidence": 0.0}
        }
        return {
            "raw_text": "",
            "ocr_status": "failed",
            "ocr_status_display": "❌ OCR FAILED",
            "nutrition_status": "not_detected",
            "date_status": "not_detected",
            "batch_status": "not_detected",
            "net_quantity_status": "not_detected",
            "product_name": "Not Clearly Read",
            "batch_number": "Not Clearly Read",
            "mfg_date": None,
            "exp_date": None,
            "use_by_date": None,
            "expiry_status": "UNVERIFIED",
            "expiry_status_display": "⚠️ Date Could Not Be Verified",
            "net_weight": "Not detected",
            "serving_size": "Not detected",
            "basis": "per_100g",
            "ocr_confidence": 0.0,
            "is_label_found": False,
            "nutrition_data": nutrition_data,
            "fields": fields,
            "system_error": True,
            "error_detail": error_msg,
            "debug_info": {
                "engine_used": "Failed",
                "preprocessing_method": "None",
                "raw_text": "",
                "normalized_text": "",
                "processing_time_ms": 0.0
            }
        }

    @staticmethod
    def parse_extracted_text(text: str, ocr_confidence: float = 85.0) -> dict:
        text_upper = text.upper()

        # 1. Product Name Extraction
        product_name_match = re.search(r'(?:PRODUCT|ITEM|NAME)\s*[:#]?\s*([A-Z0-9\s\-]{3,30})', text_upper)
        product_name = product_name_match.group(1).strip() if product_name_match else None

        # 2. Batch Code / Number Regex
        batch_match = re.search(r'(?:BATCH\s*CODE|BATCH\s*NO\.?|BATCH\s*#?|B\.?\s*NO\.?|B\.NO\.?|LOT\s*NO\.?|LOT\s*#?)\s*[:#]?\s*([A-Z0-9\-\/]{3,25})', text_upper)
        batch_no = batch_match.group(1).strip() if batch_match else None

        # Helper for date string parsing
        def parse_date_str(d_str: str):
            if not d_str:
                return None, None
            clean = d_str.strip().replace(".", "/").replace("-", "/")
            parts = clean.split("/")
            if len(parts) == 3:
                try:
                    d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
                    if y < 100:
                        y += 2000
                    p_date = datetime.date(y, m, d)
                    return p_date, p_date.strftime("%Y-%m-%d")
                except ValueError:
                    pass
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%Y/%m/%d", "%d.%m.%Y"):
                try:
                    p_date = datetime.datetime.strptime(d_str.strip(), fmt).date()
                    return p_date, p_date.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            return None, d_str.strip()

        # 3. Two-Date Pattern (e.g., MFD & USE BY: 20/07/26 & 02/12/26)
        two_date_match = re.search(
            r'(?:MFD|MFG|PKD|PACKED|MANUFACTURED)\s*(?:&|AND|\/)?\s*(?:USE\s*BY|EXP|EXPIRY|BEST\s*BEFORE)?\s*[:#]?\s*(\d{2}[\/\.-]\d{2}[\/\.-]\d{2,4})\s*(?:&|AND|\/|-|\s+AND\s+)\s*(\d{2}[\/\.-]\d{2}[\/\.-]\d{2,4})',
            text_upper
        )

        mfg_date = None
        use_by_date = None
        exp_date_str = None
        parsed_exp_date = None

        if two_date_match:
            raw_mfg = two_date_match.group(1)
            raw_exp = two_date_match.group(2)
            _, mfg_date = parse_date_str(raw_mfg)
            parsed_exp_date, use_by_date = parse_date_str(raw_exp)
            exp_date_str = use_by_date
        else:
            # Single MFD Regex
            mfg_match = re.search(
                r'(?:MFD|MFG|PKD|PACKED|DATE OF MFG|MANUFACTURED)\s*[:#]?\s*(\d{2}[\/\.-]\d{2}[\/\.-]\d{2,4}|\d{4}[\/\.-]\d{2}[\/\.-]\d{2}|\d{2}\s+[A-Z]{3}\s+\d{2,4})',
                text_upper
            )
            if mfg_match:
                _, mfg_date = parse_date_str(mfg_match.group(1))

            # Single Expiry / Best Before / Use By Regex
            exp_match = re.search(
                r'(?:BEST\s*BEFORE|BEST-BEFORE|USE\s*BY|USE-BY|EXP|EXPIRY|EXP\s*DATE)\s*[:#]?\s*(\d{2}[\/\.-]\d{2}[\/\.-]\d{2,4}|\d{4}[\/\.-]\d{2}[\/\.-]\d{2}|\d{2}\s+[A-Z]{3}\s+\d{2,4})',
                text_upper
            )
            if exp_match:
                parsed_exp_date, exp_date_str = parse_date_str(exp_match.group(1))
                use_by_date = exp_date_str

        # Relative Best-Before Statement Regex
        relative_best_before_match = re.search(
            r'(?:BEST\s*BEFORE|USE\s*BY|EXPIRY)\s+([A-Z0-9\s]+?\s+(?:MONTHS|DAYS|WEEKS|YEARS)\s+(?:FROM|OF)\s+(?:MANUFACTURE|MFG|PACKAGING|PKD|DATE OF MFG))',
            text_upper
        )
        has_relative_statement = bool(relative_best_before_match)

        expiry_status = "UNVERIFIED"
        expiry_status_display = "⚠️ Date Could Not Be Verified"
        best_before_status = "not_detected"
        best_before_notice = None

        if exp_date_str or use_by_date:
            best_before_status = "detected"
            if parsed_exp_date:
                if parsed_exp_date < datetime.date.today():
                    expiry_status = "EXPIRED"
                    expiry_status_display = "❌ Best-Before Verification Failed"
                else:
                    expiry_status = "VALID"
                    expiry_status_display = "✅ Date Valid / Within Date"
            else:
                expiry_status = "VALID"
                expiry_status_display = "✅ Date Stated"
        elif has_relative_statement:
            best_before_status = "relative_statement"
            best_before_notice = "Best-before period is stated relative to the manufacturing date; an exact date could not be calculated."
            expiry_status_display = "⚠️ Relative Best-Before Statement Detected"

        # 4. Net Weight / Quantity Regex
        weight_match = re.search(
            r'(?:NET\s*QTY\.?|NET\s*QUANTITY|NET\s*WT\.?|NET\s*WEIGHT|WEIGHT|QTY\.?)\s*[:#]?\s*(\d+(?:\.\d+)?\s*(?:g|kg|ml|L|G|KG|ML))',
            text_upper, re.IGNORECASE
        )
        net_weight = weight_match.group(1).strip() if weight_match else None
        if not net_weight:
            standalone_weight = re.search(r'\b(\d+(?:\.\d+)?\s*(?:g|kg|ml))\b', text_upper, re.IGNORECASE)
            if standalone_weight and ("NET" in text_upper or "QTY" in text_upper):
                net_weight = standalone_weight.group(1).strip()
        if net_weight:
            net_weight = re.sub(r'\b(G|KG|ML|L)\b', lambda m: m.group(1).lower(), net_weight)

        # 5. Serving Size Regex
        serving_match = re.search(r'(?:SERVING SIZE|SERVE SIZE|PER SERVING)\s*[:#]?\s*(\d+(?:\.\d+)?\s*(?:g|ml))', text_upper, re.IGNORECASE)
        serving_size = serving_match.group(1).strip() if serving_match else None

        # 6. Basis Detection
        basis = "per_100g"
        if "100 ML" in text_upper or "PER 100ML" in text_upper or "PER 100 ML" in text_upper:
            basis = "per_100ml"
        elif "100 G" in text_upper or "PER 100G" in text_upper or "PER 100 G" in text_upper:
            basis = "per_100g"
        elif "PER SERVING" in text_upper:
            basis = "serving"
        elif "PER PACK" in text_upper or "SINGLE PACK" in text_upper:
            basis = "single_pack"
        elif serving_size:
            basis = "serving"

        # 7. Table-Line Tolerant Nutrient Extraction
        def extract_num(patterns):
            for pattern in patterns:
                # Match pattern, table borders (| - _ : # whitespace), then float number
                regex = r'(?:' + pattern + r')[\s\|\:\-\_\.\=\#]*(\d+(?:\.\d+)?)\s*(?:KCAL|KJ|G|MG)?'
                match = re.search(regex, text_upper, re.IGNORECASE)
                if match:
                    try:
                        return float(match.group(1))
                    except ValueError:
                        pass
            return None

        energy_kcal = extract_num(['ENERGY', 'CALORIES', 'ENERGY VALUE'])
        protein_g = extract_num(['PROTEIN', 'PROTEINS'])
        carbohydrate_g = extract_num(['TOTAL CARBOHYDRATE', 'CARBOHYDRATE', 'CARBOHYDRATES', 'CARBS'])
        total_sugars_g = extract_num(['TOTAL SUGARS', 'TOTAL SUGAR', 'SUGARS', 'SUGAR'])
        added_sugars_g = extract_num(['ADDED SUGARS', 'ADDED SUGAR'])
        total_fat_g = extract_num(['TOTAL FAT', 'FAT'])
        saturated_fat_g = extract_num(['SATURATED FAT', 'SATURATED FATS', 'SAT FAT'])
        trans_fat_g = extract_num(['TRANS FAT', 'TRANS FATS'])
        sodium_mg = extract_num(['SODIUM', 'SODIUM MG'])
        fibre_g = extract_num(['DIETARY FIBRE', 'DIETARY FIBER', 'FIBRE', 'FIBER'])
        calcium_mg = extract_num(['CALCIUM', 'CALCIUM MG'])

        nutrition_data = {
            "energy_kcal": energy_kcal if energy_kcal is not None else "Not detected",
            "protein_g": protein_g if protein_g is not None else "Not detected",
            "carbohydrate_g": carbohydrate_g if carbohydrate_g is not None else "Not detected",
            "total_sugars_g": total_sugars_g if total_sugars_g is not None else "Not detected",
            "added_sugars_g": added_sugars_g if added_sugars_g is not None else "Not detected",
            "total_fat_g": total_fat_g if total_fat_g is not None else "Not detected",
            "saturated_fat_g": saturated_fat_g if saturated_fat_g is not None else "Not detected",
            "trans_fat_g": trans_fat_g if trans_fat_g is not None else "Not detected",
            "sodium_mg": sodium_mg if sodium_mg is not None else "Not detected",
            "fibre_g": fibre_g if fibre_g is not None else "Not detected",
            "calcium_mg": calcium_mg if calcium_mg is not None else "Not detected",
        }

        has_nutrition_detected = any(v != "Not detected" for v in nutrition_data.values())
        nutrition_status = "detected" if has_nutrition_detected else "not_detected"
        date_status = "detected" if (exp_date_str or use_by_date or mfg_date) else ("relative_statement" if has_relative_statement else "not_detected")
        batch_status = "detected" if batch_no else "not_detected"
        net_quantity_status = "detected" if net_weight else "not_detected"

        fields = {
            "product_name": {
                "value": product_name,
                "status": "detected" if product_name else "not_detected",
                "confidence": 90.0 if product_name else 0.0
            },
            "batch_number": {
                "value": batch_no,
                "status": "detected" if batch_no else "not_detected",
                "confidence": 88.0 if batch_no else 0.0
            },
            "mfg_date": {
                "value": mfg_date,
                "status": "detected" if mfg_date else "not_detected",
                "confidence": 90.0 if mfg_date else 0.0
            },
            "use_by_date": {
                "value": use_by_date,
                "status": "detected" if use_by_date else "not_detected",
                "confidence": 90.0 if use_by_date else 0.0
            },
            "best_before": {
                "value": exp_date_str or use_by_date,
                "status": best_before_status,
                "notice": best_before_notice,
                "confidence": 90.0 if (exp_date_str or use_by_date) else 0.0
            },
            "net_weight": {
                "value": net_weight,
                "status": "detected" if net_weight else "not_detected",
                "confidence": 90.0 if net_weight else 0.0
            },
            "serving_size": {
                "value": serving_size,
                "status": "detected" if serving_size else "not_detected",
                "confidence": 85.0 if serving_size else 0.0
            }
        }

        # Overall Status State
        if not text.strip() and not has_nutrition_detected and not batch_no and not exp_date_str and not product_name and not net_weight:
            ocr_status = "unclear"
            ocr_status_display = "⚠️ LABEL SCAN UNCLEAR"
        elif (product_name or net_weight) and batch_no and (exp_date_str or use_by_date) and has_nutrition_detected:
            ocr_status = "complete"
            ocr_status_display = "✅ COMPLETE SCAN"
        elif has_nutrition_detected and not (batch_no and (exp_date_str or use_by_date)):
            ocr_status = "nutrition_detected"
            ocr_status_display = "✅ NUTRITION DETECTED"
        else:
            ocr_status = "partial_success"
            ocr_status_display = "🟡 PARTIAL SUCCESS"

        is_label_found = ocr_status in ["complete", "partial_success", "nutrition_detected"]

        return {
            "raw_text": text,
            "ocr_status": ocr_status,
            "ocr_status_display": ocr_status_display,
            "nutrition_status": nutrition_status,
            "date_status": date_status,
            "batch_status": batch_status,
            "net_quantity_status": net_quantity_status,
            "fields": fields,
            "nutrition_data": nutrition_data,
            "product_name": product_name or "Not Clearly Read",
            "batch_number": batch_no or "Not Clearly Read",
            "mfg_date": mfg_date,
            "use_by_date": use_by_date,
            "exp_date": exp_date_str or use_by_date,
            "expiry_status": expiry_status,
            "expiry_status_display": expiry_status_display,
            "net_weight": net_weight or "Not detected",
            "serving_size": serving_size or "20 g",
            "basis": basis,
            "ocr_confidence": round(ocr_confidence, 1),
            "is_label_found": is_label_found,
            "system_error": False
        }

    @staticmethod
    def merge_parsed_evidence(parsed_results: list, raw_text_runs: list, elapsed_ms: float) -> dict:
        """
        Merges parsed field evidence from all image variants & region crops into a unified OCR result.
        """
        best = parsed_results[0]
        merged_nutrition = dict(best["nutrition_data"])
        merged_fields = dict(best["fields"])

        mfg_date = best["mfg_date"]
        use_by_date = best["use_by_date"]
        exp_date = best["exp_date"]
        batch_number = best["batch_number"]
        product_name = best["product_name"]
        net_weight = best["net_weight"]

        # Traverse all passes to fill in missing fields
        for res in parsed_results[1:]:
            # Fill nutrition entries
            for key, val in res["nutrition_data"].items():
                if merged_nutrition.get(key) == "Not detected" and val != "Not detected":
                    merged_nutrition[key] = val

            if (not mfg_date or mfg_date == "Not detected") and res.get("mfg_date"):
                mfg_date = res["mfg_date"]
            if (not use_by_date or use_by_date == "Not detected") and res.get("use_by_date"):
                use_by_date = res["use_by_date"]
            if (not exp_date or exp_date == "Not detected") and res.get("exp_date"):
                exp_date = res["exp_date"]
            if (not batch_number or batch_number in ("Not Clearly Read", "Not detected")) and res.get("batch_number") not in ("Not Clearly Read", "Not detected"):
                batch_number = res["batch_number"]
            if (not product_name or product_name in ("Not Clearly Read", "Not detected")) and res.get("product_name") not in ("Not Clearly Read", "Not detected"):
                product_name = res["product_name"]
            if (not net_weight or net_weight == "Not detected") and res.get("net_weight") != "Not detected":
                net_weight = res["net_weight"]

        # Recalculate statuses after merge
        has_nutrition_detected = any(v != "Not detected" for v in merged_nutrition.values())
        nutrition_status = "detected" if has_nutrition_detected else "not_detected"
        date_status = "detected" if (exp_date or use_by_date or mfg_date) else best["date_status"]
        batch_status = "detected" if (batch_number and batch_number not in ("Not Clearly Read", "Not detected")) else "not_detected"
        net_quantity_status = "detected" if (net_weight and net_weight != "Not detected") else "not_detected"

        # Update field statuses
        merged_fields["batch_number"] = {
            "value": batch_number if batch_status == "detected" else None,
            "status": batch_status,
            "confidence": 88.0 if batch_status == "detected" else 0.0
        }
        merged_fields["mfg_date"] = {
            "value": mfg_date,
            "status": "detected" if mfg_date else "not_detected",
            "confidence": 90.0 if mfg_date else 0.0
        }
        merged_fields["use_by_date"] = {
            "value": use_by_date,
            "status": "detected" if use_by_date else "not_detected",
            "confidence": 90.0 if use_by_date else 0.0
        }
        merged_fields["best_before"] = {
            "value": exp_date or use_by_date,
            "status": "detected" if (exp_date or use_by_date) else best["fields"]["best_before"]["status"],
            "notice": best["fields"]["best_before"].get("notice"),
            "confidence": 90.0 if (exp_date or use_by_date) else 0.0
        }
        merged_fields["net_weight"] = {
            "value": net_weight,
            "status": net_quantity_status,
            "confidence": 90.0 if net_quantity_status == "detected" else 0.0
        }

        # Overall Status
        if has_nutrition_detected and batch_status == "detected" and date_status == "detected":
            ocr_status = "complete"
            ocr_status_display = "✅ COMPLETE SCAN"
        elif has_nutrition_detected and (batch_status == "not_detected" or date_status == "not_detected"):
            ocr_status = "nutrition_detected"
            ocr_status_display = "✅ NUTRITION DETECTED"
        elif has_nutrition_detected or batch_status == "detected" or date_status == "detected" or net_quantity_status == "detected":
            ocr_status = "partial_success"
            ocr_status_display = "🟡 PARTIAL SUCCESS"
        else:
            ocr_status = "unclear"
            ocr_status_display = "⚠️ LABEL SCAN UNCLEAR"

        combined_text = "\n".join(raw_text_runs)

        debug_info = {
            "engine_used": best.get("engine", "PyTesseract"),
            "preprocessing_method": f"{len(parsed_results)} variants evaluated",
            "raw_text": combined_text,
            "normalized_text": combined_text.upper(),
            "processing_time_ms": elapsed_ms,
            "confidence_by_field": {
                "product_name": merged_fields["product_name"]["confidence"],
                "batch_number": merged_fields["batch_number"]["confidence"],
                "date": merged_fields["best_before"]["confidence"],
                "nutrition": 95.0 if has_nutrition_detected else 0.0,
                "net_quantity": merged_fields["net_weight"]["confidence"]
            }
        }

        return {
            "raw_text": combined_text,
            "ocr_status": ocr_status,
            "ocr_status_display": ocr_status_display,
            "nutrition_status": nutrition_status,
            "date_status": date_status,
            "batch_status": batch_status,
            "net_quantity_status": net_quantity_status,
            "fields": merged_fields,
            "nutrition_data": merged_nutrition,
            "product_name": product_name,
            "batch_number": batch_number,
            "mfg_date": mfg_date,
            "use_by_date": use_by_date,
            "exp_date": exp_date or use_by_date,
            "expiry_status": best["expiry_status"],
            "expiry_status_display": best["expiry_status_display"],
            "net_weight": net_weight,
            "serving_size": best["serving_size"],
            "basis": best["basis"],
            "ocr_confidence": best["ocr_confidence"],
            "is_label_found": ocr_status in ["complete", "partial_success", "nutrition_detected"],
            "system_error": False,
            "debug_info": debug_info
        }
