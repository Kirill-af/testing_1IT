import csv

from django import forms
from django.contrib import admin
from django.http import HttpResponse

from .models import Receipt


class ReceiptAdminForm(forms.ModelForm):
    class Meta:
        model = Receipt
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        reason = (cleaned.get("rejection_reason") or "").strip()
        if status == Receipt.Status.REJECTED and not reason:
            self.add_error("rejection_reason", "Укажите причину отказа.")
        if status and status != Receipt.Status.REJECTED:
            cleaned["rejection_reason"] = ""
        return cleaned


def export_accepted_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="accepted_receipts.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(
        ["id", "user", "fn", "fd", "fp", "purchased_at", "amount", "registered_at"]
    )
    for receipt in queryset.filter(status=Receipt.Status.ACCEPTED).select_related("user"):
        writer.writerow(
            [
                receipt.pk,
                receipt.user.username,
                receipt.fn,
                receipt.fd,
                receipt.fp,
                receipt.purchased_at.isoformat(),
                receipt.amount,
                receipt.registered_at.isoformat(),
            ]
        )
    return response


export_accepted_csv.short_description = "Выгрузить принятые чеки в CSV"


class ReceiptAdmin(admin.ModelAdmin):
    form = ReceiptAdminForm
    list_display = (
        "open_receipt",
        "id",
        "user",
        "fn",
        "fd",
        "fp",
        "purchased_at",
        "amount",
        "status",
        "registered_at",
    )
    list_display_links = ("open_receipt",)

    @admin.display(description="Действие")
    def open_receipt(self, obj):
        return "Изменить статус"
    list_filter = ("status",)
    search_fields = ("fn", "fd", "fp", "user__username")
    readonly_fields = ("registered_at",)
    actions = [export_accepted_csv]


admin.site.register(Receipt, ReceiptAdmin)
admin.site.site_header = "Чек на удачу"
