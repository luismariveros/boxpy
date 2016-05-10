from django.conf.urls import patterns, url, include


urlpatterns = patterns(
    'pytrade.apps.backend.views',
    url(r'^$', 'index_view', name='vista_backend'),
    url(r'^autocomplete/', include('autocomplete_light.urls')),
    url(r'^exportar/$', 'paquete_exportar_view', name='vista_exportar_paquete'),
    url(r'^busqueda/(?P<tipo>.*)/$', 'cliente_busqueda_view', name='vista_busqueda_clientes'),
    url(r'^cliente/$', 'cliente_list_view', name='vista_lista_clientes'),
    url(r'^cliente/(?P<user>.*)/$', 'cliente_historial_view', name='vista_historial_cliente'),
    url(r'^paquete/$', 'paquete_list_view', name='vista_lista_paquetes'),
    url(r'^paquete/agrupar/$', 'paquete_agrupar_list', name='vista_agrupar_paquetes'),
    url(r'^paquete/agregar/$', 'paquete_agregar_view', name='vista_paquete_agregar'),
    url(r'^paquete/editar/(?P<id>.*)/$', 'paquete_editar_view', name='vista_paquete_editar'),
    url(r'^paquete/entregar/(?P<user>.*)/$', 'paquete_entregar_view', name='vista_entregar_paquete'),
    url(r'^paquete/wsentregar$', 'wspaquete_entregar_view', name='ws_entregar_paquete'),
    url(r'^mail/$', 'enviar_mail_view', name='vista_enviar_mail'),
    url(r'^compra/$', 'compra_list_view', name='vista_lista_compras'),
    url(r'^compra/agregar$', 'compra_agregar_view', name='vista_agregar_orden_compra'),
    url(r'^compra/cotizar/(?P<id>.*)/$', 'compra_cotizar_view', name='vista_cotizar_pedido'),
    url(r'^compra/pagar/(?P<id>.*)/$', 'compra_pagar_pedido_view', name='vista_pagar_pedido'),
    (r'^barcode/(?P<paquete>.*)/$', 'barcode_view'),
    url(r'^listado/$', 'generar_listado_mail_view', name='vista_generar_listado'),
    url(r'^carga/importar/$', 'carga_importar_view', name='vista_importar_carga'),
    url(r'^carga/$', 'carga_list_view', name='vista_lista_cargas'),
    url(r'^carga/(?P<id>.*)/$', 'carga_detalle_view', name='vista_detalle_carga'),
    url(r'^ticket/$', 'ticket_list_view', name='vista_lista_tickets'),
    url(r'^ticket/estado/$', 'ticket_cambio_estado_view', name='vista_cambio_estado_ticket'),
    url(r'^ticket/(?P<id>.*)/$', 'ticket_detalle_view', name='vista_detalle_ticket'),
    url(r'^proveedor/$', 'proveedor_abm_view', name='vista_agregar_proveedor'),
    url(r'^proveedor/(?P<id>.*)/$', 'proveedor_abm_view', name='vista_editar_proveedor'),
    #caja
    url(r'^caja/$', 'caja_list_view', name='vista_lista_caja'),
    url(r'^caja/apertura/$', 'caja_apertura_view', name='vista_apertura_caja'),
    url(r'^caja/egreso/$', 'caja_egreso_abm_view', name='vista_agregar_egreso'),
    url(r'^caja/abierta/$', 'caja_abierta_view', name='vista_caja_abierta'),
    url(r'^caja/cierre/(?P<id>.*)/$', 'caja_cierre_view', name='vista_cierre_caja'),
    url(r'^caja/(?P<id>.*)/$', 'caja_detalle_view', name='vista_detalle_caja'),
    #manifiesto
    url(r'^manifiesto/$', 'manifiesto_list_view', name='vista_lista_manifiesto'),
    url(r'^manifiesto/agregar$', 'manifiesto_agregar_view', name='vista_manifiesto_agregar'),
    url(r'^manifiesto/(?P<id>.*)/$', 'manifiesto_detalle_view', name='vista_detalle_manifiesto'),
    #factura
    url(r'^factura/(?P<factura_id>.*)/$', 'factura_detalle_view', name='vista_detalle_factura'),
    url(r'^facturacliente/(?P<ticket_id>.*)/$', 'factura_cliente_view', name='vista_factura_cliente'),
    #webservices
    url(r'^webservices/ws_motivo_egreso', 'wsmotivo_egreso_view', name='ws_motivo_egreso'),
    url(r'^webservices/ws_compra_divisa', 'wscompra_divisa_view', name='ws_compra_divisa'),
    url(r'^webservices/ws_detalle_compra_guardar', 'wsdetalle_compra_guardar_view', name='ws_guardar_detalle_compra'),
    url(r'^webservices/ws_ticket_estado', 'wsticket_cambio_estado_view', name='ws_ticket_cambio_estado'),
    url(r'^webservices/ws_manifiesto_paquetes', 'wsmanifiesto_paquetes_view', name='ws_manifiesto_paquetes'),
    url(r'^webservices/ws_cliente_factura', 'wsfactura_cliente_view', name='ws_manifiesto_paquetes'),
    #reportes
    url(r'^informe/1', 'i_cargas_cliente_view', name='i_cargas_cliente'),
    url(r'^informe/2', 'i_ingresos_egresos_view', name='i_ingresos_egresos'),
)

