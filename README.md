# QualiGuard AI — Intelligent Food Quality, Safety & Risk Detection System

> **Automated Food Packaging Quality Assurance & Expiry Risk Monitoring Platform**

QualiGuard AI is an intelligent computer vision and automated decision-engine platform designed for quality control, defect screening, and waste prevention in food manufacturing, packaging, and distribution lines.

---

## 🌟 Key Features

- 🤖 **Dual Computer Vision AI**: Real-time product category identification (*Chips Packet*, *Milk Pouch*) and physical packaging defect classification (*Normal Package*, *Damaged Package*).
- ⚡ **Automated Decision Engine**: Multi-tiered decision rules (`REJECT > HOLD > WARNING > PASS`) evaluating product match, packaging defects, and quality parameters.
- 📦 **Batch Expiry & Waste Prevention**: Real-time batch tracking identifying normal stock, stock expiring soon, and expired inventory to prevent food waste.
- 🥗 **Automatic Verified Nutrition**: Instant display of verified nutritional facts (Energy, Fat, Carbs, Protein, Calcium/Sodium) per 100g, per serving, and per pack upon detection.
- 🥛 **Dairy & Milk Quality Screening**: Quality lab parameter evaluation for pH, Storage Temperature, Fat %, and Solids-Not-Fat (SNF %).
- 📊 **Live Analytics Dashboard**: Real-time KPIs, defect trend charts, risk alert feeds, and downloadable inspection reports.
- 📱 **Responsive Glassmorphism UI**: High-impact modern web interface optimized for Desktops, Laptops, Tablets, and Mobile devices.

---

## 🏗️ Technology Stack

| Layer | Technologies Used |
| :--- | :--- |
| **Frontend** | HTML5, Vanilla JavaScript (ES6+), Modern CSS3 (Glassmorphic Design), Phosphor Icons, Chart.js |
| **AI / Machine Learning** | TensorFlow.js (Local Client-Side Inference), Keras Models |
| **Backend API** | FastAPI (Python 3.12), PyDantic, Uvicorn ASGI Server |
| **Database & ORM** | SQLite, SQLAlchemy ORM |
| **Testing & Verification** | Python `unittest` Suite (131 Automated Tests) |

---

## 🚀 Quick Start Guide

### 1. Installation
```bash
# Clone repository
git clone https://github.com/PratikBhandari22398/Food-Quality-Intelligent.git
cd Food-Quality-Intelligent

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Application
```bash
source venv/bin/activate
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser and navigate to: **`http://127.0.0.1:8000`**

---

## 🧪 Automated Test Suite

Run the full automated test suite covering API endpoints, decision engine logic, AI model inference, and batch expiry monitoring:

```bash
python -m unittest discover tests
```
> **Test Status**: ✅ **131 / 131 Tests Passed (100%)**
