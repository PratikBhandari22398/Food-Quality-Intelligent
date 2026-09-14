import unittest
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db.database import Base
from backend.db.models import Product, Batch, Alert, Inspection
from backend.services.expiry_service import (
    calculate_batch_expiry,
    update_all_batch_expiry_statuses,
    parse_date_string,
    add_months
)
from backend.config import EXPIRY_WARNING_DAYS

class TestExpiryMonitoring(unittest.TestCase):
    def setUp(self):
        """Set up an in-memory SQLite database for test execution."""
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = Session()

        # Create test products
        self.chips_product = Product(name="Test Chips Packet", category="Chips", mrp="₹20")
        self.milk_product = Product(name="Test Milk Pouch", category="Milk", mrp="₹31")
        self.db.add_all([self.chips_product, self.milk_product])
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_01_manufacture_date_plus_4_month_rule(self):
        """TEST 1: Manufacture date + 4-month configured rule calculates correct expiry."""
        today = datetime.date(2026, 9, 14)
        mfg_date = "2026-07-20"
        calc = calculate_batch_expiry(
            manufacture_date_str=mfg_date,
            expiry_date_str=None,
            expiry_rule_type="MONTHS_FROM_MANUFACTURE",
            expiry_duration_months=4,
            product_name="Test Chips Packet",
            today_override=today
        )
        self.assertEqual(calc["expiry_date"], "2026-11-20")
        self.assertEqual(calc["expiry_status"], "NORMAL")
        self.assertEqual(calc["expiry_source"], "PRODUCT_SHELF_LIFE_RULE")

    def test_02_explicit_expiry_date_priority(self):
        """TEST 2: Explicit expiry date takes priority over relative calculations."""
        today = datetime.date(2026, 9, 14)
        calc = calculate_batch_expiry(
            manufacture_date_str="2026-07-20",
            expiry_date_str="2026-12-02",
            expiry_rule_type="MONTHS_FROM_MANUFACTURE",
            expiry_duration_months=4,
            product_name="Test Chips Packet",
            today_override=today
        )
        self.assertEqual(calc["expiry_date"], "2026-12-02")
        self.assertEqual(calc["expiry_source"], "LABEL_EXPLICIT")

    def test_03_relative_rule_missing_manufacture_date(self):
        """TEST 3: Relative expiry rule with missing manufacture date returns UNKNOWN."""
        calc = calculate_batch_expiry(
            manufacture_date_str=None,
            expiry_date_str=None,
            expiry_rule_type="MONTHS_FROM_MANUFACTURE",
            expiry_duration_months=4
        )
        self.assertEqual(calc["expiry_status"], "UNKNOWN")
        self.assertIsNone(calc["expiry_date"])
        self.assertEqual(calc["days_remaining_text"], "Unknown expiry")

    def test_04_31_days_before_expiry(self):
        """TEST 4: 31 days before expiry results in NORMAL status."""
        today = datetime.date(2026, 9, 14)
        exp_date = (today + datetime.timedelta(days=31)).strftime("%Y-%m-%d")
        calc = calculate_batch_expiry(
            manufacture_date_str=None,
            expiry_date_str=exp_date,
            today_override=today
        )
        self.assertEqual(calc["expiry_status"], "NORMAL")
        self.assertEqual(calc["days_remaining"], 31)
        self.assertEqual(calc["days_remaining_text"], "31 days remaining")

    def test_05_30_days_before_expiry(self):
        """TEST 5: 30 days before expiry results in EXPIRING_SOON status."""
        today = datetime.date(2026, 9, 14)
        exp_date = (today + datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        calc = calculate_batch_expiry(
            manufacture_date_str=None,
            expiry_date_str=exp_date,
            today_override=today
        )
        self.assertEqual(calc["expiry_status"], "EXPIRING_SOON")
        self.assertEqual(calc["days_remaining"], 30)

    def test_06_expiry_date_is_today(self):
        """TEST 6: Expiry date is today formats clean 'Expires today' text."""
        today = datetime.date(2026, 9, 14)
        calc = calculate_batch_expiry(
            manufacture_date_str=None,
            expiry_date_str="2026-09-14",
            today_override=today
        )
        self.assertEqual(calc["expiry_status"], "EXPIRING_SOON")
        self.assertEqual(calc["days_remaining"], 0)
        self.assertEqual(calc["days_remaining_text"], "Expires today")

    def test_07_expiry_date_passed(self):
        """TEST 7: Expiry date passed results in EXPIRED status with formatted text."""
        today = datetime.date(2026, 9, 14)
        exp_date = (today - datetime.timedelta(days=4)).strftime("%Y-%m-%d")
        calc = calculate_batch_expiry(
            manufacture_date_str=None,
            expiry_date_str=exp_date,
            today_override=today
        )
        self.assertEqual(calc["expiry_status"], "EXPIRED")
        self.assertEqual(calc["days_remaining"], -4)
        self.assertEqual(calc["days_remaining_text"], "Expired by 4 days")

    def test_08_no_expiry_information(self):
        """TEST 8: Complete missing expiry info returns UNKNOWN."""
        calc = calculate_batch_expiry(manufacture_date_str=None, expiry_date_str=None)
        self.assertEqual(calc["expiry_status"], "UNKNOWN")

    def test_09_dashboard_counts_match_database(self):
        """TEST 9: Dashboard summary counts accurately match database records."""
        today = datetime.date(2026, 9, 14)
        b1 = Batch(batch_number="B01", product_id=self.chips_product.id, exp_date=(today + datetime.timedelta(days=60)).strftime("%Y-%m-%d"))
        b2 = Batch(batch_number="B02", product_id=self.chips_product.id, exp_date=(today + datetime.timedelta(days=15)).strftime("%Y-%m-%d"))
        b3 = Batch(batch_number="B03", product_id=self.chips_product.id, exp_date=(today - datetime.timedelta(days=5)).strftime("%Y-%m-%d"))
        b4 = Batch(batch_number="B04", product_id=self.milk_product.id, exp_date=None)
        self.db.add_all([b1, b2, b3, b4])
        self.db.commit()

        summary = update_all_batch_expiry_statuses(self.db, today_override=today)
        self.assertEqual(summary["NORMAL"], 1)
        self.assertEqual(summary["EXPIRING_SOON"], 1)
        self.assertEqual(summary["EXPIRED"], 1)
        self.assertEqual(summary["UNKNOWN"], 1)

    def test_10_expiring_soon_alert_created_once(self):
        """TEST 10: Expiring soon alert is created upon entering warning window."""
        today = datetime.date(2026, 9, 14)
        b = Batch(batch_number="B-ALERT-01", product_id=self.chips_product.id, exp_date=(today + datetime.timedelta(days=10)).strftime("%Y-%m-%d"))
        self.db.add(b)
        self.db.commit()

        update_all_batch_expiry_statuses(self.db, today_override=today)
        alerts = self.db.query(Alert).filter(Alert.batch_number == "B-ALERT-01").all()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].status, "WARNING")

    def test_11_refresh_dashboard_no_duplicate_alert(self):
        """TEST 11: Refreshing dashboard or re-evaluating does NOT create duplicate alerts."""
        today = datetime.date(2026, 9, 14)
        b = Batch(batch_number="B-ALERT-02", product_id=self.chips_product.id, exp_date=(today + datetime.timedelta(days=10)).strftime("%Y-%m-%d"))
        self.db.add(b)
        self.db.commit()

        # Run update multiple times
        update_all_batch_expiry_statuses(self.db, today_override=today)
        update_all_batch_expiry_statuses(self.db, today_override=today)
        update_all_batch_expiry_statuses(self.db, today_override=today)

        alerts = self.db.query(Alert).filter(Alert.batch_number == "B-ALERT-02").all()
        self.assertEqual(len(alerts), 1)

    def test_12_backend_restart_persistence(self):
        """TEST 12: Expiry fields remain persisted across database queries."""
        today = datetime.date(2026, 9, 14)
        b = Batch(
            batch_number="B-PERSIST-01",
            product_id=self.chips_product.id,
            mfg_date="2026-07-20",
            exp_date="2026-11-20",
            manufacture_date="2026-07-20",
            expiry_date="2026-11-20",
            expiry_rule_type="MONTHS_FROM_MANUFACTURE",
            expiry_duration_months=4,
            expiry_status="NORMAL"
        )
        self.db.add(b)
        self.db.commit()

        update_all_batch_expiry_statuses(self.db, today_override=today)
        query_batch = self.db.query(Batch).filter(Batch.batch_number == "B-PERSIST-01").first()
        self.assertEqual(query_batch.expiry_date, "2026-11-20")
        self.assertEqual(query_batch.expiry_rule_type, "MONTHS_FROM_MANUFACTURE")


    def test_13_create_real_batch(self):
        """TEST 13: Real batch creation populates expiry fields."""
        today = datetime.date(2026, 9, 14)
        new_b = Batch(
            batch_number="BAT-REAL-001",
            product_id=self.chips_product.id,
            mfg_date="2026-08-01",
            exp_date="2026-12-01",
            manufacture_date="2026-08-01",
            expiry_date="2026-12-01",
            expiry_status="NORMAL"
        )
        self.db.add(new_b)
        self.db.commit()

        update_all_batch_expiry_statuses(self.db, today_override=today)
        fetched = self.db.query(Batch).filter(Batch.batch_number == "BAT-REAL-001").first()
        self.assertEqual(fetched.expiry_status, "NORMAL")
        self.assertEqual(fetched.expiry_date, "2026-12-01")

    def test_14_real_inspection_saved_to_batch(self):
        """TEST 14: Real inspection linked to batch preserves batch relationship."""
        b = Batch(batch_number="BAT-INSP-01", product_id=self.chips_product.id, status="ACTIVE")
        self.db.add(b)
        self.db.commit()

        insp = Inspection(
            batch_id=b.id,
            expected_product="Chips Packet",
            detected_product="Chips Packet",
            packaging_condition="Normal Package",
            final_status="PASS",
            status_reasons="[]"
        )
        self.db.add(insp)
        self.db.commit()

        fetched_b = self.db.query(Batch).filter(Batch.id == b.id).first()
        self.assertEqual(len(fetched_b.inspections), 1)
        self.assertEqual(fetched_b.inspections[0].final_status, "PASS")

if __name__ == "__main__":
    unittest.main()
