from django.db.models import Prefetch
from rest_framework import serializers

from . import utils
from ichange40 import models


class PaymentSystem(serializers.ModelSerializer):
    className = serializers.CharField(source="class_name")
    currencies = serializers.SerializerMethodField()
    icon_url = serializers.URLField()

    def get_currencies(self, payment_system: models.PaymentSystem):
        data = []

        for payment_system_currency in payment_system.paymentsystemcurrency_set.all():
            # print(payment_system_currency.balance)
            from_payment_system_currency = self.context.get("from_payment_system_currency")
            if from_payment_system_currency is not None:
                minimum = from_payment_system_currency.min
                to_payment_system_balance = utils.get_rate(
                    from_payment_system_currency, payment_system_currency
                )["to_payment_system_balance"]
                if minimum > to_payment_system_balance:
                    break

            record = {
                "id": payment_system_currency.currency.id,
                "name": payment_system_currency.currency.name.upper(),
                "toNotice": payment_system_currency.to_notice,
            }
            if self.context["no_input"] is False:
                record["inputs"] = InputSerializer(
                    payment_system_currency.to_inputs.all(), many=True, context=self.context
                ).data

                page_name = utils.page_name(self.context["from_payment_system_currency"], payment_system_currency)

                page_url = "{}_{}-{}_{}".format(
                    self.context["from_payment_system"].class_name,
                    self.context["from_currency"],
                    payment_system_currency.payment_system.class_name,
                    payment_system_currency.currency
                ).lower()

                record["page"] = {
                    "name": page_name,
                    "url": page_url,
                    "about": None,
                    "metaKeywords": None,
                    "metaDescription": None,
                    "rateFields": {
                        "fromValue": 1,
                        "fromCurrency": self.context["from_currency"].name,
                        "toValue": "215368.13",
                        "toCurrency": payment_system_currency.currency.name
                    },
                    "rateValues": {
                        "fromValue": 1,
                        "fromCurrency": self.context["from_currency"].name,
                        "toValue": "215368.13",
                        "toCurrency": payment_system_currency.currency.name
                    },
                    "balance": payment_system_currency.balance,
                    "amountInput": {
                        "id": "amount",
                        "name": "amount",
                        "label": "Сумма",
                        "placeholder": "Сумма",
                        "min": "0.02199013",
                        "max": "0.43980273"
                    },
                    "inputs": []
                }

            data.append(record)

        return data

    class Meta:
        model = models.PaymentSystem
        exclude = ["class_name", "icon"]


class Group(PaymentSystem):
    needFromField = serializers.BooleanField(default=True)
    isExternal = serializers.BooleanField(default=False)


class InputSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="name")
    name = serializers.SerializerMethodField()
    rules = serializers.SerializerMethodField()

    def get_rules(self, input_: models.Input):
        return [{rule.attribute: rule.value, "message": rule.message} for rule in input_.rules.all()]

    def get_name(self, input_: models.Input):
        return "{}[{}]".format(self.context["direction"], input_.name)  # Example: to[number]

    class Meta:
        model = models.Input
        fields = "__all__"


class FromPaymentSystemCurrency(serializers.ModelSerializer):
    id = serializers.IntegerField(source="currency.id")
    name = serializers.CharField(source="currency.name")
    fromNotice = serializers.CharField(source="from_notice")
    inputs = serializers.SerializerMethodField()
    directions = serializers.SerializerMethodField()

    def get_inputs(self, payment_system_currency: models.PaymentSystemCurrency):
        return InputSerializer(payment_system_currency.from_inputs.all(), many=True, context={"direction": "from"}).data

    def get_directions(self, value):
        query = (
            utils.payments_systems()
            .exclude(type=self.context["from_payment_system"].type)
        )
        return [
            record
            for record in Group(query, many=True, context=self.context).data if len(record["currencies"]) > 0
        ]

    class Meta:
        model = models.PaymentSystemCurrency
        exclude = ["from_notice"]


class GroupSerializer(serializers.ModelSerializer):
    className = serializers.CharField(source="class_name")
    fromNotice = serializers.SerializerMethodField()
    currencies = serializers.SerializerMethodField()

    def get_fromNotice(self, payment_system_currency: models.PaymentSystemCurrency):
        from_notice = self.context["from_currency_payment_system"].from_notice
        return str(from_notice) if from_notice is not None else None

    def get_currencies(self, payment_system: models.PaymentSystem):
        currencies_query = (
            self.context["from_currency_payment_system"].payment_system.paymentsystemcurrency_set
            .exclude(currency=self.context["from_currency"])
            .prefetch_related("from_inputs")
        )

        from_currencies_payment_system = (
            [self.context["from_currency_payment_system"]] +
            [payment_system_currency for payment_system_currency in currencies_query]
        )
        return FromPaymentSystemCurrency(from_currencies_payment_system, many=True, context=self.context).data

    class Meta:
        model = models.PaymentSystem
        exclude = ["class_name", "icon"]
