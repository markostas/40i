import transliterate
from django.db import models
import wrapcache
import pycoingecko
from django import forms
import faker

from . import fields
import enums


def is_payment_system_receipt(payment_system):
    return payment_system.type.name == enums.PaymentSystemType.receipt


def gen_code():
    return faker.Faker().password(length=30, special_chars=False)


@wrapcache.wrapcache(timeout=60)
def get_coins():
    return pycoingecko.CoinGeckoAPI().get_coins()


class PaymentSystemType(models.Model):
    name = models.CharField(unique=True, max_length=255)

    def __str__(self):
        return self.name


class Notice(models.Model):
    text = models.TextField(unique=True)

    def __str__(self):
        return self.text


class Rule(models.Model):
    name = models.CharField(max_length=255)
    attribute = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
    message = models.TextField()

    def __str__(self):
        return self.name


class Input(models.Model):
    name = models.CharField(max_length=255)
    label = models.CharField(max_length=255)
    placeholder = models.CharField(max_length=255)
    rules = models.ManyToManyField(Rule)

    def __str__(self):
        return self.label


class Currency(models.Model):
    name = fields.UpperCaseCharField(unique=True, max_length=255)

    def __str__(self):
        return self.name


class PaymentSystemCurrency(models.Model):
    payment_system: "PaymentSystem" = models.ForeignKey("PaymentSystem", on_delete=models.PROTECT)
    currency = models.ForeignKey("Currency", on_delete=models.PROTECT)

    from_inputs = models.ManyToManyField(Input, blank=True)
    to_inputs = models.ManyToManyField(Input, blank=True, related_name="toinputs")

    from_notice = models.ForeignKey(Notice, null=True, blank=True, on_delete=models.PROTECT)
    to_notice = models.ForeignKey(Notice, related_name="tonotice", null=True, blank=True, on_delete=models.PROTECT)

    balance = models.FloatField()
    min = models.FloatField(help_text="Минимальная сумма обмена")
    max = models.FloatField(help_text="Максимальная сумма обмена")

    precision = models.PositiveIntegerField(help_text="Знаков после запятой")

    requisite = models.CharField(blank=True, null=True, max_length=255)

    commission = models.FloatField(default=0, help_text="Комиссия")

    def __str__(self):
        return "{} - {}".format(self.payment_system, self.currency)

    class Meta:
        unique_together = [["payment_system", "currency"]]


class PaymentSystem(models.Model):
    name = models.CharField(unique=True, max_length=255)
    class_name = models.CharField(unique=True, max_length=255, null=True)
    icon = models.FileField(upload_to="payments_icons/")
    type = models.ForeignKey("PaymentType", on_delete=models.PROTECT)

    @property
    def icon_url(self):
        return self.icon.url

    def clean(self):
        self.class_name = transliterate.translit(
            str(self.name), language_code="ru", reversed=True
        ).replace(" ", "").replace("-", "_").lower().title()

        if self.type.name == enums.PaymentSystemType.crypto:
            for coin in get_coins():
                if self.name.lower() == coin["id"]:
                    break
            else:
                raise forms.ValidationError(
                    message="Введённая крипта не поддерживается",
                    code="invalid",
                )

        return super().clean()

    def __str__(self):
        return self.name


class PaymentType(models.Model):
    name = models.CharField(unique=True, max_length=255)

    def __str__(self):
        return self.name


class ExchangeRequest(models.Model):
    STATUS_CHOICES = [
        [4, "Не оплачена"],
        [7, "Проверяем оплату"],
        [9, "Новая"],
        [11, "Оплачена"]
    ]
    from_payment_system_currency: PaymentSystemCurrency = models.ForeignKey(
        PaymentSystemCurrency, on_delete=models.PROTECT
    )
    to_payment_system_currency: PaymentSystemCurrency = models.ForeignKey(
        PaymentSystemCurrency, related_name="topaymentsystemcurrency", on_delete=models.PROTECT
    )
    sum = models.FloatField(help_text="Сколько должны получить вы")
    need_send = models.FloatField(help_text="Сколько получит юзер")
    data = models.JSONField(blank=True, default=dict)
    from_user_data = models.CharField(null=True, max_length=255, help_text="Информация от пользователя")
    for_user = models.CharField(null=True, max_length=255, help_text="Для юзера")
    code = models.CharField(unique=True, max_length=30, default=gen_code)
    status = models.PositiveIntegerField(default=9, choices=STATUS_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if is_payment_system_receipt(self.to_payment_system_currency.payment_system) and self.for_user is None:
            raise forms.ValidationError(
                message="Заполните поле for_user", code="invalid",
                )

        return super().clean()


class Setting(models.Model):
    vk_url = models.URLField()
    inst_url = models.URLField()
    tg_url = models.URLField()
    support_url = models.URLField()
    email_support = models.EmailField()
    email_partner = models.EmailField()
