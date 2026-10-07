from django.urls import path

from . import views

urlpatterns = [
    path("", views.register_receipt, name="register"),
    path("cabinet/", views.cabinet, name="cabinet"),
    path("rules/", views.rules, name="rules"),
    path("profile/", views.profile, name="profile"),
    path("api/receipts/", views.receipts_api, name="receipts_api"),
]
