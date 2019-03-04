# -*- coding: UTF-8 -*-
import logging
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator, EmailValidator
from django.urls import reverse
from django.utils import timezone
from github import Github, UnknownObjectException, GithubException
import yaml

from haindex.common.util.readme import ReadmeRenderer
from haindex.models import Repository, RepositoryRelease

logger = logging.getLogger(__name__)


class RepositoryUpdater(object):
    def __init__(self, repository, *args, **kwargs):
        assert isinstance(repository, Repository)

        self.repository = repository
        self._file_list = None
        super().__init__(*args, **kwargs)

    def get_client(self):
        # authenticate as repository owner
        auth = self.repository.user.social_auth.filter(provider='github').first()
        if auth:
            access_token = auth.extra_data.get('access_token')
            if access_token:
                return Github(login_or_token=access_token)

        # default system user access
        return Github(login_or_token=settings.GITHUB_API_USER, password=settings.GITHUB_API_TOKEN)

    def _load_repo(self):
        try:
            return self.get_client().get_repo('{user}/{name}'.format(
                user=self.repository.user.username, name=self.repository.name), lazy=False)
        except UnknownObjectException:
            # repository wasn't found on github, let's delete it
            self.repository.delete()
        except Exception as e:
            logger.exception(e)

        return None

    def update(self):
        # get repository
        repo = self._load_repo()
        if not repo:
            return

        # get contents
        try:
            contents = repo.get_contents('')
        except GithubException as e:
            logger.exception(e)
            return

        # build list of fields to update
        update_fields = []

        # update description
        if repo.description:
            self.repository.description = repo.description
            update_fields.append('description')

        # update stat counts
        self.repository.stargazers_count = repo.stargazers_count
        update_fields.append('stargazers_count')
        self.repository.forks_count = repo.forks_count
        update_fields.append('forks_count')
        self.repository.issues_count = repo.open_issues_count
        update_fields.append('issues_count')

        # set last repository update
        self.repository.last_push = repo.pushed_at
        update_fields.append('last_push')

        # update user type
        if repo.owner.type == 'Organization':
            self.repository.user_type = getattr(Repository.USER_TYPE_CHOICES, Repository.USER_TYPE_ORG)
        else:
            self.repository.user_type = getattr(Repository.USER_TYPE_CHOICES, Repository.USER_TYPE_USER)
        update_fields.append('user_type')

        # get latest commit hash
        try:
            latest_commit = repo.get_commits()[0]
            self.repository.last_commit_id = latest_commit.sha
            update_fields.append('last_commit_id')
        except GithubException as e:
            logger.exception(e)
            return

        # try to get package.yaml and readme from the project root
        package = None
        for item in contents:
            # try to load package description
            if item.type == 'file' and item.path.lower() == 'package.yaml':
                try:
                    package = yaml.load(item.decoded_content.decode('UTF-8'))
                except Exception:
                    pass

            # try to load readme
            elif item.type == 'file' and item.path.lower() in ('readme', 'readme.md', 'readme.rst', 'readme.txt'):
                filename, extension = os.path.splitext(item.path.lower())
                self.repository.readme = ReadmeRenderer().get_html(
                    content=item.decoded_content.decode('UTF-8'), extension=extension)
                update_fields.append('readme')

        # set parent repository
        if repo.fork and repo.parent:
            parent_repository_user, created = get_user_model().objects.get_or_create(username=repo.parent.owner.login)

            parent_repository, created = Repository.objects.get_or_create(
                user=parent_repository_user, name=repo.parent.name)
            self.repository.parent_repository = parent_repository
            update_fields.append('parent_repository')

            # index parent repository
            if created:
                from haindex.tasks import update_repository
                update_repository.apply_async([parent_repository.id])

        # handle package.yaml
        self.repository.has_package_file = package is not None
        update_fields.append('has_package_file')

        if package:
            self.repository.dependencies.clear()
            if 'dependencies' in package:
                for dependency in package['dependencies']:
                    dependency_username, dependency_repo_name = dependency.split('/')
                    dependency_user, created = get_user_model().objects.get_or_create(username=dependency_username)

                    dependency_repository, created = Repository.objects.get_or_create(
                        user=dependency_user, name=dependency_repo_name)

                    if created:
                        from haindex.tasks import update_repository
                        update_repository.apply_async([dependency_repository.id])
                    self.repository.dependencies.add(dependency_repository)

            self.repository.files = []
            if 'files' in package:
                for filename in package['files']:
                    self.repository.files.append(filename)
            update_fields.append('files')

            if 'name' in package:
                self.repository.display_name = str(package['name'])[:100]
                update_fields.append('display_name')

            if 'description' in package:
                self.repository.description = package['description']
                update_fields.append('description')

            if 'type' in package:
                if package['type'] in (Repository.TYPE_LOVELACE, Repository.TYPE_COMPONENT):
                    self.repository.type = getattr(Repository.TYPE_CHOICES, package['type'])
                    update_fields.append('type')

            if 'keywords' in package and isinstance(package['keywords'], list):
                self.repository.keywords = package['keywords']
                update_fields.append('keywords')

            if 'author' in package:
                if 'name' in package['author']:
                    self.repository.author_name = str(package['author']['name'])[:100]
                    update_fields.append('author_name')
                if 'email' in package['author']:
                    try:
                        EmailValidator()(package['author']['email'])
                    except ValidationError:
                        pass
                    else:
                        self.repository.author_email = package['author']['email']
                        update_fields.append('author_email')
                if 'homepage' in package['author']:
                    try:
                        URLValidator()(package['author']['homepage'])
                    except ValidationError:
                        pass
                    else:
                        self.repository.author_homepage = package['author']['homepage']
                        update_fields.append('author_homepage')

            if 'license' in package:
                self.repository.license = str(package['license'])[:100]
                update_fields.append('license')

        # guess extension type by js/py file count in repository if not yet set
        if not self.repository.type:
            file_list = self._get_filelist(repo=repo, contents=contents)

            if file_list.get_count('.js') > 0 or file_list.get_count('.py') > 0:
                if file_list.get_count('.js') > file_list.get_count('.py'):
                    self.repository.type = getattr(Repository.TYPE_CHOICES, Repository.TYPE_LOVELACE)
                else:
                    self.repository.type = getattr(Repository.TYPE_CHOICES, Repository.TYPE_COMPONENT)
                update_fields.append('type')

        # guess required files by file extension
        if not self.repository.files or len(self.repository.files) == 0:
            if self.repository.type == Repository.TYPE_COMPONENT_ID:
                self.repository.files = self._get_filelist(repo=repo, contents=contents).get_files(extension='.py')
                update_fields.append('files')
            elif self.repository.type == Repository.TYPE_LOVELACE_ID:
                self.repository.files = self._get_filelist(repo=repo, contents=contents).get_files(extension='.js')
                update_fields.append('files')

        # set last update
        self.repository.last_import = timezone.now()
        update_fields.append('last_import')

        # save updated data
        self.repository.save(update_fields=set(update_fields))

        # update releases
        try:
            releases = repo.get_releases()
        except GithubException as e:
            logger.exception(e)
            return
        for release in releases:
            RepositoryRelease.objects.get_or_create(
                repository=self.repository, tag_name=release.tag_name, defaults=dict(
                    body=release.body, published_at=release.published_at, zipball_url=release.zipball_url))

    def _get_filelist(self, repo, contents):
        if self._file_list is None:
            self._file_list = FileList(repo=repo)
            self._file_list.count(contents=contents)
        return self._file_list

    def update_stats(self, repository):
        assert isinstance(repository, Repository)

        # get repository
        repo = self._load_repo()
        if not repo:
            return

        # build list of fields to update
        update_fields = []

        # update stat counts
        repository.stargazers_count = repo.stargazers_count
        update_fields.append('stargazers_count')
        repository.forks_count = repo.forks_count
        update_fields.append('forks_count')
        repository.issues_count = repo.open_issues_count
        update_fields.append('issues_count')

        repository.save(update_fields=update_fields)

    def subscribe(self):
        # webhook creation is not enabled
        if not settings.GITHUB_WEBHOOK_ENABLED:
            logger.warning('GitHub webhook creation has been disabled in config')
            return

        # get repository
        repo = self._load_repo()
        if not repo:
            return

        hook_config = {
            'url': '{page_url}{endpoint}'.format(
                page_url=settings.PAGE_URL, endpoint=reverse('haindex_github_callback')),
            'content_type': 'json',
            'secret': settings.GITHUB_WEBHOOK_SECRET,
        }
        hook_events = ['push', 'watch', 'issues', 'pull_request', 'fork']
        webhook = repo.create_hook('web', hook_config, hook_events, active=True)

        self.repository.webhook_id = webhook.id
        self.repository.save(update_fields=['webhook_id'])


class FileList(object):
    def __init__(self, repo):
        self.extensions = dict()
        self.files = dict()
        self.repo = repo
        super().__init__()

    def count(self, contents):
        for item in contents:
            # search directories recursively
            if item.type == 'dir':
                try:
                    self.count(contents=self.repo.get_contents(item.path))
                except GithubException as e:
                    logger.exception(e)
                    return

            # count files
            if item.type == 'file':
                filename, file_extension = os.path.splitext(item.path.lower())
                self.extensions.setdefault(file_extension, 0)
                self.extensions[file_extension] += 1
                self.files.setdefault(file_extension, list())
                self.files[file_extension].append(item.path.lower())

    def get_count(self, extension):
        if extension not in self.extensions:
            return 0
        return self.extensions[extension]

    def get_files(self, extension):
        if extension not in self.files:
            return []
        return self.files[extension]
