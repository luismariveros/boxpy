#encoding=utf8
from django import forms
from pytrade.apps.home.models import Cliente, Vendedor, Sucursal
from pytrade.apps.backend.models import Compra, CompraDetalle


class ClienteAgregarCompraForm(forms.ModelForm):

    class Meta:
        model = CompraDetalle
        fields = ('enlace', 'descripcion', 'comentario')


def sucursalChoice():
    choices = []
    for choice in Sucursal.objects.filter(is_active=True):
        choices.append([choice.id, choice.nombre])
    return choices


class ClienteForm(forms.ModelForm):

    class Meta:
        model = Cliente
        fields = ('cedula', 'ruc', 'celular', 'telefono', 'direccion', 'vendedor', 'sucursal')

    def __init__(self, *args, **kwargs):
        super(ClienteForm, self).__init__(*args, **kwargs)
        self.fields['sucursal'].choices = sucursalChoice()
        self.fields['sucursal'].label = 'Retirar de'

    def clean(self):
        return self.cleaned_data


class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(), label="Email")
    password = forms.CharField(widget=forms.PasswordInput(render_value=False), label="Contraseña")


class RegistrarForm(forms.Form):
    nombre = forms.CharField(widget=forms.TextInput(attrs={'class': 'input required'}))
    apellido = forms.CharField(widget=forms.TextInput(attrs={'class': 'input required'}))
    password = forms.CharField(widget=forms.PasswordInput(render_value=False, attrs={'class': 'input required',
                                                                                     'minlength': '5'}),
                               label='Contraseña')
    password2 = forms.CharField(widget=forms.PasswordInput(render_value=False, attrs={'class': 'input required',
                                                                                      'equalTo': '#id_password'}),
                                label='Contraseña')
    email = forms.EmailField(widget=forms.TextInput(attrs={'class': 'input required email'}))
    cedula = forms.CharField(widget=forms.TextInput(attrs={'class': 'input required digits'}),
                             label='Cédula')
    celular = forms.CharField(widget=forms.TextInput(attrs={'class': 'input required digits',
                                                            'placeholder': 'Ej. 09XX957518'}))
    telefono = forms.CharField(widget=forms.TextInput(attrs={'class': 'input',
                                                             'placeholder': 'Ej. 021681578'}),
                               label='Teléfono', required=False)
    ruc = forms.CharField(widget=forms.TextInput(attrs={'class': 'input', 'maxlength': '20',
                                                        'placeholder': 'Ej. 29584730-9'}),
                          required=False)
    direccion = forms.CharField(widget=forms.TextInput(attrs={'class': 'extend'}),
                                label='Dirección', required=False)
    sucursal = forms.ModelChoiceField(queryset=Sucursal.objects.filter(is_active=True).order_by('id'),
                                      widget=forms.Select(attrs={'class': 'input required'}),
                                      label='Retirar los paquetes de', empty_label=None)
    vendedor = forms.ModelChoiceField(queryset=Vendedor.objects.filter(user__is_active=True).order_by('id'),
                                      label='Invitado por...', required=False)

    def clean(self):
        return self.cleaned_data
