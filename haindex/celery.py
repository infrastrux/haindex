# -*- coding: UTF-8 -*-
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'haindex.settings')

app = Celery('haindex')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
