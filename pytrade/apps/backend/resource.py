from import_export import resources
from pytrade.apps.backend.models import PreManifiesto


class PreManifiestoResource(resources.ModelResource):
    class Meta:
        model = PreManifiesto
        import_id_fields = ('codigo',)
        #export_order = ('codigo', )
        #exclude = ('id', 'fecha')
        fields = ('lote', 'fecha', 'codigo', 'cliente', 'descripcion', 'peso', 'valor_dolar', 'tipo')