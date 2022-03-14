from django.db.models import Prefetch
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import datetime
from django.views import View
from django.utils.decorators import method_decorator

from .utils import JsonResponse
from . import serializers, utils
from ichange40.models import PaymentSystem, Currency, PaymentSystemCurrency, ExchangeRequest, Setting
import enums
from config import settings


def config(request, language: str):
    settings: Setting = Setting.objects.get()
    response = {
        "status": {
            "id": 10,
            "label": "Доступен"
        },
        "technicalWorkTimeout": 0,
        "breakText": "",
        "needAuthorize": 0,
        "infoMessages": [],
        "vk_url": settings.vk_url,
        "inst_url": settings.inst_url,
        "tg_url": settings.tg_url,
        "email_support": settings.email_support,
        "email_partner": settings.email_partner,
        "support_url": settings.support_url
    }
    data = request.GET.get("exchangeUrl")
    if data is not None:
        from_, to = data.split("-")  # Example qiwi_rub-binanceusd_busd

        from_payment_system = utils.payment_system_by_class_name(from_.split("_")[0])
        from_currency = utils.currency_by_name(from_.split("_")[1])

        to_payment = utils.payment_system_by_class_name(to.split("_")[0])
        to_currency = utils.currency_by_name(to.split("_")[1])

        response["exchangeAttributes"] = {
            "fromTypeId": from_payment_system.type.id,
            "fromPaymentSystemId": from_payment_system.id,
            "fromCurrencyId": from_currency.id,
            "toTypeId": to_payment.type.id,
            "toPaymentSystemId": to_payment.id,
            "toCurrencyId": to_currency.id,
            "exchangePriority": 1
        }

    return utils.api_response(response)


def dictionary(request, language: str):
    return utils.api_response(utils.read_dict())


def from_payment_systems(request, language: str):
    context = {"no_input": bool(request.GET.get("noInputs", 0)), "direction": "from"}
    serialized = serializers.PaymentSystem(utils.payments_systems(), many=True, context=context)

    return utils.api_response(serialized.data)


def group(request, language: str):
    from_payment_system_currency_query = (
        utils.payment_system_currencies()
        .filter(currency_id=request.GET["fromCurrencyId"], payment_system_id=request.GET["fromPaymentSystemId"])
    )

    from_currency_payment_system: PaymentSystemCurrency = (
        from_payment_system_currency_query
        .prefetch_related(
            Prefetch("payment_system__paymentsystemcurrency_set", queryset=from_payment_system_currency_query)
        )
    ).get()
    from_payment_system = from_currency_payment_system.payment_system

    context = {
        "no_input": bool(request.GET.get("noInputs", 0)),
        "from_payment_system": from_payment_system,
        "from_payment_system_currency": from_currency_payment_system,
        "from_currency_payment_system":  from_currency_payment_system,
        "from_currency": from_currency_payment_system.currency,
        "direction": "to",
    }
    return utils.api_response([serializers.GroupSerializer(from_payment_system, context=context).data])


def rate(
        request, language: str, from_payment_system: str, from_currency: str, to_payment_system: str, to_currency: str):
    from_payment_system_currency = utils.payment_system_currency(from_payment_system, from_currency)
    to_payment_system_currency = utils.payment_system_currency(to_payment_system, to_currency)

    response = utils.get_rate(from_payment_system_currency, to_payment_system_currency)

    maximum = min(
        [
            from_payment_system_currency.max,
            response["to_payment_system_balance"]
        ]
    )

    response = {
        "success": True,
        "data": {
            "hash": "X7TfeWwf3nKhG-rSlGqPdYKo50Zl6ra-mGv0sPD4DFuTgnqpwsauh3Xuw6O3o0UA",
            "hashLifetime": 515,
            "rateValues": {
                "fromValue": response["from_value"],
                "fromCurrency": from_currency.upper(),
                "toValue": response["to_value"],
                "toCurrency": to_currency.upper()
            },
            "rate": response["rate"],
            "operation": response["operation"],
            "fromPrecision": from_payment_system_currency.precision,
            "toPrecision": to_payment_system_currency.precision,
            "fromMultiple": 0,
            "toMultiple": 0,
            "amountInput": {
                "id": "amount",
                "name": "amount",
                "label": "Сумма",
                "placeholder": "Сумма",
                "min": from_payment_system_currency.min,
                "max": maximum
            },
            "isHaveExternalPaymentMethods": False
        },
        "status": 200
    }

    return JsonResponse(response)


def reserve(request, language: str):
    data = [
        {
            "paymentSystem": {
                "name": payment_system_currency.payment_system.name,
                "code": payment_system_currency.payment_system.name,
                "type": payment_system_currency.payment_system.type_id,
            },
            "currency": {
                "name": payment_system_currency.currency.name.upper(),
                "code": payment_system_currency.currency.name.upper(),
            },
            "amount": payment_system_currency.balance,
            "icon_url": payment_system_currency.payment_system.icon.url

        }
        for payment_system_currency in utils.payment_system_currencies()
    ]

    return utils.api_response(data)


@csrf_exempt
def exchange_process(
        request, language: str, from_payment_system: str, from_currency: str, to_payment_system: str, to_currency: str):
    from_payment_system_currency = utils.payment_system_currency(from_payment_system, from_currency)
    to_payment_system_currency = utils.payment_system_currency(to_payment_system, to_currency)

    data = []
    inputs = [
        {
            "direction": "from",
            "queryset": from_payment_system_currency.from_inputs.all(),
            "payment_system_currency": from_payment_system_currency
        },
        {
            "direction": "to",
            "queryset": to_payment_system_currency.to_inputs.all(),
            "payment_system_currency": to_payment_system_currency
        }
    ]

    for input_ in inputs:
        for input__ in input_["queryset"]:
            data.append(
                "{}_{}_{}".format(
                    input_["payment_system_currency"].payment_system,
                    input__.label,
                    request.POST["{}[{}]".format(input_["direction"], input__.name)]
                )
            )

    request: ExchangeRequest = ExchangeRequest.objects.create(
        from_payment_system_currency=from_payment_system_currency,
        to_payment_system_currency=to_payment_system_currency,
        sum=request.POST["amount"],
        data=data,
        need_send=utils.get_rate(
            from_payment_system_currency, to_payment_system_currency
        )["to_value"] * float(request.POST["amount"])
    )
    return utils.api_response({"code": request.code, "amount": request.sum})


def exchange_status(request, language: str, code: str):
    exchange_request = utils.get_exchange_request(code)
    statuses = {status: label for status, label in exchange_request.STATUS_CHOICES}

    all_values = [
        "BANK",
        "CRYPT",
        "PAYSYSTEM",
        "CHECK",
        "WIDGET"
    ]
    expired = exchange_request.timestamp + datetime.timedelta(seconds=settings.REQUEST_ON_CHANGE_TIME)

    if exchange_request.from_payment_system_currency.requisite is not None:
        outputs = [
            {
                "name": "number",
                "label": "Кошелёк",
                "value": exchange_request.from_payment_system_currency.requisite,
                "copyValue": exchange_request.from_payment_system_currency.requisite,
                "type": "text",
                "icon_url": exchange_request.from_payment_system_currency.payment_system.icon.url,
            },
            {
                "name": "amount",
                "label": "Сумма",
                "value": "{} {}".format(
                    exchange_request.sum, exchange_request.from_payment_system_currency.currency.name.upper()
                ),
                "copyValue": exchange_request.sum,
                "type": "text",
            }
        ]
        view_type = {"value": "CRYPT", "allValues": all_values}
    else:
        outputs = [
            {
                "name": "merchant",
                "label": "Перейти к оплате",
                "value": {
                    "paymentSystem": "Perfect Money e-Voucher",
                    "action": "/pay/form/f68295adb526350334d9cb5e770b9142/",
                    "method": "get",
                     "inputs": []
                },
                "copyValue": None,
                "type": "form"
            }
        ]
        view_type = {"value": "CHECK", "allValues": all_values}

    withdrawal_transactions = []
    if exchange_request.for_user is not None:
        withdrawal_transactions.append(
            {
                "label": None,
                "outputs": [
                    {
                        "name": "Чек",
                        "label": "Чек",
                        "value": exchange_request.for_user,
                        "copyValue": exchange_request.for_user,
                        "type": "text",
                    }
                ]
            }
        )

    data = {
            "id": exchange_request.pk,
            "code": exchange_request.code,
            "site": request.get_host(),
            "name": utils.page_name(
                exchange_request.from_payment_system_currency, exchange_request.to_payment_system_currency
            ),
            "endAt": expired,
            "createdAt": exchange_request.timestamp,
            "verification": {
                "isRequired": False,
            },
            "fromPaymentSystemType": view_type,
            "depositViewType": view_type,

            "fromPaymentSystem": exchange_request.from_payment_system_currency.payment_system.name,
            "fromPaymentSystemClassName": exchange_request.from_payment_system_currency.payment_system.class_name,
            "fromCurrency":  exchange_request.from_payment_system_currency.currency.name.upper(),
            "toPaymentSystemType": view_type,
            "toPaymentSystem": exchange_request.to_payment_system_currency.payment_system.name,
            "toPaymentSystemClassName": exchange_request.to_payment_system_currency.payment_system.class_name,
            "toCurrency": exchange_request.to_payment_system_currency.currency.name.upper(),
            "description": "",
            "paymentStatus": {
                "id": exchange_request.status,
                "label": statuses[exchange_request.status],
                "statuses": statuses
            },
            "requisites": {},
            "deposits": [
                {
                    "tabs": [
                        {
                            "label": None,
                            "outputs": outputs
                        }
                    ]
                }
            ],
            "withdrawalTransactions": withdrawal_transactions,
            "transactionLink": None,
            "timerEnd": expired,
            "canRepeat": False,
            "recountRequired": False
    }
    return utils.api_response(data)


@csrf_exempt
def set_paid(request, language: str, code: str):
    utils.exchange_request_set_status(code, 7)
    return utils.api_response({"code": code})


@method_decorator(csrf_exempt, name="dispatch")
class PaymentView(View):
    @staticmethod
    def get(request, language: str, code: str):
        exchange_request = utils.get_exchange_request(code)
        data = {
            "parentId": exchange_request.pk,
            "parentCode": exchange_request.code,
            "payment": {
                "amount": exchange_request.sum,
                "paymentSystemLabel": exchange_request.from_payment_system_currency.payment_system.name,
                "currencyLabel": exchange_request.from_payment_system_currency.currency.name.upper()
            },
            "paymentStatus": {
                "id": exchange_request.status,
            },
            "inputs": [
                {
                    "name": "code[]",
                    "label": "1234567890-1234567890123456",
                    "placeholder": "1234567890-1234567890123456",
                    "rules": [
                        {
                            "type": "string",
                            "message": "Значение поля должно быть строкой"
                        },
                        {
                            "required": True,
                            "message": "Поле обязательно для заполнения"
                        },
                    ]
                }
            ]
        }
        return utils.api_response(data)

    @staticmethod
    def post(request, language: str, code: str):
        utils.exchange_request_set_status(code, 7)
        exchange_request = utils.get_exchange_request(code)
        exchange_request.from_user_data = request.POST["code[0]"]
        exchange_request.save()
        return utils.api_response({})
