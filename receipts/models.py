from django.contrib.auth.models import User
from django.db import models


class Receipt(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "На проверке"
        ACCEPTED = "accepted", "Принят"
        REJECTED = "rejected", "Отклонен"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="receipts", verbose_name="Пользователь")
    fn = models.CharField("ФН", max_length=16)
    fd = models.CharField("ФД", max_length=10)
    fp = models.CharField("ФП", max_length=10)
    purchased_at = models.DateTimeField("Дата и время покупки")
    amount = models.DecimalField("Сумма", max_digits=12, decimal_places=2)
    status = models.CharField(
        "Статус",
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    rejection_reason = models.TextField("Причина отказа", blank=True)
    registered_at = models.DateTimeField("Дата регистрации", auto_now_add=True)

    class Meta:
        verbose_name = "Чек"
        verbose_name_plural = "Чеки"
        ordering = ["-registered_at"]
        constraints = [
            models.UniqueConstraint(fields=["fn", "fd", "fp"], name="unique_fiscal_receipt"),
        ]

    def __str__(self):
        return f"{self.fn}/{self.fd}/{self.fp}"
