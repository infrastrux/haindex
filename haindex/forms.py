# -*- coding: UTF-8 -*-
from django import forms
from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _
from snowpenguin.django.recaptcha2.fields import ReCaptchaField
from snowpenguin.django.recaptcha2.widgets import ReCaptchaWidget


class RepositorySubmitForm(forms.Form):
    repository_url = forms.URLField(validators=[
        RegexValidator(regex=r'https://github.com/[^/]+/[^/]+/?$', message=_('Please enter a GitHub repository URL'),
                       code='github_url')])
    captcha = ReCaptchaField(widget=ReCaptchaWidget())


class RepositorySearchForm(forms.Form):
    search = forms.CharField(max_length=100)
