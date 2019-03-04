# -*- coding: UTF-8 -*-
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from haindex import models


def repository_update(modeladmin, request, queryset):
    for item in queryset:
        item.update()


repository_update.short_description = _('Update repositories from GitHub')


@admin.register(models.Repository)
class RepositoryAdmin(admin.ModelAdmin):
    actions = [repository_update]


@admin.register(models.RepositoryRelease)
class RepositoryReleaseAdmin(admin.ModelAdmin):
    pass
