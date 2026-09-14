import datetime
from typing import Dict, Any, List, Optional
from backend.config import DEFAULT_MILK_REFERENCE, DEFAULT_NUTRITION_PROFILES

class DecisionEngine:
    @staticmethod
    def evaluate(
        expected_product: str,
        detected_product: str,
        product_confidence: float,
        packaging_condition: str,
        condition_confidence: float,
        ocr_data: Optional[Dict[str, Any]] = None,
        milk_lab_params: Optional[Dict[str, Any]] = None,
        batch_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluates complete food inspection workflow rules across AI models, OCR back-side label,
        and lab quality parameters. Returns status (PASS, WARNING, HOLD, REJECT), checklist UI indicators,
        summary card data, and recommended actions.
        """
        reasons: List[str] = []
        status_ranks = {"PASS": 1, "WARNING": 2, "HOLD": 3, "REJECT": 4}
        current_status = "PASS"
        recommended_action = "All configured inspection checks passed. Proceed with normal production."

        checklist = {
            "Product Detection": "✅",
            "Product Match": "✅",
            "Package Condition": "✅",
            "Label Readability": "✅",
            "Batch Number": "✅",
            "Best Before": "✅",
            "Nutrition": "✅",
            "Milk Quality": "N/A",
            "Final Decision": "✅"
        }

        def escalate_status(new_status: str, reason_text: str, action: str):
            nonlocal current_status, recommended_action
            reasons.append(reason_text)
            if status_ranks[new_status] > status_ranks[current_status]:
                current_status = new_status
                recommended_action = action

        # -------------------------------------------------------------
        # 1. Non-Food Object / Other Object Rule (Requirement 18)
        # -------------------------------------------------------------
        det_lower = detected_product.strip().lower() if detected_product else ""
        exp_raw = (expected_product or "").strip()
        exp_lower = exp_raw.lower()
        is_general_inspection = exp_lower in ["", "none", "not specified", "n/a", "unspecified"]

        if is_general_inspection:
            checklist["Product Match"] = "N/A"

        det_category = "Milk" if "milk" in det_lower else ("Chips" if "chips" in det_lower else "Other")
        exp_category = "Milk" if "milk" in exp_lower else ("Chips" if "chips" in exp_lower else "Other")

        if det_lower == "other object" or "other object" in det_lower:
            checklist["Product Detection"] = "❌"
            if not is_general_inspection:
                checklist["Product Match"] = "❌"
            escalate_status(
                "HOLD",
                "No supported food product detected.",
                "Remove non-food object from production inspection line."
            )

        # -------------------------------------------------------------
        # 2. Category Mismatch & Product Verification Rules (Explicit Mode Only)
        # -------------------------------------------------------------
        elif not is_general_inspection:
            if (det_category != "Other" and exp_category != "Other" and det_category != exp_category) or (exp_lower != det_lower and det_lower != "other food product"):
                checklist["Product Match"] = "❌"
                escalate_status(
                    "HOLD",
                    "Expected and detected products do not match.",
                    "Human verification required. Confirm physical batch product match."
                )

        if det_lower == "other food product":
            checklist["Product Match"] = "⚠"
            escalate_status(
                "WARNING",
                "Product recognized: Other Food Product. detailed verification data is unavailable for unconfigured product.",
                "Select or configure product profile manually."
            )
        elif product_confidence < 0.65 and det_lower != "other object" and "other object" not in det_lower:
            checklist["Product Detection"] = "⚠"
            escalate_status(
                "WARNING",
                f"Low AI Product Confidence: '{detected_product}' classification confidence is {product_confidence*100:.1f}% (Threshold: 65%).",
                "Capture another clear image of product front."
            )

        # -------------------------------------------------------------
        # 3. Packaging Condition Evaluation (Requirement 4 & 15)
        # -------------------------------------------------------------
        cond_lower = packaging_condition.strip().lower()
        if "damage" in cond_lower:
            checklist["Package Condition"] = "❌"
            escalate_status(
                "REJECT",
                "Visible package damage detected.",
                "Remove/inspect product according to manufacturing procedure."
            )
        elif "unclear" in cond_lower or condition_confidence < 0.65:
            checklist["Package Condition"] = "⚠"
            escalate_status(
                "WARNING",
                "Package condition could not be verified clearly.",
                "Capture another image of package condition."
            )

        # -------------------------------------------------------------
        # 4. OCR & Label Verification (Requirements 4, 9, 10, 14, 15, Step 15)
        # -------------------------------------------------------------
        ocr_status_code = ocr_data.get("ocr_status") if ocr_data else None
        if not ocr_data:
            checklist["Label Readability"] = "N/A"
            checklist["Batch Number"] = "N/A"
            checklist["Best Before"] = "N/A"
            checklist["Nutrition"] = "✅"
        elif ocr_status_code == "unclear" or not ocr_data.get("is_label_found", True):
            checklist["Label Readability"] = "⚠"
            checklist["Batch Number"] = "⚠"
            checklist["Best Before"] = "⚠"
            checklist["Nutrition"] = "✅"
        else:
            checklist["Label Readability"] = "✅"
            fields = ocr_data.get("fields", {})

            # Nutrition Status
            nutr_status = ocr_data.get("nutrition_status")
            if nutr_status == "detected" or ocr_data.get("has_nutrition_detected"):
                checklist["Nutrition"] = "✅"

            # Batch Number Readability
            ocr_batch = ocr_data.get("batch_number")
            batch_status = fields.get("batch_number", {}).get("status")
            if ocr_batch in ("Not Clearly Read", "Not detected") or batch_status == "not_detected":
                checklist["Batch Number"] = "⚠"
                escalate_status(
                    "WARNING",
                    "Batch number not detected on package label.",
                    "Re-scan package back label or verify batch code manually."
                )

            # Best Before Date Verification
            bb_info = fields.get("best_before", {})
            bb_status = bb_info.get("status")
            expiry_status = ocr_data.get("expiry_status")
            exp_date_str = ocr_data.get("exp_date")

            if expiry_status == "EXPIRED":
                checklist["Best Before"] = "❌"
                escalate_status(
                    "REJECT",
                    f"Best-before verification failed: Product date ({exp_date_str}) has expired.",
                    "Reject item and quarantine expired batch package."
                )
            elif bb_status == "relative_statement":
                checklist["Best Before"] = "⚠"
                notice_msg = bb_info.get("notice") or "Best-before period is stated relative to the manufacturing date; an exact date could not be calculated."
                escalate_status(
                    "WARNING",
                    notice_msg,
                    "Verify physical manufacturing date and batch code manually."
                )
            elif bb_status == "not_detected" or exp_date_str in ("Not detected", "Not Clearly Read"):
                checklist["Best Before"] = "⚠"
                escalate_status(
                    "WARNING",
                    "Best-before date not detected on package label.",
                    "Verify physical expiration date manually."
                )

            # Product Name Consistency (AI vs OCR vs Expected - Explicit Mode Only)
            ocr_pname = ocr_data.get("product_name")
            if not is_general_inspection and ocr_pname and ocr_pname not in ("Not Clearly Read", "Not detected"):
                ocr_pname_lower = ocr_pname.lower()
                if not (exp_lower in ocr_pname_lower or ocr_pname_lower in exp_lower or det_lower in ocr_pname_lower):
                    checklist["Product Match"] = "❌"
                    escalate_status(
                        "HOLD",
                        f"Product information mismatch: OCR label name ('{ocr_pname}') does not match expected product ('{expected_product}').",
                        "Human verification required. Confirm package label authenticity."
                    )

            # Nutrition OCR Mismatch Check
            has_mismatch = ocr_data.get("has_nutrition_mismatch", False)
            if has_mismatch:
                checklist["Nutrition"] = "⚠"
                escalate_status(
                    "WARNING",
                    "Nutrition value mismatch requiring human review.",
                    "Inspect physical label nutrition panel and verify values."
                )

        # -------------------------------------------------------------
        # 5. Milk Quality Parameters Evaluation (Milk Pouch only)
        # -------------------------------------------------------------
        milk_eval_result = {}
        if "milk" in exp_lower or "milk" in det_lower:
            checklist["Milk Quality"] = "✅"
            if milk_lab_params:
                fat = milk_lab_params.get("fat")
                snf = milk_lab_params.get("snf")
                ph = milk_lab_params.get("ph")
                temp = milk_lab_params.get("temperature")

                ref = DEFAULT_MILK_REFERENCE

                # pH Evaluation
                if ph is not None:
                    ph = float(ph)
                    milk_eval_result["ph"] = ph
                    if ph < 6.2 or ph > 7.0:
                        checklist["Milk Quality"] = "❌"
                        escalate_status(
                            "REJECT",
                            f"Critical Milk Quality Failure: Measured pH {ph:.2f} is outside safe limits (6.2 - 7.0).",
                            "Reject milk batch due to severe acidity/pH safety breach."
                        )
                    elif ph < ref["min_ph"] or ph > ref["max_ph"]:
                        checklist["Milk Quality"] = "⚠"
                        escalate_status(
                            "WARNING",
                            f"Milk pH Drift: Measured pH {ph:.2f} deviates from standard reference ({ref['min_ph']} - {ref['max_ph']}).",
                            "Monitor tank acidity and check temperature regulation."
                        )

                # Temperature Evaluation
                if temp is not None:
                    temp = float(temp)
                    milk_eval_result["temperature"] = temp
                    if temp > 12.0:
                        checklist["Milk Quality"] = "❌"
                        escalate_status(
                            "REJECT",
                            f"Cold Chain Breach: Milk Temperature {temp:.1f}°C exceeds safety limit (12°C).",
                            "Reject pouch and check chiller storage."
                        )
                    elif temp > ref["max_temp"]:
                        checklist["Milk Quality"] = "⚠"
                        escalate_status(
                            "WARNING",
                            f"Milk Temperature High: Measured {temp:.1f}°C is above target storage temp ({ref['max_temp']}°C).",
                            "Adjust storage chiller temperature."
                        )

                # Fat % Evaluation
                if fat is not None:
                    fat = float(fat)
                    milk_eval_result["fat"] = fat
                    if fat < 3.0:
                        checklist["Milk Quality"] = "❌"
                        escalate_status(
                            "HOLD",
                            f"Sub-standard Fat Content: Fat level is {fat:.2f}% (Minimum standard: 3.5%).",
                            "Hold batch for fat standardization check."
                        )
                    elif fat < ref["min_fat"] or fat > ref["max_fat"]:
                        checklist["Milk Quality"] = "⚠"
                        escalate_status(
                            "WARNING",
                            f"Fat % Out of Standard Target: {fat:.2f}% (Reference: {ref['min_fat']}% - {ref['max_fat']}%).",
                            "Adjust milk blending ratio."
                        )

                # SNF % Evaluation
                if snf is not None:
                    snf = float(snf)
                    milk_eval_result["snf"] = snf
                    if snf < 8.0:
                        checklist["Milk Quality"] = "❌"
                        escalate_status(
                            "HOLD",
                            f"Sub-standard Solids-Not-Fat (SNF): {snf:.2f}% (Minimum standard: 8.5%).",
                            "Hold batch for lab SNF re-testing."
                        )

        # -------------------------------------------------------------
        # 6. Final Status & Summary Card Construction
        # -------------------------------------------------------------
        if current_status == "PASS":
            if is_general_inspection:
                if "milk" in det_lower:
                    reasons.insert(0, "Milk pouch detected and package condition appears normal.")
                elif "chips" in det_lower:
                    reasons.insert(0, "Chips packet detected and package condition appears normal.")
                else:
                    reasons.insert(0, "Product detected and package condition appears normal.")
            else:
                reasons.insert(0, "All configured inspection checks passed successfully.")
            checklist["Final Decision"] = "✅ PASS"
        elif current_status == "WARNING":
            checklist["Final Decision"] = "⚠ WARNING"
        elif current_status == "HOLD":
            checklist["Final Decision"] = "✋ HOLD"
        elif current_status == "REJECT":
            checklist["Final Decision"] = "❌ REJECT"

        # Determine nutrition profile automatically based on detected product in General mode
        nutr_key = detected_product if (is_general_inspection or not expected_product) else expected_product
        raw_nutr = DEFAULT_NUTRITION_PROFILES.get(
            nutr_key,
            DEFAULT_NUTRITION_PROFILES.get(detected_product, DEFAULT_NUTRITION_PROFILES.get("Chips Packet", {}))
        )
        verified_nutrition = dict(raw_nutr) if isinstance(raw_nutr, dict) else {}
        if "nutrition_table" in verified_nutrition and isinstance(verified_nutrition["nutrition_table"], dict):
            verified_nutrition.update(verified_nutrition["nutrition_table"])

        b_num_display = batch_number or (ocr_data.get("batch_number") if ocr_data else None)
        if is_general_inspection and not batch_number:
            b_num_display = "N/A"

        summary_card = {
            "status": current_status,
            "overall_reason": reasons[0] if reasons else "Inspection completed.",
            "product_confidence": f"{product_confidence*100:.1f}%",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "batch_number": b_num_display or "N/A",
            "detected_product": detected_product,
            "package_condition": packaging_condition,
            "recommended_action": recommended_action
        }

        return {
            "final_status": current_status,
            "reasons": reasons,
            "recommended_action": recommended_action,
            "detected_product": detected_product,
            "product_confidence": product_confidence,
            "packaging_condition": packaging_condition,
            "condition_confidence": condition_confidence,
            "checklist": checklist,
            "summary_card": summary_card,
            "verified_nutrition": verified_nutrition,
            "milk_params_eval": milk_eval_result
        }


