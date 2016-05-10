from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from pytrade.apps.home.models import *
from import_export.admin import ImportExportModelAdmin
import resource


class ClienteInline(admin.StackedInline):
    model = Cliente
    can_delete = False
    verbose_name_plural = 'clientes'


class ClienteAdmin(admin.ModelAdmin):
    search_fields = ['user__email', 'codigo', '^user__last_name', '^user__first_name']
    list_display = ('user', 'user_nombre', 'categoria', 'codigo', 'celular', 'contrato')
    list_filter = ('sucursal', 'completo', 'contrato', 'categoria', 'vendedor')

    def user_nombre(self, obj):
        u = User.objects.get(id=obj.user_id)
        return "%s %s" % (u.first_name, u.last_name)


# Import-Export del Cliente
class ClienteIEAdmin(ImportExportModelAdmin):
    list_display = ('codigo', 'lote', 'cliente', 'descripcion', 'peso', 'valor_dolar', 'tipo')
    search_fields = ['cliente']
    resource_class = resource.ClienteResource


# Define a new User admin
class UserAdmin(UserAdmin):
    date_hierarchy = 'date_joined'
    #inlines = (ClienteInline, )



# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Categoria)
admin.site.register(Cliente, ClienteAdmin)
#admin.site.register(Cliente, ClienteIEAdmin)
admin.site.register(Vendedor)
admin.site.register(Sucursal)
admin.site.register(Usuario)
admin.site.register(ClienteFactura)
#admin.site.register(PrePaquete)