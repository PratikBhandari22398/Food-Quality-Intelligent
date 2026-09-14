# Batch Expiry Monitoring & Waste Prevention

## 1. Feature Purpose
The Batch Expiry Monitoring & Waste Prevention module provides persistent, real-time tracking of manufacturing batch shelf-life across F&B inventory. It assists staff in identifying products nearing expiry and prioritizing stock rotation to minimize avoidable food waste.

> [!IMPORTANT]
> **Waste Prevention Support Notice**: This system provides decision-support visibility ("Waste Prevention Support") and early risk alerts. It does not claim automated food safety certification or guaranteed zero waste without manual operator verification and rotational procedure compliance.

---

## 2. Data Fields
The `batches` table in SQLite (`food_quality.db`) contains the following extended schema:

| Column Name | Type | Description |
|---|---|---|
| `batch_number` | VARCHAR | Unique identifier code for the production batch |
| `product_id` | INTEGER | Foreign key referencing `products.id` |
| `mfg_date` / `manufacture_date` | VARCHAR | Manufacturing date (YYYY-MM-DD or readable string) |
| `exp_date` / `expiry_date` | VARCHAR | Resolved expiry or best-before date (YYYY-MM-DD) |
| `expiry_rule_type` | VARCHAR | Calculation method (`EXPLICIT_DATE` or `MONTHS_FROM_MANUFACTURE`) |
| `expiry_duration_months` | INTEGER | Relative duration in months when rule type is `MONTHS_FROM_MANUFACTURE` |
| `expiry_source` | VARCHAR | Provenance (`LABEL_EXPLICIT`, `PRODUCT_SHELF_LIFE_RULE`, `USER_MANUAL`, `DEMO`) |
| `expiry_status` | VARCHAR | Status classification (`NORMAL`, `EXPIRING_SOON`, `EXPIRED`, `UNKNOWN`) |
| `last_expiry_check` | DATETIME | Timestamp of last automated expiry status check |

---

## 3. Explicit Date Handling
When a verified package label or user input provides an explicit date (`USE BY`, `BEST BEFORE`, or `EXPIRY`), explicit date priority is enforced. The explicit date takes precedence over any calculated relative shelf life.

---

## 4. Relative Shelf-Life Handling
When a relative shelf-life rule is configured (`expiry_rule_type = "MONTHS_FROM_MANUFACTURE"`), the expiry date is computed as:
$$\text{Expiry Date} = \text{Manufacture Date} + N \text{ Months}$$
Calendar month boundaries and leap years are preserved.

For the configured demo product (**Chips**), a 4-month relative shelf-life rule is applied when explicit dates are absent. Milk products use explicit package labels unless configured otherwise.

---

## 5. Warning Window
The warning threshold is controlled by the centralized configuration setting:
```python
EXPIRY_WARNING_DAYS = 30
```
Batches with days remaining between $0$ and $30$ enter the `EXPIRING_SOON` status.

---

## 6. Expiry Status Rules
Each batch is assigned one of four distinct expiry statuses:
- **`NORMAL`**: Expiry date is outside the warning window ($> 30$ days remaining).
- **`EXPIRING_SOON`**: Expiry date is within the warning window ($0 \le \text{days} \le 30$).
- **`EXPIRED`**: Expiry date has passed ($\text{days} < 0$).
- **`UNKNOWN`**: Manufacture or expiry date information is missing or unparseable.

---

## 7. Alerts & Deduplication
- **`EXPIRING_SOON` Alert**: Generates a `⚠ PRODUCT EXPIRING SOON` warning alert in the Alert Center with recommended action: *"Review and prioritize this stock according to company procedure."*
- **`EXPIRED` Alert**: Generates a `🚨 EXPIRED BATCH` reject alert in the Alert Center with recommended action: *"Inspect and quarantine/remove according to company procedure."*
- **Alert Deduplication**: Alerts are deduplicated by `batch_number` and status category. Repeated page refreshes or backend restarts do NOT create duplicate alert records. No automatic product deletion occurs.

---

## 8. Dashboard Overview
The Dashboard features:
1. **EXPIRY MONITORING Cards**: Live stat counters for Normal, Expiring Soon, Expired, and Unknown stock.
2. **STOCK AT RISK Table**: Displays batches in `EXPIRING_SOON` or `EXPIRED` status sorted by earliest expiry date.
3. **Guidance Note**: *"Track batches approaching expiry so staff can review stock in time and reduce avoidable waste."*

---

## 9. Batches Page & Modal Timeline
- **Batches Table**: Displays Batch Number, Product Name, Manufacturing Date, Expiry Date, Days Remaining text (e.g. `"15 days remaining"`, `"Expired by 4 days"`), Expiry Status badge, Inspection Count, and Actions.
- **Batch Details & Timeline Modal**: Interactive drawer displaying batch metadata, rule type, and a visual 4-step lifecycle timeline:
  $$\text{Manufactured} \longrightarrow \text{Normal Stock} \longrightarrow \text{Expiring Soon} \longrightarrow \text{Expired}$$

---

## 10. Persistence
All batch records, manufacture/expiry dates, expiry statuses, and generated alerts are persisted in SQLite (`food_quality.db`). All metrics survive browser refreshes, application restarts, and system reboots.

---

## 11. Demo Dataset
A pre-configured demo batch set is seeded into SQLite on initial database initialization:
- `DEMO-EXP-001` (Chips): Expiring in 15 days (`EXPIRING_SOON`)
- `DEMO-EXP-002` (Milk): Expiring in 60 days (`NORMAL`)
- `DEMO-EXP-003` (Chips): Expired 5 days ago (`EXPIRED`)
- `DEMO-EXP-004` (Milk): Missing date information (`UNKNOWN`)

All demo records are marked with `expiry_source = "DEMO"`.

---

## 12. Limitations
- Expiry calculations rely on valid date inputs or configured shelf-life rules.
- Negative days remaining are cleanly formatted for operator readability (e.g. `"Expired by 4 days"`) rather than raw negative numbers.
- Automatic product disposal is intentionally excluded to prevent accidental data loss or inventory discrepancies.
