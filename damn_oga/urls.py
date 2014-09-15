from django.conf.urls import patterns, include, url


urlpatterns = patterns('',
    url(r'^$', 'files.views.index', name='index'),
    
    url(r'^reset/$', 'files.views.reset', name='reset'),
    
    url(r'^capabilities/$', 'files.views.capabilities', name='capabilities'),
    
    url(r'^analyzed/$', 'files.views.analyzed', name='analyzed'),
    
    url(r'^analyze/$', 'files.views.analyze', name='analyze'),
    
    url(r'^transcode/$', 'files.views.transcode', name='transcode'),
    
    url(r'^download/$', 'files.views.download', name='download'),
)
