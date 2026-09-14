import unittest
import datetime as dt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.db.database import Base, get_db
from backend.db.models import Product, Batch, Alert
from backend.services.expiry_service import update_all_batch_expiry_statuses, calculate_batch_expiry

class TestStep21ActiveBatchAndExpiry(unittest.TestCase):
    def setUp(self):
        """Set up an in-memory SQLite database and test client."""
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        TestingSessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = TestingSessionLocal()

        def override_get_db():
            try:
                yield self.db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

        # Seed products
        self.chips_prod = Product(name="Test Chips Packet", brand="Lay's", category="Chips", mrp="₹20")
        self.milk_prod = Product(name="Test Milk Pouch", brand="Pure Dairy", category="Milk", mrp="₹31")
        self.db.add_all([self.chips_prod, self.milk_prod])
        self.db.commit()

        # Seed demo expiry batches
        today = dt.date.today()
        self.b1 = Batch(
            batch_number="DEMO-EXP-001",
            product_id=self.chips_prod.id,
            manufacture_date=(today - dt.timedelta(days=10)).strftime("%Y-%m-%d"),
            expiry_date=(today + dt.timedelta(days=90)).strftime("%Y-%m-%d"),
            expiry_rule_type="MONTHS_FROM_MANUFACTURE",
            expiry_duration_months=4,
            expiry_source="DEMO",
            expiry_status="NORMAL",
            status="ACTIVE"
        )
        self.b2 = Batch(
            batch_number="DEMO-EXP-002",
            product_id=self.milk_prod.id,
            manufacture_date=(today - dt.timedelta(days=5)).strftime("%Y-%m-%d"),
            expiry_date=(today + dt.timedelta(days=15)).strftime("%Y-%m-%d"),
            expiry_rule_type="EXPLICIT_DATE",
            expiry_source="DEMO",
            expiry_status="EXPIRING_SOON",
            status="INACTIVE"
        )
        self.b3 = Batch(
            batch_number="DEMO-EXP-003",
            product_id=self.chips_prod.id,
            manufacture_date=(today - dt.timedelta(days=130)).strftime("%Y-%m-%d"),
            expiry_date=(today - dt.timedelta(days=10)).strftime("%Y-%m-%d"),
            expiry_rule_type="EXPLICIT_DATE",
            expiry_source="DEMO",
            expiry_status="EXPIRED",
            status="INACTIVE"
        )
        self.b4 = Batch(
            batch_number="DEMO-EXP-004",
            product_id=self.milk_prod.id,
            manufacture_date=None,
            expiry_date=None,
            expiry_rule_type="EXPLICIT_DATE",
            expiry_source="DEMO",
            expiry_status="UNKNOWN",
            status="INACTIVE"
        )
        self.db.add_all([self.b1, self.b2, self.b3, self.b4])
        self.db.commit()

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()

    def test_01_single_active_batch_activation(self):
        """TEST 1: Activating Batch B sets Batch A to INACTIVE automatically."""
        # Verify b1 is active, b2 is inactive initially
        self.assertEqual(self.b1.status, "ACTIVE")
        self.assertEqual(self.b2.status, "INACTIVE")

        # Activate b2 via API endpoint
        response = self.client.put(f"/api/batches/{self.b2.id}/activate")
        self.assertEqual(response.status_code, 200)

        # Refresh objects
        self.db.refresh(self.b1)
        self.db.refresh(self.b2)

        # Only b2 must be active
        self.assertEqual(self.b1.status, "INACTIVE")
        self.assertEqual(self.b2.status, "ACTIVE")

        # Count total active batches in DB
        active_count = self.db.query(Batch).filter(Batch.status == "ACTIVE").count()
        self.assertEqual(active_count, 1)

    def test_02_create_new_batch_deactivates_previous_active(self):
        """TEST 2: Creating a new active batch deactivates existing active batches."""
        today = dt.date.today()
        new_batch_data = {
            "batch_number": "BAT-TEST-NEW-01",
            "product_id": self.chips_prod.id,
            "manufacture_date": today.strftime("%Y-%m-%d"),
            "expiry_date": (today + dt.timedelta(days=60)).strftime("%Y-%m-%d"),
            "expiry_rule_type": "EXPLICIT_DATE",
            "expiry_source": "USER_MANUAL"
        }
        response = self.client.post("/api/batches", json=new_batch_data)
        self.assertEqual(response.status_code, 200)

        # Check database: newly created batch is ACTIVE, b1 is INACTIVE
        self.db.refresh(self.b1)
        self.assertEqual(self.b1.status, "INACTIVE")

        active_batches = self.db.query(Batch).filter(Batch.status == "ACTIVE").all()
        self.assertEqual(len(active_batches), 1)
        self.assertEqual(active_batches[0].batch_number, "BAT-TEST-NEW-01")

    def test_03_relative_system_date_demo_expiry_statuses(self):
        """TEST 3: Demo expiry batches calculate correct statuses relative to current date."""
        today = dt.date.today()

        calc1 = calculate_batch_expiry(self.b1.manufacture_date, self.b1.expiry_date, today_override=today)
        self.assertEqual(calc1["expiry_status"], "NORMAL")
        self.assertGreater(calc1["days_remaining"], 30)

        calc2 = calculate_batch_expiry(self.b2.manufacture_date, self.b2.expiry_date, today_override=today)
        self.assertEqual(calc2["expiry_status"], "EXPIRING_SOON")
        self.assertLessEqual(calc2["days_remaining"], 30)
        self.assertGreaterEqual(calc2["days_remaining"], 0)

        calc3 = calculate_batch_expiry(self.b3.manufacture_date, self.b3.expiry_date, today_override=today)
        self.assertEqual(calc3["expiry_status"], "EXPIRED")
        self.assertLess(calc3["days_remaining"], 0)

        calc4 = calculate_batch_expiry(self.b4.manufacture_date, self.b4.expiry_date, today_override=today)
        self.assertEqual(calc4["expiry_status"], "UNKNOWN")

    def test_04_expiry_alerts_creation_and_deduplication(self):
        """TEST 4: update_all_batch_expiry_statuses creates EXPIRING_SOON and EXPIRED alerts cleanly without duplicates."""
        update_all_batch_expiry_statuses(self.db)
        
        # Verify alerts created for DEMO-EXP-002 (EXPIRING_SOON) and DEMO-EXP-003 (EXPIRED)
        alerts = self.db.query(Alert).all()
        alert_batch_numbers = [a.batch_number for a in alerts]
        self.assertIn("DEMO-EXP-002", alert_batch_numbers)
        self.assertIn("DEMO-EXP-003", alert_batch_numbers)

        # Run update again to test deduplication
        count_before = len(alerts)
        update_all_batch_expiry_statuses(self.db)
        count_after = self.db.query(Alert).count()
        self.assertEqual(count_before, count_after)

if __name__ == "__main__":
    unittest.main()
