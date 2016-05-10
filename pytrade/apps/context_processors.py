from pytrade.apps.backend.models import Moneda


def my_processor(request):
    context = {
        'cotizacion': Moneda.objects.get(codigo='USD').cotizacion,
    }
    return context

