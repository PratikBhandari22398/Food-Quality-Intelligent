# REAL-WORLD SYSTEM TEST PLAN & TEST MATRIX

## Project Title
AI-Based Intelligent Food Quality, Safety and Risk Detection System for Food & Beverage Manufacturing

## Purpose
This document establishes the real-world validation protocol, test groups, camera operating boundaries, and test evaluation matrix for testing the full food quality inspection workflow using physical food package samples and live camera streams.

---

## 1. Test Groups & Scope

### A. Product Classification Model (Model 1)
- **Chips Packet**: Front-side inspection of branded potato/snack chip packaging.
- **Milk Pouch**: Front-side inspection of standard liquid milk pouch packaging.
- **Other Food Product**: Other food packages (e.g., biscuit packs, juice boxes).
- **Other Object**: Non-food physical objects (e.g., coffee mug, notebook, phone).

### B. Packaging Condition Model (Model 2)
- **Normal Package**: Pristine, undamaged package surface with clean seals.
- **Damage Package**: Visible surface tears, crushes, major dents, or punctures.
- **Unclear**: Obscured, heavily blurred, or unidentifiable packaging condition.

### C. OCR Label & Back-Side Inspection Engine
- **Chips Nutrition Label**: Back-side nutritional table & text.
- **Milk Nutrition Label**: Back-side milk nutritional table.
- **Batch Code Extraction**: Extracted lot/batch numbers (`BATCH`, `LOT`, `B.NO`).
- **Best-Before Date**: Extracted expiration date (`EXP`, `BEST BEFORE`, `USE BY`).
- **Net Weight / Net Qty**: Extracted weight/volume (`g`, `kg`, `ml`).
- **Nutrition Facts**: Energy, Protein, Carbohydrates, Total Sugars, Added Sugars, Total Fat, Saturated Fat, Trans Fat, Sodium, Fibre, Calcium.

### D. Decision Engine Outcome Categories
- **PASS**: All AI, OCR label, and milk quality parameters are verified within reference.
- **WARNING**: Unclear AI prediction, missing OCR text, or minor nutrient/pH drift.
- **HOLD**: Product mismatch, non-food object, or sub-standard fat/SNF levels.
- **REJECT**: Packaging damage detected, expired best-before date, or severe milk acidity ($pH < 6.2$).

---

## 2. Test Environment & Camera Conditions Matrix

| Condition ID | Environment Parameter | Operating Range | Testing Focus |
| :--- | :--- | :--- | :--- |
| **ENV-1** | Lighting Level | Good Ambient (300+ lux) vs Low Indoor (50 lux) | AI model classification stability |
| **ENV-2** | Camera Distance | 15 cm (Macro) to 60 cm (Far View) | Focal depth & OCR text extraction |
| **ENV-3** | Viewing Angle | Frontal ($0^\circ$) vs Side/Oblique ($45^\circ$) | Perspective distortion tolerance |
| **ENV-4** | Package Orientation | Upright ($0^\circ$) vs Rotated ($90^\circ / 180^\circ$) | Invariance to package rotation |
| **ENV-5** | Surface Reflection | Matte Packaging vs Metallic Foil Glare | Optical glare resistance for OCR |

## 4. Front-Side vs Back-Side Inspection Workflow

```
STEP 1: Front-Side Image Capture
  ├── Purpose: Product Identification & Packaging Damage Check (Model 1 & Model 2)
  ├── Guidance: Complete package visible, good ambient light, minimal tilt/glare
  └── Status: Triggers "Inspection Incomplete" if back-side scan is pending

STEP 2: Back-Side Label OCR Scan
  ├── Purpose: Batch Code, Expiration Date, Net Weight & Nutrition Table Verification
  ├── Guidance: Hold label flat, align text in focus, avoid metallic foil reflections
  └── Status: Performs date validation & database nutrition reference screening

STEP 3: Product-Specific Quality Screening
  ├── Chips: Nutrition table match & reference screening
  └── Milk: Fat %, SNF %, pH level, and temperature checks

STEP 4: Final Quality Decision & Summary
  └── Priority: REJECT > HOLD > WARNING > PASS
```

## 5. System Accuracy & Validation Scope Declaration
* **Scope**: Validated on current test set.
* **Function**: AI-assisted inspection & reference screening prototype.

