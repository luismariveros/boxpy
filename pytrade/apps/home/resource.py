from import_export import resources
from pytrade.apps.home.models import Cliente


class ClienteResource(resources.ModelResource):
    class Meta:
        model = Cliente
        import_id_fields = ('codigo',)
        #export_order = ('codigo', )
        #exclude = ('id', 'fecha')
        fields = ('id', 'user__id', 'user__email', 'celular', 'telefono')