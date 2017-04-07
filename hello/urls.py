from django.conf.urls import url

from hello.views import HomePageView
from hello import views

urlpatterns = [
    url(r'^$', views.homePage, name='home'),
    url(r'^user_manual$', views.user_manual, name='user_manual'),
    url(r'^documentation$', views.documentation, name='documentation'),
    url(r'^upload$', views.upload, name='upload'),
    url(r'^generate$', views.generate, name='generate'),
    url(r'^choose_key$', views.choose_key, name='choose_key'),
    url(r'^choose_merge$', views.choose_merge, name='choose_merge'),
    url(r'^proceed_next$', views.proceed_next, name='proceed_next'),
    url(r'^download$', views.download, name='download'),
]
