# -*- coding: UTF-8 -*-
import hmac
import json
from hashlib import sha1

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.http import Http404, HttpResponseForbidden, HttpResponse, HttpResponseBadRequest
from django.urls import reverse_lazy, reverse
from django.utils.encoding import force_bytes
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, FormView, DetailView, ListView, RedirectView
from django.views.generic.base import View

from haindex import forms, models, documents


class IndexView(TemplateView):
    template_name = 'haindex/index.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['hide_search'] = True

        # list extension counts
        totals = models.Repository.objects.values('type').annotate(total=Count('type'))
        for total in totals:
            if total['type'] == models.Repository.TYPE_LOVELACE_ID:
                ctx['lovelace_count'] = total['total']
            elif total['type'] == models.Repository.TYPE_COMPONENT_ID:
                ctx['component_count'] = total['total']

        return ctx


class Login(RedirectView):
    permanent = False

    def get_redirect_url(self):
        return reverse('social:begin', args=('github',))


class Logout(RedirectView):
    permanent = False

    def get_redirect_url(self):
        logout(self.request)
        return reverse('haindex_index')


class RepositorySubmitView(LoginRequiredMixin, FormView):
    template_name = 'haindex/repository/submit.html'
    form_class = forms.RepositorySubmitForm
    success_url = reverse_lazy('haindex_index')

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(request=self.request, **self.get_form_kwargs())

    def form_valid(self, form):
        response = super().form_valid(form)

        # get or create user
        user, created = get_user_model().objects.get_or_create(username=form.github_user)

        # get or create repository
        repository, created = models.Repository.objects.get_or_create(
            user=user, name=form.github_repo)

        # start data update job
        from haindex.tasks import update_repository
        update_repository.apply_async([repository.id])

        # subscribe to repository events
        if not repository.webhook_id:
            from haindex.tasks import subscribe_repository
            subscribe_repository.apply_async([repository.id])

        # let the user know what will happen next
        if created:
            messages.success(self.request, _('Thanks! The extension will be processed soon'))
        else:
            messages.success(self.request, _('Thanks! The extension will be updated soon'))

        return response


class RepositorySearchView(ListView):
    template_name = 'haindex/repository/search.html'
    context_object_name = 'results'
    paginate_by = 20

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        ctx['search_term'] = self.request.GET.get('search', '')
        return ctx

    def get_queryset(self):
        # filter search
        search_term = self.request.GET.get('search', None)
        if search_term:
            queryset = documents.RepositoryDocument.search_all(term=search_term).to_queryset()
        else:
            queryset = models.Repository.objects.all().order_by('-last_push')

        return queryset


class RepositoryDetailView(DetailView):
    template_name = 'haindex/repository/detail.html'
    model = models.Repository
    context_object_name = 'result'

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()

        queryset = queryset.filter(
            user__username=self.kwargs.get('user'), name=self.kwargs.get('name')
        ).prefetch_related('dependencies', 'repositoryrelease_set')

        try:
            # Get the single item from the filtered queryset
            obj = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404(_('Repository not found, why don\'t you add it to the index?'))
        return obj


class GitHubCallbackView(View):
    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        # get request signature
        header_signature = request.META.get('HTTP_X_HUB_SIGNATURE')
        if header_signature is None:
            return HttpResponseForbidden('Permission denied')

        # verify signature format
        if '=' not in header_signature:
            return HttpResponseBadRequest('Invalid header signature')
        sha_name, signature = header_signature.split('=')
        if sha_name != 'sha1':
            return HttpResponseBadRequest('Operation not supported')

        # verify webhook key
        mac = hmac.new(force_bytes(settings.GITHUB_WEBHOOK_SECRET), msg=force_bytes(request.body), digestmod=sha1)
        if not hmac.compare_digest(force_bytes(mac.hexdigest()), force_bytes(signature)):
            return HttpResponseForbidden('Invalid token')

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        event = request.META.get('HTTP_X_GITHUB_EVENT', 'ping')

        # get payload from post data or use whole request body
        if 'payload' in request.POST:
            payload = json.loads(request.POST['payload'])
        else:
            payload = json.loads(request.body.decode('utf-8'))

        # get related repository
        repository = models.Repository.objects.filter(
            user__name=payload['repository']['owner']['login'],
            name=payload['repository']['name']).first()
        if not repository:
            return HttpResponse(status=204)

        # handle the event
        if event == 'push':
            from haindex.tasks import update_repository
            update_repository.apply_async([repository.id])
        elif event in ('watch', 'issues', 'pull_request'):
            from haindex.tasks import update_repository_stats
            update_repository_stats.apply_async([repository.id])
        elif event == 'fork':
            fork_user, created = get_user_model().objects.get_or_create(
                username=payload['forkee']['owner']['login'])
            fork_repository, created = models.Repository.objects.get_or_create(
                user=fork_user, name=payload['forkee']['name'])
            from haindex.tasks import update_repository
            update_repository.apply_async([fork_repository.id])
        else:
            return HttpResponse(status=204)

        return HttpResponse('success')
