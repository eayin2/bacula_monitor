from django.conf.urls import patterns, url, include
from monitor import views
urlpatterns = patterns('',
    url(r'^monitor/', views.monitor, name='monitor'),
)
