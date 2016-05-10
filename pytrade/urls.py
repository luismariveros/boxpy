from django.conf.urls import patterns, include, url
import settings

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
    url('', include('social.apps.django_app.urls', namespace='social')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include('pytrade.apps.home.urls')),
    url(r'^backend/', include('pytrade.apps.backend.urls')),
    url(r'^recuperar/', include('password_reset.urls')),
    #url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
)

#urlpatterns = format_suffix_patterns(urlpatterns)