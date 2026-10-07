from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from receipts.forms import ReceiptForm, parse_qr
from receipts.models import Receipt

TZ = ZoneInfo("Europe/Moscow")


def aware(year, month, day, hour=12, minute=0):
    return timezone.make_aware(datetime(year, month, day, hour, minute), TZ)


@override_settings(
    PROMO_START_DATE=datetime(2026, 1, 1).date(),
    PROMO_END_DATE=datetime(2026, 3, 31).date(),
    TIME_ZONE="Europe/Moscow",
    MIN_RECEIPT_AMOUNT=1000,
)
class ReceiptValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("buyer", password="pass12345")
        self.other = User.objects.create_user("other", password="pass12345")

    def payload(self, **overrides):
        data = {
            "fn": "8710000100001234",
            "fd": "12345",
            "fp": "1234567890",
            "purchased_at": aware(2026, 2, 10, 15, 30),
            "amount": Decimal("1500.00"),
        }
        data.update(overrides)
        return data

    def test_accepts_valid_receipt(self):
        form = ReceiptForm(self.payload())
        self.assertTrue(form.is_valid(), form.errors)
        receipt = form.save(self.user)
        self.assertEqual(receipt.status, Receipt.Status.PENDING)

    def test_amount_below_minimum(self):
        form = ReceiptForm(self.payload(amount=Decimal("999.99")))
        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)

    def test_date_outside_promo(self):
        form = ReceiptForm(self.payload(purchased_at=aware(2025, 12, 31, 23, 59)))
        self.assertFalse(form.is_valid())
        self.assertIn("purchased_at", form.errors)

    def test_duplicate_is_rejected_with_message(self):
        first = ReceiptForm(self.payload())
        self.assertTrue(first.is_valid(), first.errors)
        first.save(self.user)
        second = ReceiptForm(self.payload())
        self.assertFalse(second.is_valid())
        self.assertIn("уже зарегистрирован", str(second.non_field_errors()))

    def test_rejected_receipt_cannot_be_resent(self):
        form = ReceiptForm(self.payload())
        form.is_valid()
        receipt = form.save(self.user)
        receipt.status = Receipt.Status.REJECTED
        receipt.rejection_reason = "не читается"
        receipt.save()
        again = ReceiptForm(self.payload())
        self.assertFalse(again.is_valid())

    def test_api_returns_only_own_receipts(self):
        own = ReceiptForm(self.payload())
        own.is_valid()
        own.save(self.user)
        foreign = ReceiptForm(self.payload(fn="8710000100009999", fd="9", fp="0987654321"))
        self.assertTrue(foreign.is_valid(), foreign.errors)
        foreign.save(self.other)
        self.client.login(username="buyer", password="pass12345")
        response = self.client.get(reverse("receipts_api") + "?user=2")
        self.assertEqual(response.status_code, 200)
        ids = [item["fn"] for item in response.json()["results"]]
        self.assertEqual(ids, ["8710000100001234"])

    def test_qr_parser(self):
        parsed = parse_qr("t=20260210T153000&s=1500.00&fn=8710000100001234&i=12345&fp=1234567890")
        self.assertEqual(parsed["fn"], "8710000100001234")
        self.assertEqual(parsed["i"], "12345")
