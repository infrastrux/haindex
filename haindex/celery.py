# -*- coding: UTF-8 -*-
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'haindex.settings')

app = Celery('haindex')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.CELERYBEAT_SCHEDULE.update({
    'update_repositories': {
        'task': 'haindex.tasks.fan_out_update_repository_tasks',
        'schedule': crontab(day_of_month='*', hour=3, minute=0),
    },
})
