from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns('sample.views',
    url(r'^wizard/(?P<step>[a-zA-Z]+)/$', 'wizard_view', name="wizard"),
)
