from django.conf.urls import patterns, url, include
from monitor import views

urlpatterns = patterns('',
    url(r'^$', views.monitor, name='monitor'),
    url(r'^monitor/', views.monitor, name='monitor'),
    url(r'^all_backups/', views.all_backups, name='all_backups'),
)
