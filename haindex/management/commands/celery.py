# -*- coding: UTF-8 -*-
import shlex
import subprocess

from django.core.management.base import BaseCommand
from django.utils import autoreload


def restart_celery(*args, **kwargs):
    kill_worker_cmd = 'pkill -9 celery'
    subprocess.call(shlex.split(kill_worker_cmd))
    start_worker_cmd = 'celery worker -A haindex  -l info'
    subprocess.call(shlex.split(start_worker_cmd))


class Command(BaseCommand):
    """
    used to automatically reload celery workers in dev setup running docker-compose
    """
    def handle(self, *args, **options):
        self.stdout.write('Starting celery worker with autoreload...')
        autoreload.main(restart_celery, args=None, kwargs=None)
