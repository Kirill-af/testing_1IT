import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qs
from zoneinfo import ZoneInfo

from django import forms
from django.conf import settings
from django.db import IntegrityError
from django.utils import timezone

from .models import Receipt

QR_KEYS = ("t", "s", "fn", "i", "fp")


def parse_qr(raw: str) -> dict:
    text = (raw or "").strip()
    if not text:
        return {}
    if "://" in text or "?" in text:
        query = text.split("?", 1)[-1]
    else:
        query = text
    parsed = parse_qs(query, keep_blank_values=False)
    data = {}
    for key in QR_KEYS:
        values = parsed.get(key)
        if values:
            data[key] = values[0].strip()
    return data


def parse_qr_datetime(value: str) -> datetime | None:
    value = value.strip()
    for fmt in ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M"):
        try:
            naive = datetime.strptime(value, fmt)
        except ValueError:
            continue
        return timezone.make_aware(naive, ZoneInfo(settings.TIME_ZONE))
    return None


class ReceiptForm(forms.ModelForm):
    qr = forms.CharField(
        label="Строка из QR-кода",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "t=...&s=...&fn=...&i=...&fp=..."}),
    )

    class Meta:
        model = Receipt
        fields = ["fn", "fd", "fp", "purchased_at", "amount"]
        widgets = {
            "purchased_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "amount": forms.NumberInput(attrs={"min": "1000", "step": "0.01"}),
            "fn": forms.TextInput(attrs={"inputmode": "numeric", "maxlength": "16"}),
            "fd": forms.TextInput(attrs={"inputmode": "numeric", "maxlength": "10"}),
            "fp": forms.TextInput(attrs={"inputmode": "numeric", "maxlength": "10"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["purchased_at"].input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"]

    def clean_fn(self):
        return _digits(self.cleaned_data["fn"], "ФН", 16)

    def clean_fd(self):
        value = _digits(self.cleaned_data["fd"], "ФД", 10, exact=False)
        if not value:
            raise forms.ValidationError("Укажите ФД.")
        return value

    def clean_fp(self):
        return _digits(self.cleaned_data["fp"], "ФП", 10)

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount < Decimal(settings.MIN_RECEIPT_AMOUNT):
            raise forms.ValidationError(f"Сумма должна быть не меньше {settings.MIN_RECEIPT_AMOUNT} ₽.")
        return amount

    def clean_purchased_at(self):
        moment = self.cleaned_data["purchased_at"]
        if timezone.is_naive(moment):
            moment = timezone.make_aware(moment, ZoneInfo(settings.TIME_ZONE))
        start, end = promo_bounds()
        if moment < start or moment > end:
            raise forms.ValidationError(
                f"Дата покупки должна попадать в период акции: "
                f"{settings.PROMO_START_DATE:%d.%m.%Y} — {settings.PROMO_END_DATE:%d.%m.%Y}."
            )
        return moment

    def clean(self):
        cleaned = super().clean()
        fn, fd, fp = cleaned.get("fn"), cleaned.get("fd"), cleaned.get("fp")
        if fn and fd and fp and Receipt.objects.filter(fn=fn, fd=fd, fp=fp).exists():
            raise forms.ValidationError(
                "Этот чек уже зарегистрирован. Повторно отправить его нельзя, даже если его отклонили."
            )
        return cleaned

    def save(self, user, commit=True):
        receipt = super().save(commit=False)
        receipt.user = user
        receipt.status = Receipt.Status.PENDING
        receipt.rejection_reason = ""
        if commit:
            try:
                receipt.save()
            except IntegrityError as exc:
                raise forms.ValidationError(
                    "Этот чек уже зарегистрирован. Повторно отправить его нельзя, даже если его отклонили."
                ) from exc
        return receipt


def promo_bounds():
    tz = ZoneInfo(settings.TIME_ZONE)
    start = datetime.combine(settings.PROMO_START_DATE, datetime.min.time(), tzinfo=tz)
    end = datetime.combine(settings.PROMO_END_DATE, datetime.max.time().replace(microsecond=0), tzinfo=tz)
    return start, end


def _digits(value: str, label: str, length: int, exact: bool = True) -> str:
    value = re.sub(r"\s+", "", value or "")
    if not value.isdigit():
        raise forms.ValidationError(f"{label} должен состоять только из цифр.")
    if exact and len(value) != length:
        raise forms.ValidationError(f"{label} должен содержать {length} цифр.")
    if not exact and len(value) > length:
        raise forms.ValidationError(f"{label} не длиннее {length} цифр.")
    return value


def apply_qr(data) -> dict:
    """Fill missing form fields from a QR payload. Existing values win."""
    result = data.dict() if hasattr(data, "dict") else dict(data)
    parsed = parse_qr(result.get("qr", ""))
    if parsed.get("fn") and not result.get("fn"):
        result["fn"] = parsed["fn"]
    if parsed.get("i") and not result.get("fd"):
        result["fd"] = parsed["i"]
    if parsed.get("fp") and not result.get("fp"):
        result["fp"] = parsed["fp"]
    if parsed.get("s") and not result.get("amount"):
        try:
            result["amount"] = str(Decimal(parsed["s"].replace(",", ".")))
        except InvalidOperation:
            pass
    if parsed.get("t") and not result.get("purchased_at"):
        moment = parse_qr_datetime(parsed["t"])
        if moment:
            local = moment.astimezone(ZoneInfo(settings.TIME_ZONE))
            result["purchased_at"] = local.strftime("%Y-%m-%dT%H:%M")
    return result
