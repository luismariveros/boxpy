from django.contrib import admin
#import autocomplete_light
from django.contrib.auth.models import User
from pytrade.apps.backend.models import *
from pytrade.apps.home.models import Usuario
from import_export.admin import ImportExportModelAdmin
import resource


# Import-Export del PreManifiesto
class PreManifiestoAdmin(ImportExportModelAdmin):
    list_display = ('codigo', 'lote', 'cliente', 'descripcion', 'peso', 'valor_dolar', 'tipo')
    search_fields = ['cliente']
    resource_class = resource.PreManifiestoResource


class PagoAdmin(admin.ModelAdmin):
    list_display = ('id', 'monto', 'moneda', 'formapago')
    list_filter = ('moneda', 'formapago')


class PagoAdminExport(ImportExportModelAdmin):
    #resource_class = PagoResource
    list_display = ('id', 'monto', 'moneda', 'formapago')
    list_filter = ('moneda', 'formapago')


class PaqueteAdmin(admin.ModelAdmin):
    #resource_class = PaqueteResource
    date_hierarchy = 'fecha'
    search_fields = ['user__email', '^user__first_name', '^user__last_name', 'codigo', 'tracking']
    list_display = ('user', 'codigo', 'user_nombre', 'descripcion', 'peso', 'fecha_origen', 'ubicacion',
                    'fecha_destino_corta', 'entregado', 'costo_envio_gs', 'tracking')
    list_filter = ('sucursal', 'ubicacion', 'entregado', 'delivery', 'seguro')
    readonly_fields = ('created_at', )
    #form = autocomplete_light.modelform_factory(Paquete)

    def user_nombre(self, obj):
        u = User.objects.get(id=obj.user_id)
        return "%s %s" % (u.first_name, u.last_name)

    def fecha_origen(self, obj):
        return "%s" % obj.fecha.strftime("%d/%b/%Y") if obj.fecha else "Sin Fecha"

    def fecha_destino_corta(self, obj):
        return "%s" % obj.fecha_destino.strftime("%d/%b/%Y") if obj.fecha_destino else "Sin Fecha"


class TicketAdmin(admin.ModelAdmin):
    date_hierarchy = 'fecha'
    search_fields = ['user__first_name', 'user__last_name', 'id']
    list_display = ('id', 'user_nombre', 'cantidad_paquete', 'peso_sistema', 'peso_cobrado',
                    'monto_gs', 'monto_dolar', 'fecha_corta')
    list_filter = ('sucursal', )
    readonly_fields = ('fecha', )

    def user_nombre(self, obj):
        u = User.objects.get(id=obj.user_id)
        return "%s %s" % (u.first_name, u.last_name)

    def fecha_corta(self, obj):
        return obj.fecha.strftime("%d/%b/%Y %H:%M") if obj.fecha else "Sin Fecha"


class CargaAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    search_fields = ['origen__nombre', 'archivo']
    list_display = ('archivo', 'origen', 'cantidad_paquetes', 'kilos', 'created_at')
    list_filter = ('origen', )
    readonly_fields = ('created_at', )


class CajaAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    search_fields = ['user__email', '^user__first_name', '^user__last_name']
    list_display = ('id', 'sucursal', 'tipo', 'user_nombre', 'monto_gs', 'monto_dolar', 'created_at')
    list_filter = ('sucursal', 'tipo')
    readonly_fields = ('created_at', )
    #form = autocomplete_light.modelform_factory(Paquete)

    def user_nombre(self, obj):
        u = User.objects.get(id=obj.user_id)
        return "%s %s" % (u.first_name, u.last_name)


class MovimientoAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    search_fields = ['user__email', '^user__first_name', '^user__last_name']
    list_display = ('sucursal', 'motivo', 'motivo_tipo', 'monto', 'moneda', 'created_at')
    list_filter = ('sucursal', 'motivo__tipo', 'motivo')
    readonly_fields = ('created_at', )

    def usuario_sistema(self, obj):
        u = Usuario.objects.get(id=obj.user_id)
        return u.user.get_full_name()

    def motivo_tipo(self, obj):
        return obj.motivo.tipo


class ComprasAdmin(admin.ModelAdmin):
    date_hierarchy = 'fecha_solicitud'
    search_fields = ['user__email', '^user__first_name', '^user__last_name']
    list_display = ('user_nombre', 'detalle_cantidad', 'pagado', 'fecha_solicitud', 'valor_compra_dolar')
    list_filter = ('detalle__estado', 'pagado')
    #readonly_fields = ('created_at', )

    def user_nombre(self, obj):
        u = User.objects.get(id=obj.user_id)
        return u.get_full_name()

    def detalle_cantidad(self, obj):
        return obj.detalle.count()


class ManifiestoAdmin(admin.ModelAdmin):
    date_hierarchy = 'fecha_arribo'
    search_fields = ['id', 'fecha_arribo', 'bolsa_cantidad']
    list_display = ('id', 'origen', 'fecha_arribo', 'bolsa_cantidad', 'bolsa_peso', 'created_at')
    list_filter = ('origen', )
    readonly_fields = ('created_at', )


admin.site.register(Configuracion)
admin.site.register(Compra, ComprasAdmin)
admin.site.register(CompraDetalle)
admin.site.register(Carga, CargaAdmin)
admin.site.register(Paquete, PaqueteAdmin)
admin.site.register(Ubicacion)
admin.site.register(Ticket, TicketAdmin)
admin.site.register(FormaPago)
admin.site.register(Moneda)
admin.site.register(Proveedor)
admin.site.register(MotivoMovimiento)
admin.site.register(Movimiento, MovimientoAdmin)
admin.site.register(Caja, CajaAdmin)
admin.site.register(Pago, PagoAdmin)
admin.site.register(Manifiesto, ManifiestoAdmin)
admin.site.register(PreManifiesto, PreManifiestoAdmin)
admin.site.register(Talonario)
admin.site.register(Factura)
admin.site.register(FacturaDetalle)