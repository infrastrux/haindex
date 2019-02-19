# -*- coding: UTF-8 -*-
from celery.utils.log import get_task_logger

from haindex.common.util.updater import RepositoryUpdater
from haindex import celery_app

logger = get_task_logger(__name__)


@celery_app.task(autoretry_for=(Exception,), retry_kwargs={'max_retries': 5}, retry_backoff=True)
def update_repository(repository_id, *args, **kwargs):
    from haindex.models import Repository
    repository = Repository.objects.filter(id=repository_id).first()
    if not repository:
        return
    RepositoryUpdater().update(repository=repository)


@celery_app.task(autoretry_for=(Exception,), retry_kwargs={'max_retries': 5}, retry_backoff=True)
def update_repository_stats(repository_id, *args, **kwargs):
    from haindex.models import Repository
    repository = Repository.objects.filter(id=repository_id).first()
    if not repository:
        return
    RepositoryUpdater().update_stats(repository=repository)


@celery_app.task(autoretry_for=(Exception,), retry_kwargs={'max_retries': 5}, retry_backoff=True)
def subscribe_repository(repository_id, *args, **kwargs):
    from haindex.models import Repository
    repository = Repository.objects.filter(id=repository_id).first()
    if not repository:
        return
    RepositoryUpdater().subscribe(repository=repository)
