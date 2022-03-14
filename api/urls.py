from django.urls import path

from . import views


urlpatterns = [
    path("exchange/config", views.config),
    path("exchange/dictionary", views.dictionary),
    path("exchange/from-payment-systems", views.from_payment_systems),
    path("exchange/group", views.group),
    path(
        "exchange/rate/<str:from_payment_system>_<str:from_currency>-<str:to_payment_system>_<str:to_currency>",
        views.rate
    ),
    path("exchange/reserve", views.reserve),
    path(
        "exchange/process/<str:from_payment_system>_<str:from_currency>-<str:to_payment_system>_<str:to_currency>",
        views.exchange_process
    ),
    path("exchange/status/<str:code>", views.exchange_status),
    path("exchange/set-paid/<str:code>", views.set_paid),
    path("exchange/payment/<str:code>", views.PaymentView.as_view())
]
