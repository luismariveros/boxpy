#encoding=utf8
from django import forms
from django.db.models import Q
from pytrade.apps.home.models import Cliente, ClienteFactura, Sucursal
from pytrade.apps.backend.models import *
from simple_search import BaseSearchForm
from bootstrap3_datetime.widgets import DateTimePicker
from django.contrib.auth.models import User
import autocomplete_light


class CotizacionForm(forms.Form):
    dolar = forms.IntegerField(min_value=0, label='Nueva Cotización')

    def clean(self):
        return self.cleaned_data


class BusquedaClienteForm(BaseSearchForm):
    class Meta:
        base_qs = Cliente.objects
        search_fields = ('user__last_name', 'user__first_name', '=cedula', 'codigo')

    sucursal = forms.IntegerField(widget=forms.HiddenInput(), required=False)

    # Se filtra la sucursal del Usuario
    def prepare_sucursal(self):
        sucursal = self.cleaned_data.get('sucursal')
        if sucursal:
            return Q(sucursal_id=sucursal)
        else:
            return ""


class PaqueteEntregarForm(forms.Form):
    pesocobrado = forms.DecimalField(widget=forms.HiddenInput())
    formapago = forms.ModelChoiceField(queryset=FormaPago.objects.all(), label='Forma de Pago: ')
    cobrado_gs = forms.IntegerField(widget=forms.HiddenInput())
    cobrado_dolar = forms.DecimalField(widget=forms.HiddenInput())
    contrato = forms.BooleanField(label='¿Firmo Contrato?', required=False)
    delivery = forms.BooleanField(label='Delivery', required=False)
    moneda = forms.ModelChoiceField(queryset=Moneda.objects.all(), label='Moneda de Pago: ')
    monto_compra_divisa_gs = forms.IntegerField(required=False, label='Monto Gs: ')
    monto_compra_divisa_dolar = forms.DecimalField(required=False, label='Monto USD: ')

    def clean(self):
        return self.cleaned_data

    def __init__(self, *args, **kwargs):
        super(PaqueteEntregarForm, self).__init__(*args, **kwargs)
        self.fields['formapago'].choices = pagosChoices()
        self.fields['moneda'].choices = monedasChoice()


def pagosChoices():
    choices = []
    for choice in FormaPago.objects.all():
        choices.append([choice.id, choice.nombre])
    return choices


def monedasChoice():
    choices = []
    for choice in Moneda.objects.all():
        choices.append([choice.id, choice.nombre])
    return choices


class PaqueteForm(forms.ModelForm):
    codigo_cliente = forms.IntegerField(min_value=0, required=True,
                                        widget=forms.TextInput(attrs={'class': 'form-control',
                                                                      'placeholder': 'Código'}))
    nombre = forms.CharField(max_length=250, required=False, widget=forms.TextInput(attrs={'readonly': True}))

    class Meta:
        model = Paquete
        fields = ('fecha', 'ubicacion', 'peso', 'descripcion', 'tracking', 'proveedor', 'codigo')
        widgets = {'descripcion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descripción'}),
                   'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código Paquete'}),
                   }

    def clean(self):
        return self.cleaned_data


class PaqueteEditarForm(forms.ModelForm):
    class Meta:
        model = Paquete
        exclude = ('user', 'dolar', 'mail_origen', 'mail_destino')
        widgets = {
            'descripcion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descripción'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código Paquete'}),
        }

    def clean(self):
        return self.cleaned_data


class CompraAgregarForm(forms.ModelForm):
    codigo_cliente = forms.IntegerField(min_value=0, required=True,
                                        widget=forms.TextInput(attrs={'class': 'form-control',
                                                                      'placeholder': 'Código'}))
    nombre = forms.CharField(max_length=250, required=False, widget=forms.TextInput(attrs={'readonly': True}))

    class Meta:
        model = CompraDetalle
        fields = ('enlace', 'descripcion', 'comentario')

        widgets = {
            'comentario': forms.Textarea(attrs={'rows': '5'}),
        }


class CompraCotizarPedidoForm(forms.ModelForm):

    class Meta:
        model = CompraDetalle
        fields = ('valor_producto', 'valor_impuesto', 'valor_envio_interno', 'valor_dolar', 'valor_gs')
        widgets = {
            'valor_dolar': forms.HiddenInput(),
            'valor_gs': forms.HiddenInput()
        }

    def clean(self):
        return self.cleaned_data


class CompraPagarForm(forms.Form):
    moneda = forms.ModelChoiceField(queryset=Moneda.objects.all(), label='Moneda Entrega: ')
    formapago = forms.ModelChoiceField(queryset=FormaPago.objects.filter(codigo__in=['EF', 'TRA', 'CHE']).order_by('id'), label='Forma de Pago: ')
    monto_compra_divisa_gs = forms.IntegerField(required=False, label='Monto Gs: ')
    monto_compra_divisa_dolar = forms.DecimalField(required=False, label='Monto USD: ')

    def clean(self):
        return self.cleaned_data


class ExportarPaqueteForm(forms.Form):
    origen = forms.ModelChoiceField(queryset=Ubicacion.objects.all().order_by('id'), empty_label=None)


class EnviarMailForm(forms.Form):
    destino = forms.ModelChoiceField(queryset=Ubicacion.objects.all().order_by('id'), empty_label=None)


class ExportarListadoMail(forms.Form):
    TIPOS_CLIENTES = (
        (0, 'Clientes activos'),
        (1, 'Paquetes en Miami'),
        (2, 'Paquetes en Asunción'),
    )
    tipo = forms.ChoiceField(choices=TIPOS_CLIENTES)

    def clean(self):
        return self.cleaned_data


class CargaForm(forms.Form):
    archivo = forms.FileField()
    origen = forms.ModelChoiceField(queryset=Ubicacion.objects.all())
    enviar_mail = forms.BooleanField(required=False)
    controlar_nombre = forms.BooleanField(initial=True, required=False)
    controlar_warehouse = forms.BooleanField(initial=True, required=False)
    kilo_carga = forms.DecimalField(min_value=1, required=False)
    carga_asociada = forms.ModelChoiceField(queryset=Carga.objects.filter(origen=Ubicacion.objects.get(codigo='ASU'), carga_asociada=None).order_by('-id'), required=False)


class ManifiestoAgregarForm(forms.ModelForm):

    class Meta:
        model = Manifiesto
        exclude = ('paquete', )
        widgets = {
            'bolsa_peso': forms.TextInput(attrs={'readonly': True}),
        }

    def clean(self):
        return self.cleaned_data


class ProveedorForm(forms.ModelForm):

    class Meta:
        model = Proveedor

    def clean(self):
        return self.cleaned_data


class CajaAperturaForm(forms.ModelForm):

    class Meta:
        model = Caja
        fields = ('monto_gs', 'monto_dolar')
        widgets = {
            'monto_gs': forms.TextInput(attrs={'readonly': True}),
            'monto_dolar': forms.TextInput(attrs={'readonly': True})
        }

    def clean(self):
        return self.cleaned_data


class CajaCierreForm(forms.Form):
    saldo_gs = forms.IntegerField(widget=forms.HiddenInput())
    saldo_dolar = forms.DecimalField(widget=forms.HiddenInput())
    faltante_gs = forms.IntegerField()
    faltante_dolar = forms.DecimalField()
    sobrante_gs = forms.IntegerField()
    sobrante_dolar = forms.DecimalField()
    comentario = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    arqueo = forms.FileField()


class MovimientoForm(forms.ModelForm):

    class Meta:
        model = Movimiento
        fields = ('formapago', 'moneda', 'monto', 'motivo', 'descripcion')
        widgets = {
            'motivo': forms.HiddenInput(),
            'descripcion': forms.Textarea(attrs={'rows': 3})
        }

    def clean(self):
        return self.cleaned_data


class TicketEstadoForm(forms.Form):
    estado = forms.ModelChoiceField(queryset=FormaPago.objects.all(), label='Estado Ticket: ')
    estado_nuevo = forms.ModelChoiceField(queryset=FormaPago.objects.all(), label='Estado Nuevo Ticket: ')


class CabeceraInformeForm(forms.Form):
    fecha_desde = forms.DateField(widget=DateTimePicker(options={"format": "YYYY-MM-DD", "pickTime": False}))
    fecha_hasta = forms.DateField(widget=DateTimePicker(options={"format": "YYYY-MM-DD", "pickTime": False}))


class FacturaClienteForm(forms.ModelForm):

    class Meta:
        model = ClienteFactura
        fields = ('nombre', 'ruc')

    def clean(self):
        return self.cleaned_data


class FacturaAgregarForm(forms.ModelForm):

    class Meta:
        model = Factura
        fields = ('numero', 'fecha', 'plazo', 'total', 'cliente')
        widgets = {
            'total': forms.TextInput(attrs={'readonly': True}),
            'cliente': forms.HiddenInput()
        }

    def clean(self):
        return self.cleaned_data