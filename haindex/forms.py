# -*- coding: UTF-8 -*-
import re

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from snowpenguin.django.recaptcha2.fields import ReCaptchaField
from snowpenguin.django.recaptcha2.widgets import ReCaptchaWidget

from haindex.common.util.repository.checker import RepositoryChecker


class RepositorySubmitForm(forms.Form):
    repository_url = forms.URLField(label=_('GitHub repository URL'))
    captcha = ReCaptchaField(widget=ReCaptchaWidget(), label=_('Captcha'))

    def __init__(self, request, *args, **kwargs):
        self.request = request
        self.github_user = None
        self.github_repo = None
        super().__init__(*args, **kwargs)

    def clean_repository_url(self):
        repository_url = self.cleaned_data.get('repository_url')
        matches = re.match(r'https://github.com/([^/]+)/([^/]+)/?', repository_url)
        if not matches:
            raise ValidationError(_('Please enter a GitHub repository URL'))
        github_user, github_repo = matches.groups()

        # remove .git from name
        if github_repo.endswith('.git'):
            github_repo = github_repo.replace('.git', '')

        # get user access token
        access_token = None
        auth = self.request.user.social_auth.filter(provider='github').first()
        if auth:
            access_token = auth.extra_data.get('access_token')

        # check package.yaml
        try:
            RepositoryChecker(
                access_token=access_token, github_user=github_user, github_repo=github_repo).check_package()
        except Exception as e:
            raise ValidationError(_('Repository validation error: %(error)s') % dict(error=str(e)))

        self.github_user = github_user
        self.github_repo = github_repo

        return repository_url


class RepositorySearchForm(forms.Form):
    search = forms.CharField(max_length=100)
