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
    repository.update()


@celery_app.task(autoretry_for=(Exception,), retry_kwargs={'max_retries': 5}, retry_backoff=True)
def update_repository_stats(repository_id, *args, **kwargs):
    from haindex.models import Repository
    repository = Repository.objects.filter(id=repository_id).first()
    if not repository:
        return
    RepositoryUpdater(repository=repository).update_stats()


@celery_app.task(autoretry_for=(Exception,), retry_kwargs={'max_retries': 5}, retry_backoff=True)
def subscribe_repository(repository_id, *args, **kwargs):
    from haindex.models import Repository
    repository = Repository.objects.filter(id=repository_id).first()
    if not repository:
        return
    RepositoryUpdater(repository=repository).subscribe()


@celery_app.task(autoretry_for=(Exception,), retry_kwargs={'max_retries': 5}, retry_backoff=True)
def fan_out_update_repository_tasks(*args, **kwargs):
    from haindex.models import Repository
    for repository in Repository.objects.filter(user__usersocialauth__isnull=True):
        update_repository.apply_async([repository.id])
