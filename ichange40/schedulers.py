import time
import datetime
from django.utils.timezone import make_aware
from apscheduler.schedulers.background import BackgroundScheduler

from config import settings
from ichange40 import urls
from ichange40.models import ExchangeRequest


def close_request_on_change():
    query = (
        ExchangeRequest.objects
        .filter(
            status=9,
            timestamp__lte=make_aware(datetime.datetime.fromtimestamp(time.time() - settings.REQUEST_ON_CHANGE_TIME))
        )
    )
    query.update(status=4)


def setup():
    scheduler = BackgroundScheduler({'apscheduler.timezone': 'Europe/Moscow'})
    scheduler.add_job(close_request_on_change, "interval", seconds=30)
    scheduler.start()
