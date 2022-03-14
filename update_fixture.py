import json
import pycoingecko

import enums

default_currencies = enums.Currency.all()


currencies = default_currencies + [coin["symbol"].lower() for coin in pycoingecko.CoinGeckoAPI().get_coins()]


model_name = "ichange40.Currency"

with open("fixture.json", encoding="utf-8") as f:
    data = [record for record in json.load(f) if model_name != record["model"]]


currencies_records = [
    {
        "model": model_name,
        "pk": id_,
        "fields": {
            "name": currency
        }
    }
    for id_, currency in enumerate(currencies, start=1)
]


with open("fixture.json", encoding="utf-8", mode="w") as f:
    data.extend(currencies_records)
    f.write(json.dumps(data, ensure_ascii=False, indent=4))
