from django.shortcuts import render
from django.db.models import Count

from ichange40.models import ExchangeRequest, PaymentSystemCurrency


def top_pairs(request):
    data = {}
    query = (
        ExchangeRequest.objects
        .filter(status=11)
        .select_related("from_payment_system_currency")
        .select_related("to_payment_system_currency")
        .select_related("from_payment_system_currency__currency")
        .select_related("to_payment_system_currency__currency")
        .select_related("from_payment_system_currency__payment_system")
        .select_related("to_payment_system_currency__payment_system")
    )
    for exchange_request in query:
        pair = "{} {}".format(
            exchange_request.from_payment_system_currency, exchange_request.to_payment_system_currency
        )
        if pair not in data:
            data[pair] = 0
        data[pair] += 1

    data = sorted(data.items(), key=lambda item: item[1])
    data.reverse()

    return render(request, "custom_admin/top_pairs.html", context={"data": dict(data)})
