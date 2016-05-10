from pytrade.apps.backend.models import *
import django_filters


class CompraFilter(django_filters.FilterSet):
    fecha_solicitud = django_filters.DateRangeFilter()


    class Meta:
        model = Compra
        fields = {
            'pagado': ['exact'],
            'fecha_solicitud': ['gte', 'lte'],
            'valor_compra_dolar': ['gte', 'lte'],
        }

        #fields = ["pagado", "fecha_solicitud"]

        #order_by = (
        #    ('fecha_solicitud', 'Solicitud'),
        #    ('valor_compra_dolar', 'Valor USD'),
        #)


class CargaFilter(django_filters.FilterSet):
    created_at = django_filters.DateRangeFilter()

    class Meta:
        model = Carga
        fields = ['origen', 'created_at']