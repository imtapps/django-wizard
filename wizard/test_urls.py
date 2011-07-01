from django import http
from django.conf.urls.defaults import patterns, include, url

test_urls = patterns('',
    url(r'^(?P<step>.+?)?/?$', lambda request, step: http.HttpResponse(step), name="test1"),
    url(r'^(?P<asdf>\d+)/(?P<step>.+?)?/?$', lambda request, step: http.HttpResponse(step), name="test2"),
    url(r'^(\d+)/(.+?)/(.+?)/?$', lambda request, *args: http.HttpResponse(args), name='test3'),
)

urlpatterns = patterns('',
    (r'^test/', include(test_urls, namespace='test')),
)