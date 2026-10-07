from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="Receipt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fn", models.CharField(max_length=16, verbose_name="ФН")),
                ("fd", models.CharField(max_length=10, verbose_name="ФД")),
                ("fp", models.CharField(max_length=10, verbose_name="ФП")),
                ("purchased_at", models.DateTimeField(verbose_name="Дата и время покупки")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12, verbose_name="Сумма")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "На проверке"),
                            ("accepted", "Принят"),
                            ("rejected", "Отклонен"),
                        ],
                        default="pending",
                        max_length=16,
                        verbose_name="Статус",
                    ),
                ),
                ("rejection_reason", models.TextField(blank=True, verbose_name="Причина отказа")),
                ("registered_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата регистрации")),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="receipts",
                        to="auth.user",
                        verbose_name="Пользователь",
                    ),
                ),
            ],
            options={
                "verbose_name": "Чек",
                "verbose_name_plural": "Чеки",
                "ordering": ["-registered_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="receipt",
            constraint=models.UniqueConstraint(fields=("fn", "fd", "fp"), name="unique_fiscal_receipt"),
        ),
    ]
