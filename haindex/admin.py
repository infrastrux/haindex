# -*- coding: UTF-8 -*-
from django.contrib import admin

from haindex import models


@admin.register(models.Repository)
class RepositoryAdmin(admin.ModelAdmin):
    pass
