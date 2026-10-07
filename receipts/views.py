from django import forms
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods

from .forms import ReceiptForm, apply_qr
from .models import Receipt


STATUS_UI = {
    Receipt.Status.PENDING: "В обработке",
    Receipt.Status.ACCEPTED: "Обработан",
    Receipt.Status.REJECTED: "Ошибка",
}


def _payload(receipt: Receipt) -> dict:
    return {
        "id": receipt.pk,
        "fn": receipt.fn,
        "fd": receipt.fd,
        "fp": receipt.fp,
        "purchased_at": receipt.purchased_at.isoformat(),
        "amount": str(receipt.amount),
        "status": receipt.status,
        "status_label": STATUS_UI.get(receipt.status, receipt.get_status_display()),
        "rejection_reason": receipt.rejection_reason,
        "registered_at": receipt.registered_at.isoformat(),
    }


@login_required
@require_http_methods(["GET", "POST"])
def register_receipt(request):
    if request.method == "POST":
        data = apply_qr(request.POST)
        form = ReceiptForm(data)
        if form.is_valid():
            try:
                receipt = form.save(user=request.user)
            except forms.ValidationError as exc:
                return JsonResponse({"ok": False, "errors": {"__all__": exc.messages}}, status=400)
            return JsonResponse({"ok": True, "receipt": _payload(receipt)})
        errors = {field: [str(err) for err in messages] for field, messages in form.errors.items()}
        return JsonResponse({"ok": False, "errors": errors}, status=400)
    return render(request, "receipts/register.html", {"form": ReceiptForm()})


@login_required
def cabinet(request):
    qs = Receipt.objects.filter(user=request.user)
    page = Paginator(qs, 10).get_page(request.GET.get("page"))
    return render(
        request,
        "receipts/cabinet.html",
        {"page_obj": page, "receipt_count": qs.count()},
    )


@login_required
def rules(request):
    return render(request, "receipts/rules.html")


@login_required
def profile(request):
    return render(request, "receipts/profile.html")


@login_required
@require_GET
def receipts_api(request):
    qs = Receipt.objects.filter(user=request.user)
    return JsonResponse({"results": [_payload(item) for item in qs]})
