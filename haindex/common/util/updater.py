# -*- coding: UTF-8 -*-
import logging
import os

from django.conf import settings
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
    def __init__(self):
        super().__init__()
        self._client = None
        self._file_list = dict()

    @property
    def client(self):
        if self._client is None:
            self._client = Github(login_or_token=settings.GITHUB_API_USER,
                                  password=settings.GITHUB_API_TOKEN)
        return self._client

    def _load_repo(self, repository):
        try:
            return self.client.get_repo('{user}/{name}'.format(
                user=repository.github_user, name=repository.github_repo), lazy=False)
        except UnknownObjectException:
            # repository wasn't found on github, let's delete it
            repository.delete()
        except GithubException as e:
            logger.exception(e)

        return None

    def update(self, repository):
        assert isinstance(repository, Repository)

        # get repository
        repo = self._load_repo(repository=repository)
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
            repository.description = repo.description
            update_fields.append('description')

        # update stat counts
        repository.stargazers_count = repo.stargazers_count
        update_fields.append('stargazers_count')
        repository.forks_count = repo.forks_count
        update_fields.append('forks_count')
        repository.issues_count = repo.open_issues_count
        update_fields.append('issues_count')

        # set last repository update
        repository.last_push = repo.pushed_at
        update_fields.append('last_push')

        # get latest commit hash
        try:
            latest_commit = repo.get_commits()[0]
            repository.last_commit_id = latest_commit.sha
            update_fields.append('last_commit_id')
        except GithubException as e:
            logger.exception(e)
            return

        # try to get package.yaml and readme
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
                repository.readme = ReadmeRenderer().get_html(
                    content=item.decoded_content.decode('UTF-8'), extension=extension)
                update_fields.append('readme')

        # set parent repository
        if repo.fork and repo.parent:
            parent_repository, created = Repository.objects.get_or_create(
                github_user=repo.parent.owner.login, github_repo=repo.parent.name)
            from haindex.tasks import update_repository
            update_repository.apply_async([parent_repository.id])
            repository.parent_repository = parent_repository
            update_fields.append('parent_repository')

        # parse package.yaml if found
        if package:
            repository.has_package_file = True
            update_fields.append('has_package_file')

            repository.dependencies.clear()
            if 'dependencies' in package:
                for dependency in package['dependencies']:
                    dependency_github_user, dependency_github_repo = dependency.split('/')
                    dependency_repository, created = Repository.objects.get_or_create(
                        github_user=dependency_github_user, github_repo=dependency_github_repo)
                    from haindex.tasks import update_repository
                    update_repository.apply_async([dependency_repository.id])
                    repository.dependencies.add(dependency_repository)

            repository.files = []
            if 'files' in package:
                for filename in package['files']:
                    repository.files.append(filename)
            update_fields.append('files')

            if 'name' in package:
                repository.name = str(package['name'])[:100]
                update_fields.append('name')

            if 'description' in package:
                repository.description = package['description']
                update_fields.append('description')

            if 'type' in package:
                if package['type'] in (Repository.TYPE_LOVELACE, Repository.TYPE_COMPONENT):
                    repository.type = getattr(Repository.TYPE_CHOICES, package['type'])
                    update_fields.append('type')

            if 'keywords' in package and isinstance(package['keywords'], list):
                repository.keywords = package['keywords']
                update_fields.append('keywords')

            if 'author' in package:
                if 'name' in package['author']:
                    repository.author_name = str(package['author']['name'])[:100]
                    update_fields.append('author_name')
                if 'email' in package['author']:
                    try:
                        EmailValidator()(package['author']['email'])
                    except ValidationError:
                        pass
                    else:
                        repository.author_email = package['author']['email']
                        update_fields.append('author_email')
                if 'homepage' in package['author']:
                    try:
                        URLValidator()(package['author']['homepage'])
                    except ValidationError:
                        pass
                    else:
                        repository.author_homepage = package['author']['homepage']
                        update_fields.append('author_homepage')

            if 'license' in package:
                repository.license = str(package['license'])[:100]
                update_fields.append('license')

        # guess extension type by js/py file count in repository if not yet set
        if not repository.type:
            file_list = self._get_filelist(repo=repo, contents=contents)

            if file_list.get_count('.js') > 0 or file_list.get_count('.py') > 0:
                if file_list.get_count('.js') > file_list.get_count('.py'):
                    repository.type = getattr(Repository.TYPE_CHOICES, Repository.TYPE_LOVELACE)
                else:
                    repository.type = getattr(Repository.TYPE_CHOICES, Repository.TYPE_COMPONENT)
                update_fields.append('type')

        # guess required files by file extension
        if not repository.files or len(repository.files) == 0:
            if repository.type == Repository.TYPE_COMPONENT_ID:
                repository.files = self._get_filelist(repo=repo, contents=contents).get_files(extension='.py')
                update_fields.append('files')
            elif repository.type == Repository.TYPE_LOVELACE_ID:
                repository.files = self._get_filelist(repo=repo, contents=contents).get_files(extension='.js')
                update_fields.append('files')

        # set last update
        repository.last_import = timezone.now()
        update_fields.append('last_import')

        # save updated data
        repository.save(update_fields=set(update_fields))

        # update releases
        try:
            releases = repo.get_releases()
        except GithubException as e:
            logger.exception(e)
            return
        for release in releases:
            RepositoryRelease.objects.get_or_create(
                repository=repository, tag_name=release.tag_name, defaults=dict(
                    body=release.body, published_at=release.published_at, zipball_url=release.zipball_url))

    def _get_filelist(self, repo, contents):
        if repo.full_name not in self._file_list:
            self._file_list[repo.full_name] = FileList(repo=repo)
            self._file_list[repo.full_name].count(contents=contents)
        return self._file_list[repo.full_name]

    def update_stats(self, repository):
        assert isinstance(repository, Repository)

        # get repository
        repo = self._load_repo(repository=repository)
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

    def subscribe(self, repository):
        assert isinstance(repository, Repository)

        # webhook creation is not enabled
        if not settings.GITHUB_WEBHOOK_ENABLED:
            logger.warning('GitHub webhook creation has been disabled in config')
            return

        # get repository
        repo = self._load_repo(repository=repository)
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

        repository.webhook_id = webhook.id
        repository.save(update_fields=['webhook_id'])


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
