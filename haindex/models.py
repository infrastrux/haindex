# -*- coding: UTF-8 -*-
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django_extensions.db.models import TimeStampedModel
from model_utils import Choices


class Repository(TimeStampedModel):
    TYPE_LOVELACE_ID = 1
    TYPE_LOVELACE = 'lovelace'
    TYPE_COMPONENT_ID = 2
    TYPE_COMPONENT = 'component'
    TYPE_CHOICES = Choices(
        (TYPE_LOVELACE_ID, TYPE_LOVELACE, _('Lovelace plugin')),
        (TYPE_COMPONENT_ID, TYPE_COMPONENT, _('Custom component')),
    )

    github_user = models.CharField(max_length=100, verbose_name=_('GitHub user'))
    github_repo = models.CharField(max_length=100, verbose_name=_('GitHub repo'))
    type = models.IntegerField(choices=TYPE_CHOICES, null=True, verbose_name=_('Extension type'))
    parent_repository = models.ForeignKey('haindex.Repository', null=True, blank=True,
                                          verbose_name=_('Parent repository'), on_delete=models.SET_NULL)

    last_import = models.DateTimeField(null=True, blank=True, verbose_name=_('Last import'))

    last_commit_id = models.CharField(max_length=40, blank=True, verbose_name=_('Last git commit ID'))
    last_push = models.DateTimeField(null=True, blank=True, verbose_name=_('Last git push'))
    stargazers_count = models.IntegerField(null=True, blank=True, verbose_name=_('Stargazers count'))
    forks_count = models.IntegerField(null=True, blank=True, verbose_name=_('Forks count'))
    issues_count = models.IntegerField(null=True, blank=True, verbose_name=_('Issues count'))
    webhook_id = models.IntegerField(null=True, blank=True, verbose_name=_('GitGub webhook ID'))

    # package.json meta
    name = models.CharField(max_length=100, blank=True, verbose_name=_('Display name'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    readme = models.TextField(blank=True, verbose_name=_('Readme'))
    keywords = ArrayField(base_field=models.CharField(max_length=30), blank=True, null=True,
                          verbose_name=_('Keywords'))
    author_name = models.CharField(max_length=100, blank=True, verbose_name=_('Author name'))
    author_homepage = models.URLField(blank=True, verbose_name=_('Author Homepage'))
    author_email = models.EmailField(blank=True, verbose_name=_('Author email'))
    license = models.CharField(max_length=100, blank=True, verbose_name=_('License'))

    # package.json code
    files = ArrayField(base_field=models.CharField(max_length=100), blank=True, null=True, verbose_name=_('Files'))
    dependencies = models.ManyToManyField(to='haindex.Repository', related_name='provider', blank=True,
                                          verbose_name=_('Dependencies'))

    def get_url(self):
        return '{owner_url}/{name}'.format(owner_url=self.get_owner_url(), name=self.github_repo)

    def get_raw_url(self):
        return self.get_url() + '/raw/master'

    def get_last_commit_url(self):
        return '{repo}/commit/{commit}'.format(repo=self.get_url(), commit=self.last_commit_id)

    def get_issue_url(self):
        return '{repo}/issues'.format(repo=self.get_url())

    def get_stargazers_url(self):
        return '{repo}/stargazers'.format(repo=self.get_url())

    def get_forks_url(self):
        return '{repo}/network/members'.format(repo=self.get_url())

    def get_issues_url(self):
        return '{repo}/issues'.format(repo=self.get_url())

    def get_owner_url(self):
        return 'https://github.com/{user}'.format(user=self.github_user)

    def get_name(self):
        return '{}/{}'.format(self.github_user, self.github_repo)

    def get_author_name(self):
        if self.author_name:
            return self.author_name
        return self.github_user

    @property
    def last_commit_id_short(self):
        if self.last_commit_id:
            return self.last_commit_id[:7]
        return ''

    def __str__(self):
        return self.get_name()

    class Meta:
        verbose_name = _('Repository')
        verbose_name_plural = _('Repositories')
        unique_together = ('github_user', 'github_repo')
