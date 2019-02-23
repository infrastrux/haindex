# -*- coding: UTF-8 -*-
import json
import logging
import os
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from github import Github, UnknownObjectException, GithubException
import yaml
import jsonschema

logger = logging.getLogger(__name__)


class RepositoryChecker(object):
    def __init__(self, access_token, github_user, github_repo, *args, **kwargs):
        self.client = Github(login_or_token=access_token)
        self.github_user = github_user
        self.github_repo = github_repo
        self.repo = None
        super().__init__(*args, **kwargs)

    def check_package(self):
        # get repository
        try:
            repo = self.client.get_repo('{user}/{name}'.format(
                user=self.github_user, name=self.github_repo), lazy=False)
        except UnknownObjectException as e:
            raise Exception(_('Repository doesn\'t exist'))
        except Exception as e:
            raise Exception(_('Failed to load repository (%(error)s)', str(e)))

        # get contents
        try:
            contents = repo.get_contents('')
        except GithubException as e:
            logger.exception(e)
            raise Exception(_('Failed to load repository contents'))

        package = None
        for item in contents:
            # try to load package description
            if item.type == 'file' and item.path.lower() == 'package.yaml':
                try:
                    package = yaml.load(item.decoded_content.decode('UTF-8'))
                except Exception:
                    raise Exception('Failed to parse package.yaml')

        if not package:
            raise Exception(_('package.yaml not found'))

        # validate package content
        schema = json.loads(Path(os.path.join(
            settings.BASE_DIR, 'haindex', 'static', 'package-yaml.schema.json')).read_text())
        try:
            jsonschema.validate(instance=package, schema=schema)
        except ValidationError as e:
            raise Exception(_('Failed to validate package.yaml: %(error)s', error=str(e)))
