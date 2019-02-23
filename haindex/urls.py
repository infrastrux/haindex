# -*- coding: UTF-8 -*-
from django.conf.urls import url
from django.contrib import admin
from django.contrib.flatpages.views import flatpage
from django.http import HttpResponse
from django.urls import include

from haindex import views

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^pages(?P<url>.*)$', flatpage, name='flatpage'),
    url('', include('social_django.urls', namespace='social')),

    url(r'^login/$', views.Login.as_view(), name='login'),
    url(r'^logout/$', views.Logout.as_view(), name='logout'),
    url(r'^lb/check/$', lambda r: HttpResponse('OK!')),  # endpoint for load balancers to check if system is up

    url(r'^$', views.IndexView.as_view(), name='haindex_index'),
    url(r'^extension/submit/$', views.RepositorySubmitView.as_view(), name='haindex_extension_submit'),
    url(r'^extension/search/$', views.RepositorySearchView.as_view(), name='haindex_extension_search'),
    url(r'^extension/(?P<user>[^/]+)/(?P<name>[^/]+)/$', views.RepositoryDetailView.as_view(),
        name='haindex_extension_detail'),
    url(r'^github/callback/$', views.GitHubCallbackView.as_view(), name='haindex_github_callback'),
]
