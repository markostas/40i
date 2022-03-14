from django.contrib import admin

from ichange40.models import (
    PaymentSystem, Input, Notice, Rule, PaymentSystemCurrency, ExchangeRequest, is_payment_system_receipt, Setting
)
import enums


class PaymentSystemAdmin(admin.ModelAdmin):
    exclude = ["class_name"]


class PaymentSystemCurrencyAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "__str__",
        "balance",
        "min",
        "max",
        "commission"
    ]
    list_editable = list_display[2:]


class ExchangeRequestAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "sum",
        "need_send",
        "status",
        "timestamp"
    ]
    list_filter = ["status"]

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_exclude(self, request, exchange_request: ExchangeRequest = None):
        exclude = []
        if is_payment_system_receipt(exchange_request.to_payment_system_currency.payment_system) is False:
            exclude.append("for_user")
        if is_payment_system_receipt(exchange_request.from_payment_system_currency.payment_system) is False:
            exclude.append("from_user_data")

        return exclude


class SettingAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "vk_url",
        "inst_url",
        "tg_url",
        "support_url",
        "email_support",
        "email_partner",
    ]
    list_editable = list_display[1:]


admin.site.register(PaymentSystem, PaymentSystemAdmin)
admin.site.register(Input)
admin.site.register(Notice)
admin.site.register(Rule)
admin.site.register(PaymentSystemCurrency, PaymentSystemCurrencyAdmin)
admin.site.register(ExchangeRequest, ExchangeRequestAdmin)
admin.site.register(Setting, SettingAdmin)
