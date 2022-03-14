import os
import json
import functools
from wrapcache import wrapcache
import typing
import requests
from django.http import JsonResponse as JsonResponse_
from django.http.response import DjangoJSONEncoder as DjangoJSONEncoder_
import datetime

from config import settings
from ichange40.models import PaymentSystem, Currency, get_coins, PaymentSystemCurrency, ExchangeRequest
import enums


class DjangoJSONEncoder(DjangoJSONEncoder_):
    """
    JSONEncoder subclass that knows how to encode date/time, decimal types, and
    UUIDs.
    """
    def default(self, o):
        # See "Date Time String Format" in the ECMA-262 specification.
        if isinstance(o, datetime.datetime):
            return str(o)

        super().default(o)


class JsonResponse(JsonResponse_):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args, **kwargs, json_dumps_params={"ensure_ascii": False, "indent": 4}, encoder=DjangoJSONEncoder
        )


def api_response(data: typing.Union[list, dict]):
    return JsonResponse({"success": True, "data": data, "status": 200}, safe=False)


def payment_system_by_class_name(class_name: str) -> PaymentSystem:
    return PaymentSystem.objects.filter(class_name__iexact=class_name).first()


def currency_by_name(name: str) -> Currency:
    return Currency.objects.filter(name__iexact=name).first()


def payment_system_currency(payment_system_name: str, currency_name: str) -> PaymentSystemCurrency:
    return PaymentSystemCurrency.objects.get(
        payment_system__class_name__iexact=payment_system_name, currency__name__iexact=currency_name
    )


@functools.lru_cache()
def read_dict():
    with open(os.path.join(settings.BASE_DIR, "api", "dict.json"), encoding="utf-8") as f:
        data = json.loads(f.read())

    return data


def payments_systems():
    query = (
        PaymentSystem.objects.all()
        .order_by("id")
        .prefetch_related("paymentsystemcurrency_set__currency")
        .prefetch_related("paymentsystemcurrency_set")
        .prefetch_related("paymentsystemcurrency_set__to_inputs")
        .prefetch_related("paymentsystemcurrency_set__to_inputs__rules")
    )
    return query


@wrapcache(timeout=60 * 60 * 1)  # Кешируется на час
def get_coingecko_by_symbol(symbol: str) -> dict:
    return {coin["symbol"]: coin for coin in get_coins()}[symbol.lower()]


@wrapcache(timeout=60 * 60 * 1)  # Кешируется на час
def get_coingate_rate(from_currency, to_currency) -> float:
    return float(
        requests.get("https://api.coingate.com/v2/rates/merchant/{}/{}".format(from_currency, to_currency)).text
    )


@wrapcache(timeout=60 * 10)
def get_crypto_rate(fiat_currency, crypto_currency) -> float:
    return get_coingecko_by_symbol(crypto_currency)["market_data"]["current_price"][fiat_currency]


def payment_system_currencies():
    return PaymentSystemCurrency.objects.select_related("currency").select_related("payment_system")


def get_num_or_one(num):
    return max([num, 1])


def get_rate(from_payment_system_currency: PaymentSystemCurrency, to_payment_system_currency: PaymentSystemCurrency):
    fiat = enums.Currency.all()

    if from_payment_system_currency.currency.name in fiat and to_payment_system_currency.currency.name in fiat:
        if from_payment_system_currency.currency.name == to_payment_system_currency.currency.name:
            from_value = 1
            to_value = 1
            operation = "MUL"
            crypto_rate = to_value
            to_payment_system_balance = to_payment_system_currency.balance
        else:
            from_value = get_num_or_one(
                get_coingate_rate(to_payment_system_currency.currency, from_payment_system_currency.currency)
            )
            to_value = get_num_or_one(
                get_coingate_rate(from_payment_system_currency.currency, to_payment_system_currency.currency)
            )

            operation = "MUL" if from_value == 1 else "DIV"
            crypto_rate = to_value if from_value == 1 else from_value
            to_payment_system_balance = to_payment_system_currency.balance / crypto_rate

    elif from_payment_system_currency.currency.name in fiat or to_payment_system_currency.currency.name in fiat:
        if from_payment_system_currency.currency.name in enums.Currency.all():
            from_value = get_num_or_one(
                get_crypto_rate(from_payment_system_currency.currency.name, to_payment_system_currency.currency.name)
            )
            to_value = 1
            crypto_rate = to_value if from_value == 1 else from_value
            to_payment_system_balance = to_payment_system_currency.balance * crypto_rate
        else:
            from_value = 1
            to_value = get_num_or_one(
                get_crypto_rate(to_payment_system_currency.currency.name, from_payment_system_currency.currency.name)
            )
            crypto_rate = to_value if from_value == 1 else from_value
            to_payment_system_balance = to_payment_system_currency.balance / crypto_rate

        operation = "MUL" if from_value == 1 else "DIV"
    else:
        raise ValueError

    to_payment_system_balance = round(
        to_payment_system_balance, from_payment_system_currency.precision
    )

    if 1 == to_value:
        if 1 == from_value:
            rate = round(crypto_rate / 100 * (100 - to_payment_system_currency.commission), 8)
        else:
            rate = round(crypto_rate / 100 * (100 + to_payment_system_currency.commission), 8)

        from_value = round(from_value / 100 * (100 + to_payment_system_currency.commission), 8)
    else:
        to_value = round(to_value / 100 * (100 - to_payment_system_currency.commission), 8)
        rate = round(crypto_rate / 100 * (100 - to_payment_system_currency.commission), 8)

    return {
        "from_value": from_value,
        "to_value": to_value,
        "operation": operation,
        "to_payment_system_balance": to_payment_system_balance,
        "rate": rate,
    }


def page_name(
        from_payment_system_currency: PaymentSystemCurrency, to_payment_system_currency: PaymentSystemCurrency) -> str:
    return "{} {} - {} {}".format(
        from_payment_system_currency.payment_system.name,
        from_payment_system_currency.currency.name.upper(),
        to_payment_system_currency.payment_system.name,
        to_payment_system_currency.currency.name.upper(),
    )


def get_exchange_request(code: str) -> ExchangeRequest:
    return (
        ExchangeRequest.objects
        .select_related("from_payment_system_currency")
        .select_related("to_payment_system_currency")
        .get(code=code)
    )


def exchange_request_set_status(code: str, status: int):
    exchange_request = get_exchange_request(code)
    exchange_request.status = status
    exchange_request.save()
