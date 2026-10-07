from django.conf import settings


def promo(request):
    return {
        "promo_start": settings.PROMO_START_DATE,
        "promo_end": settings.PROMO_END_DATE,
        "min_amount": settings.MIN_RECEIPT_AMOUNT,
    }
