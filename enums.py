import json


class Helper:
    mode = ""

    @classmethod
    def all(cls):
        """
        Get all consts
        :return: list
        """
        result = []
        for name in dir(cls):
            if not name.isupper():
                continue
            value = getattr(cls, name)
            result.append(value)

        return result


class Item:
    def __init__(self, value=None):
        self._value = value

    def __get__(self, instance, owner):
        return self._value

    def __set_name__(self, owner, name):
        if not name.isupper():
            raise NameError("Name for helper item must be in uppercase!")
        if not self._value:
            if hasattr(owner, 'mode'):
                self._value = HelperMode.apply(name, getattr(owner, "mode"))


class HelperMode(Helper):
    mode = "original"

    snake_case = 'snake_case'
    lowercase = 'lowercase'

    @classmethod
    def all(cls):
        return [cls.snake_case, cls.lowercase]

    @classmethod
    def _screaming_snake_case(cls, text):
        """
        Transform text to SCREAMING_SNAKE_CASE
        :param text:
        :return:
        """
        return text

    @classmethod
    def _snake_case(cls, text):
        """
        Transform text to snake cale (Based on SCREAMING_SNAKE_CASE)
        :param text:
        :return:
        """
        return cls._screaming_snake_case(text).lower()

    @classmethod
    def apply(cls, text, mode):
        """
        Apply mode for text
        :param text:
        :param mode:
        :return:
        """
        if mode == cls.snake_case:
            return cls._snake_case(text)
        if mode == cls.lowercase:
            return cls._snake_case(text).replace('_', '')
        return text


with open("fixture.json", encoding="utf-8") as f:
    data = {
        record["fields"]["name"]: record["fields"]["name"]
        for record in json.load(f) if "ichange40.PaymentType" == record["model"]
    }


class PaymentSystemType:
    bank = data["Банк"]
    crypto = data["Крипта"]
    eps = data["Эпс"]
    receipt = data["Чеки"]


class Currency(Helper):
    mode = HelperMode.lowercase

    RUB = Item()
    USD = Item()
    UAH = Item()
    EUR = Item()
