# Guided Demo Flow & Demo Dataset Documentation (Step 20)

## Executive Summary
Guided Demo Mode (`[ 🎬 START DEMO ]`) provides an interactive 10-step guided tour through the AI Food Quality & Risk Detection System. It demonstrates real application features—live AI classification, damage detection, milk lab parameters, category mismatch handling, batch management, expiry monitoring, audit logs, and printable PDF reporting—without substituting real models with artificial predictions.

---

## 1. Guided Demo Flow Steps

| Step # | Title | Application View | Description & Feature Highlights |
|---|---|---|---|
| **Step 1** | Executive Quality Dashboard | Dashboard (`view-dashboard`) | Displays overall inspection volume, status distribution, active alerts, and throughput charts. |
| **Step 2** | Live Quality Inspection Console | Live Inspection (`view-inspection`) | Introduces front camera / photo upload viewport and 3-step progress indicator. |
| **Step 3** | Chips Packet Inspection (PASS) | Live Inspection (`view-inspection`) | Classifies 'Chips Packet' ($96.4\%$) and 'Normal Package' ($93.1\%$), auto-fetches nutrition -> `🟢 PASS`. |
| **Step 4** | Damaged Package Detection (REJECT) | Live Inspection (`view-inspection`) | Classifies 'Damage Package' ($91.0\%$) -> `🔴 REJECT`. Recommends stock quarantine. |
| **Step 5** | Milk Pouch & Lab Parameters (PASS) | Live Inspection (`view-inspection`) | Classifies 'Milk Pouch' ($96.2\%$), loads Per 100 ml liquid nutrition, verifies lab params -> `🟢 PASS`. |
| **Step 6** | Product Category Mismatch (HOLD) | Live Inspection (`view-inspection`) | Expected 'Chips' vs Detected 'Milk' mismatch -> `🟠 HOLD`. |
| **Step 7** | Production Batch Management | Batches (`view-batches`) | Lists production batches, manufacturing dates, shelf-life rules, and active batch selection. |
| **Step 8** | Expiry Monitoring & Stock at Risk | Dashboard (`view-dashboard`) | Highlights stock risk categories (Normal, Expiring Soon, Expired) and Stock at Risk table. |
| **Step 9** | Inspection Audit Logs & History | History (`view-history`) | Displays persistent inspection history audit logs saved in SQLite (`food_quality.db`). |
| **Step 10** | Printable Audit Report Modal | History (`view-history`) | Opens interactive PDF report modal containing AI scores, label verification, and operator review. |

---

## 2. Interactive Navigation Controls
The overlay banner floats non-intrusively at the top of the viewport:
- **`← Previous`**: Returns to the previous demo step.
- **`Next →`**: Advances to the next demo step.
- **`Skip`**: Immediately exits Guided Demo Mode and returns to Dashboard view.
- **`Finish Demo`**: Concludes the guided tour on Step 10 and displays completion notification.

---

## 3. Demo Dataset & Seeding Policy
Seeded records are tagged with `data_source = 'DEMO'` or `expiry_source = 'DEMO'` to ensure transparency:
- **Batches**:
  - `BAT-DEMO-CHIPS-01`: Active Chips batch ($110$ days remaining, `NORMAL`)
  - `BAT-DEMO-CHIPS-02`: Expiring Chips batch ($15$ days remaining, `EXPIRING_SOON`)
  - `BAT-DEMO-MILK-01`: Active Milk batch ($60$ days remaining, `NORMAL`)
  - `BAT-DEMO-MILK-02`: Expired Milk batch (Expired by $5$ days, `EXPIRED`)
  - `DEMO-EXP-004`: Milk batch with unconfigured expiry (`UNKNOWN`)
- **Inspection Logs**:
  - Chips PASS ($96.4\%$), Chips REJECT ($92.5\%$), Milk PASS ($96.2\%$), Milk WARNING ($62.0\%$), Category Mismatch HOLD ($91.5\%$).

---

## 4. Safety & Terminology Disclosures
> [!NOTE]
> All UI notifications, guided steps, and reports use standard safety disclosures:
> - *"AI-assisted inspection"*
> - *"Reference screening"*
> - *"Expiry monitoring"*
> - *"Waste-prevention support"*
> 
> Guarantees of zero waste, financial savings, or independent food safety certifications are explicitly disclaimed.

---

## 5. UI Button Audit Summary

| # | Button Label / ID | Location | Status |
|---|---|---|---|
| 1 | `🎬 START DEMO` (`#btn-start-demo`) | Header Bar | ✅ Tested & Working |
| 2 | `Next →` (`#btn-demo-next`) | Demo Overlay | ✅ Tested & Working |
| 3 | `← Previous` (`#btn-demo-prev`) | Demo Overlay | ✅ Tested & Working |
| 4 | `Skip` (`#btn-demo-skip`) | Demo Overlay | ✅ Tested & Working |
| 5 | `Finish Demo` (`#btn-demo-next` on Step 10) | Demo Overlay | ✅ Tested & Working |
| 6 | `VIEW INSPECTION` | Dashboard Table | ✅ Tested & Working |
| 7 | `VIEW BATCH` | Dashboard Table | ✅ Tested & Working |
| 8 | `VIEW ALERT` | Alert Center | ✅ Tested & Working |
| 9 | `Report` / `OPEN REPORT` | History Table | ✅ Tested & Working |
| 10 | `Print / Save PDF` | Report Modal | ✅ Tested & Working |
| 11 | `Live Inspection` | Nav Tabs | ✅ Tested & Working |
| 12 | `📷 USE CAMERA` | Inspection Console | ✅ Tested & Working |
| 13 | `📁 UPLOAD PHOTO` | Inspection Console | ✅ Tested & Working |
| 14 | `⚡ INSPECT` | Inspection Console | ✅ Tested & Working |
| 15 | `↻ RESET` | Inspection Console | ✅ Tested & Working |
