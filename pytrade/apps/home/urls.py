from django.conf.urls import patterns, url
#from pytrade.apps.home.views import wsagregar_prepaquete
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = patterns(
    'pytrade.apps.home.views',
    url(r'^$', 'index_view', name='vista_inicio'),
    url(r'^login/', 'login_view', name='vista_login'),
    url(r'^logout/', 'logout_view', name='vista_logout'),
    url(r'^registrar/', 'registrar_view', name='vista_registrar'),
    # Perfiles
    url(r'^profile/$', 'profile_view', name='vista_profile'),
    url(r'^profile/edit/', 'perfil_usuario_view', name='vista_perfil'),
    url(r'^profile/comprar/', 'comprar_view', name='vista_comprar'),
    url(r'^profile/historial/', 'cliente_historial_view', name='vista_historial'),
    # Paginas Internas
    url(r'^empresa/', 'empresa_view', name='vista_empresa'),
    url(r'^servicio/', 'servicio_view', name='vista_servicio'),
    url(r'^tarifa/', 'tarifa_view', name='vista_tarifa'),
    url(r'^preguntas/', 'preguntas_view', name='vista_preguntas'),
    url(r'^tiendas/', 'tiendas_view', name='vista_tiendas'),
    url(r'^contacto/', 'contacto_view', name='vista_contacto'),
    #webservices
    url(r'^webservices/ws_email', 'wsemail_view', name='ws_email'),
    url(r'^webservices/ws_codigo', 'wscodigo_view', name='ws_codigo'),
    #RESTful
    #url(r'^ws/paquete/$', wsagregar_prepaquete.as_view(), name='vista_rest_agregar_prepaquete'),
)

#urlpatterns = format_suffix_patterns(urlpatterns)