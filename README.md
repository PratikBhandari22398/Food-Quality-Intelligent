# AI-Based Intelligent Food Quality, Safety and Risk Detection System

> **Internship MVP Project** | Food & Beverage Quality Assurance Automation

An intelligent, dual-model AI + OCR computer vision platform for automated food packaging quality control, product verification, back-side label OCR extraction, nutrition profile validation, and risk alert tracking.

---

## 1. Project Overview
In modern food manufacturing, manual quality inspection of food packages is prone to human error, fatigue, and bottlenecking. This project provides a production-grade Internship MVP that automates multi-stage quality checks:
* **Product Identification**: Classifying food items (*Chips Packet*, *Milk Pouch*, *Other Food*, *Non-Food Object*) using Teachable Machine TensorFlow.js browser inference.
* **Packaging Defect Detection**: Screening physical condition (*Normal Package*, *Damaged Package*, *Unclear*).
* **Back-Side Label OCR**: Parsing Batch Numbers, Expiration Dates, Net Weight, Serving Size, and Nutrition Tables using PyTesseract / EasyOCR.
* **Database & Reference Validation**: Comparing extracted label values against verified product master records and reference standards with a 5% tolerance allowance.
* **Milk Lab Quality Screening**: Evaluating pH, Temperature, Fat %, and Solids-Not-Fat (SNF %) for dairy products.
* **Rule-Based Decision Engine**: Enforcing multi-tiered decision priorities (`REJECT > HOLD > WARNING > PASS`) and raising automated risk alerts.

---

## 2. Features
* **Dual AI Browser Classifier**: Runs 100% local client-side browser inference via TensorFlow.js models converted from Teachable Machine Keras H5 exports.
* **Dual Input Modes**: Seamless support for both **Live WebCam** streaming and **Image File Upload / Drag-and-Drop**.
* **4-Step Inspection Workflow**: Progress tracker across Front View AI, Back Label OCR, Quality/Milk Parameters, and Final Decision.
* **Field Verification Status Badges**: Displays visual indicators (`✅ Verified`, `✅ Date Valid`, `⚠️ VALUE MISMATCH`, `ℹ️ UNVERIFIED`) for extracted text fields without fabricating missing values.
* **Milk Quality Parameter Separation**: Evaluates lab parameters (`fat`, `snf`, `ph`, `temp`) in a distinct panel without mutating nutrition facts.
* **Human Operator Review Drawer**: Supports manual operator overrides (`APPROVED`, `REJECTED`, `REINSPECT_REQUESTED`) for `HOLD` or `WARNING` inspections.
* **Automated Batch Management & Risk Alerts**: Maintains batch records, tracks defect statistics, and logs high-priority risk alerts.
* **Printable PDF Inspection Reports**: Generates formal quality compliance reports directly from history records.

---

## 3. Technology Stack
* **Frontend**: HTML5, Vanilla JavaScript (ES6+), CSS3 (Modern Glassmorphism & HSL design system), Google Fonts (Inter/Outfit), Phosphor Icons.
* **Browser AI Inference**: TensorFlow.js (`@tensorflow/tfjs`) running local client-side browser evaluation.
* **Backend Framework**: FastAPI (Python 3.12), PyDantic schema validation, Uvicorn ASGI server.
* **OCR Engines**: PyTesseract (Tesseract-OCR) & EasyOCR (PyTorch-backed fallback).
* **Database & ORM**: SQLite, SQLAlchemy ORM.
* **Testing Suite**: Python `unittest`, FastAPI `TestClient`, TF-Keras model integrity verifiers.

---

## 4. System Workflow
```
                          [ START INSPECTION ]
                                   │
                           Select/Create Batch
                                   │
                         Select Expected Product
                                   │
              ┌────────────────────┴────────────────────┐
              ▼                                         ▼
      📷 Live Camera Capture                    📁 Photo File Upload
              │                                         │
              └────────────────────┬────────────────────┘
                                   │
                         Preview Front Image
                                   │
                     ┌─────────────┴─────────────┐
                     ▼                           ▼
            Model 1: Product AI        Model 2: Packaging AI
                     │                           │
                     └─────────────┬─────────────┘
                                   │
                     Display Classification & Badges
                                   │
                         STEP 2: Back-Side Scan
              ┌────────────────────┴────────────────────┐
              ▼                                         ▼
     📷 Capture Back Label                     📁 Upload Back Label
              │                                         │
              └────────────────────┬────────────────────┘
                                   │
                      OCR Extraction Engine (Python)
                                   │
               Parse Batch No, Best-Before, Net Weight & Nutrition
                                   │
              ┌────────────────────┴────────────────────┐
              ▼                                         ▼
     Product DB Verification                   Milk Lab Quality Params
     (5% Mismatch Tolerance)                   (If Product = Milk Pouch)
              │                                         │
              └────────────────────┬────────────────────┘
                                   │
                       Decision Engine Evaluation
                 (REJECT > HOLD > WARNING > PASS)
                                   │
               Display Inspection Checklist & Summary Card
                                   │
            Save Inspection Record & Trigger Risk Alert (If Needed)
                                   │
                   Human Operator Review (If Required)
```

---

## 5. AI Models
The application utilizes two distinct Teachable Machine models trained locally and converted to TensorFlow.js format (`frontend/models/`):

* **Model 1 — Product Classifier**:
  * Output shape: 4 classes
  * `Class 0`: `chips packet`
  * `Class 1`: `milk pouch`
  * `Class 2`: `other food product`
  * `Class 3`: `other object` (Non-food object)

* **Model 2 — Packaging Condition Classifier**:
  * Output shape: 3 classes
  * `Class 0`: `normal package`
  * `Class 1`: `damage package`
  * `Class 2`: `unclear`

* **Inference Pipeline**: Images are resized to $224 \times 224 \times 3$, normalized to $[-1, 1]$, and evaluated locally in-browser via TensorFlow.js.

---

## 6. OCR (Optical Character Recognition)
* **Pipeline**: Accepts back-side label snapshot, processes grayscale image normalization, and runs PyTesseract or EasyOCR tokenization.
* **Regex Extractors**:
  * Batch Codes: `BATCH NO`, `LOT NO`, `B.NO`
  * Dates: `BEST BEFORE`, `EXP DATE`, `USE BY`
  * Weights: `NET WT`, `NET QTY`
  * Nutrition Table: `ENERGY`, `PROTEIN`, `CARBOHYDRATE`, `TOTAL SUGARS`, `ADDED SUGARS`, `TOTAL FAT`, `SATURATED FAT`, `TRANS FAT`, `SODIUM`, `CALCIUM`.
* **Missing Value Handling**: Unreadable nutrient fields default strictly to `"Not detected"` or `"Not Clearly Read"`. Values are **never** invented.

---

## 7. Nutrition Profile Verification
* **Database Matching**: Compares extracted OCR values against stored product standards (`CHIP001` or `MILK001`).
* **5% Tolerance Allowance**: Differences $\le 5\%$ pass as `✅ MATCH`. Differences $> 5\%$ trigger `⚠️ VALUE MISMATCH` warnings.
* **Basis Detection**: Recognizes `per_100g`, `per_100ml`, or `serving` basis automatically.
* **Reference Screening**: Checks nutrients against configured category bounds (`✅ WITHIN REFERENCE`, `⚠️ DEVIATION DETECTED`, `❌ UNABLE TO VERIFY`).

---

## 8. Milk Quality Parameters
For `Milk Pouch` products, quality lab inputs are evaluated in a distinct panel:
* **Fat %**: Standard range $3.5\% - 4.5\%$
* **SNF %**: Minimum $8.5\%$
* **pH**: Standard range $6.4 - 6.8$ (pH $<6.2$ or $>7.0$ triggers immediate `REJECT`)
* **Temperature**: Storage target $4.0^\circ\text{C} - 8.0^\circ\text{C}$ (Temp $>12^\circ\text{C}$ triggers `REJECT`)

---

## 9. Database Architecture
SQLite database managed via SQLAlchemy (`backend/db/models.py`):
* `products`: Master product catalog, category, standard nutrition profile, milk reference JSON.
* `nutrition_records`: Verified product label profiles and basis definitions.
* `batches`: Manufacturing batch tracking, product ID, total units, defect counts, status (`ACTIVE`/`CLOSED`).
* `inspections`: Individual inspection logs, AI predictions, OCR JSON, lab params JSON, final decision status, human review records.
* `alerts`: Risk alerts logged automatically for `WARNING`, `HOLD`, or `REJECT` decisions.

---

## 10. Installation

### Prerequisites
* Python 3.10+
* Tesseract-OCR (`sudo apt-get install tesseract-ocr`)
* Node.js / npm (Optional for TF.js conversion tools)

### Setup Steps
```bash
# Clone repository
cd Food-Quality-Intelligent

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 11. How to Run

### Start FastAPI Server
```bash
source venv/bin/activate
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Access Web Interface
Open your web browser and navigate to:
```text
http://127.0.0.1:8000
```

---

## 12. How to Use Camera
1. Navigate to the **Inspection Console** tab.
2. Click `📷 USE LIVE CAMERA`.
3. Allow browser camera permission when prompted.
4. Position the food package in front of the lens.
5. Click `Capture & Inspect` to capture a frame snapshot.

---

## 13. How to Upload Images
1. Click `📁 UPLOAD PRODUCT PHOTO` or drag an image into the drag-and-drop zone.
2. Select a valid `.jpg`, `.png`, or `.webp` food package image.
3. The application will render the image preview and run AI inference automatically.

---

## 14. How to Train or Replace Teachable Machine Models
To upgrade or replace the AI models:
1. Train new image models on [Google Teachable Machine](https://teachablemachine.withgoogle.com/).
2. Export as **Keras H5** model format.
3. Convert H5 to TensorFlow.js format using `tensorflowjs_converter`:
   ```bash
   tensorflowjs_converter --input_format=keras model.h5 frontend/models/product_model/
   ```
4. Ensure label order matches `metadata.json`.

---

## 15. Testing
Run the automated test suite covering unit, API, OCR, model verification, and decision engine rules:
```bash
source venv/bin/activate
python -m unittest discover tests
```
*Current test suite result*: **131 / 131 tests passed (100%)**.

---

## 16. Limitations
* **Dataset Scope**: Teachable Machine models are *Validated on current test set*. Universal multi-brand accuracy across unseen environments requires dataset expansion.
* **Environmental Factors**: Severe camera glare, extreme package tilt ($>45^\circ$), or dark blurry text will trigger the operator retry warning (`Prediction unclear / Capture another image`).

---

## 17. Future Final-Year Upgrades (Roadmap)
* **IoT Sensor Integration**: Real-time MQTT streaming from industrial temperature, pH, and humidity sensors.
* **Real-time Industrial Cameras**: High-speed RTSP IP camera feed integration for conveyor belts.
* **Worker Safety & PPE Detection**: Secondary AI model for helmet, glove, and hairnet compliance on production lines.
* **Multi-Product YOLO Expansion**: Upgrading from classification to multi-object bounding-box detection.
* **Predictive Shelf-Life Modeling**: ML regression for shelf-life estimation based on storage temperature drift.
