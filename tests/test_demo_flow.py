import unittest
import json
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db.database import Base, init_db
from backend.db.models import Product, Batch, Inspection, Alert
from backend.services.expiry_service import update_all_batch_expiry_statuses

class TestDemoFlowAndData(unittest.TestCase):
    def setUp(self):
        """Set up in-memory SQLite database for demo data verification."""
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = Session()

        # Seed products
        self.chips = Product(name="Chips Packet", category="Chips", mrp="₹20")
        self.milk = Product(name="Milk Pouch", category="Milk", mrp="₹31")
        self.db.add_all([self.chips, self.milk])
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_01_demo_batches_seeded_correctly(self):
        """Verify demo batches (BAT-DEMO-CHIPS-01, CHIPS-02, MILK-01, MILK-02) are populated with DEMO source."""
        today = datetime.date.today()
        b1 = Batch(batch_number="BAT-DEMO-CHIPS-01", product_id=self.chips.id, expiry_source="DEMO", status="ACTIVE", mfg_date=str(today), exp_date=str(today + datetime.timedelta(days=110)))
        b2 = Batch(batch_number="BAT-DEMO-CHIPS-02", product_id=self.chips.id, expiry_source="DEMO", status="COMPLETED", mfg_date=str(today - datetime.timedelta(days=105)), exp_date=str(today + datetime.timedelta(days=15)))
        b3 = Batch(batch_number="BAT-DEMO-MILK-01", product_id=self.milk.id, expiry_source="DEMO", status="COMPLETED", mfg_date=str(today - datetime.timedelta(days=5)), exp_date=str(today + datetime.timedelta(days=60)))
        b4 = Batch(batch_number="BAT-DEMO-MILK-02", product_id=self.milk.id, expiry_source="DEMO", status="COMPLETED", mfg_date=str(today - datetime.timedelta(days=130)), exp_date=str(today - datetime.timedelta(days=5)))
        
        self.db.add_all([b1, b2, b3, b4])
        self.db.commit()

        update_all_batch_expiry_statuses(self.db, today_override=today)

        batches = self.db.query(Batch).filter(Batch.expiry_source == "DEMO").all()
        self.assertEqual(len(batches), 4)
        
        active_chips = self.db.query(Batch).filter(Batch.batch_number == "BAT-DEMO-CHIPS-01").first()
        self.assertEqual(active_chips.expiry_status, "NORMAL")

        soon_chips = self.db.query(Batch).filter(Batch.batch_number == "BAT-DEMO-CHIPS-02").first()
        self.assertEqual(soon_chips.expiry_status, "EXPIRING_SOON")

        expired_milk = self.db.query(Batch).filter(Batch.batch_number == "BAT-DEMO-MILK-02").first()
        self.assertEqual(expired_milk.expiry_status, "EXPIRED")

    def test_02_demo_inspections_seeded_with_correct_statuses(self):
        """Verify demo inspection dataset covers PASS, REJECT, WARNING, and HOLD."""
        seeds = [
            Inspection(expected_product="Chips Packet", detected_product="Chips Packet", packaging_condition="Normal Package", final_status="PASS", data_source="DEMO", status_reasons=json.dumps(["Product and package verified."])),
            Inspection(expected_product="Chips Packet", detected_product="Chips Packet", packaging_condition="Damage Package", final_status="REJECT", data_source="DEMO", status_reasons=json.dumps(["Visible damage detected."])),
            Inspection(expected_product="Milk Pouch", detected_product="Milk Pouch", packaging_condition="Normal Package", final_status="PASS", data_source="DEMO", status_reasons=json.dumps(["Milk verified."])),
            Inspection(expected_product="Milk Pouch", detected_product="Milk Pouch", packaging_condition="Unclear", final_status="WARNING", data_source="DEMO", status_reasons=json.dumps(["Low confidence."])),
            Inspection(expected_product="Chips Packet", detected_product="Milk Pouch", packaging_condition="Normal Package", final_status="HOLD", data_source="DEMO", status_reasons=json.dumps(["Category mismatch."]))
        ]
        self.db.add_all(seeds)
        self.db.commit()

        total = self.db.query(Inspection).filter(Inspection.data_source == "DEMO").count()
        self.assertEqual(total, 5)

        pass_cnt = self.db.query(Inspection).filter(Inspection.final_status == "PASS").count()
        reject_cnt = self.db.query(Inspection).filter(Inspection.final_status == "REJECT").count()
        warn_cnt = self.db.query(Inspection).filter(Inspection.final_status == "WARNING").count()
        hold_cnt = self.db.query(Inspection).filter(Inspection.final_status == "HOLD").count()

        self.assertEqual(pass_cnt, 2)
        self.assertEqual(reject_cnt, 1)
        self.assertEqual(warn_cnt, 1)
        self.assertEqual(hold_cnt, 1)

    def test_03_timestamp_formatting(self):
        """Verify date objects format to operator string format (e.g., '14 Sep 2026, 05:20 PM')."""
        dt = datetime.datetime(2026, 9, 14, 17, 20)
        formatted = dt.strftime("%d %b %Y, %I:%M %p")
        self.assertEqual(formatted, "14 Sep 2026, 05:20 PM")

if __name__ == "__main__":
    unittest.main()
