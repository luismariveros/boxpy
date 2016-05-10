#encoding=utf8
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponse
from django.template import RequestContext, Context
from django.template.loader import get_template
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core import serializers
from django.core.mail import EmailMultiAlternatives
from django.core.urlresolvers import reverse
from django.conf import settings
from pytrade.apps.home.forms import ClienteForm, LoginForm, RegistrarForm, ClienteAgregarCompraForm
from pytrade.apps.home.models import Cliente
from pytrade.apps.backend.models import Configuracion, Compra, CompraDetalle, Paquete
from datetime import date
import simplejson
import random
import os


def generar_codigo():
    config = Configuracion.objects.get(id=1)
    ultimo_valor = config.ultimo_valor
    CODE = str(random.randrange(ultimo_valor * 10000, ultimo_valor * 10000 + 9999))
    while True:
        if not Cliente.objects.filter(codigo__endswith=CODE):
            break
        else:
            CODE = str(random.randrange(ultimo_valor * 10000, ultimo_valor * 10000 + 9999))

    if ultimo_valor == 9:
        nuevo_valor = 1
    else:
        nuevo_valor = ultimo_valor + 1

    config.ultimo_valor = nuevo_valor
    config.save()
    return CODE


def envio_mail(clientes, archivo, datos=None, bcc=None, request=None):
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError

    band = 0  # El parametro clientes es de tipo USER
    htmly = get_template('emails/' + archivo + '.html')
    origen = 'PyTrade <no-reply@pytrade.com.py>'

    if isinstance(clientes[0], Cliente):
        band = 1  # El parametro clientes es de tipo CLIENTE

    if archivo == 'bienvenido':
        asunto = '[PyTrade] Usuario creado en PyTrade.com.py'


    if archivo == 'paquetes_1':  # Notifica paquetes en Miami (id=1)
        asunto = '[PyTrade] Paquete recibido en Miami'

    if archivo == 'paquetes_2':  # Notifica paquetes en Asuncion (id=2)
        asunto = '[PyTrade] Paquete recibido en Asunción'

    for cliente in clientes:
        if datos:
            if len(datos) == 1:
                d = Context({'cliente': cliente, 'datos': datos[0]})
            else:
                d = Context({'cliente': cliente, 'datos': datos[0], 'datos_extra': datos[1]})
        else:
            d = Context({'cliente': cliente})

        if band:
            destino = 'riveros@gmail.com' if settings.DESARROLLO else cliente.user.email
        else:
            destino = 'riveros@gmail.com' if settings.DESARROLLO else cliente.email

        try:
            validate_email(destino)
            html_content = htmly.render(d)
            copia = None if settings.DESARROLLO else bcc
            if copia:
                msg = EmailMultiAlternatives(asunto, html_content, origen, [destino], bcc=[copia])
            else:
                msg = EmailMultiAlternatives(asunto, html_content, origen, [destino])
            msg.attach_alternative(html_content, 'text/html')
            msg.send()
        except ValidationError:
            if cliente.get_full_name():
                messages.error(request, "Error en el mail de " + cliente.get_full_name())
            else:
                msj = "Error en el mail. Enviar sus datos a info@pytrade.com.py para solucionar."
                messages.error(request, msj)


def envio_mail_compra(cliente, compra, bcc=None):
    htmly = get_template('emails/compras-solitud.html')
    origen = 'PyTrade <no-reply@pytrade.com.py>'
    destino = 'riveros@gmail.com' if settings.DESARROLLO else settings.TO_COMPRAS
    asunto = '[PyTrade] Solicitud de Cotización'

    d = Context({'cliente': cliente, 'compra': compra})
    html_content = htmly.render(d)

    copia = None if settings.DESARROLLO else bcc
    if copia:
        msg = EmailMultiAlternatives(asunto, html_content, origen, [destino], bcc=[copia])
    else:
        msg = EmailMultiAlternatives(asunto, html_content, origen, [destino])
    msg.attach_alternative(html_content, 'text/html')
    msg.send()


def index_view(request):
    path = os.path.normpath(os.path.join(settings.MEDIA_ROOT, 'images/slider'))
    path2, dirs, files = os.walk(path).next()
    ctx = {'archivos': sorted(files)}
    return render_to_response('home/index.html', ctx, context_instance=RequestContext(request))


def preguntas_view(request):
    return render_to_response('home/faq.html', context_instance=RequestContext(request))


def tiendas_view(request):
    return render_to_response('home/tiendas.html', context_instance=RequestContext(request))


def servicio_view(request):
    return render_to_response('home/servicio.html', context_instance=RequestContext(request))


def empresa_view(request):
    return render_to_response('home/empresa.html', context_instance=RequestContext(request))


def tarifa_view(request):
    return render_to_response('home/tarifa.html', context_instance=RequestContext(request))


def contacto_view(request):
    return render_to_response('home/contacto.html', context_instance=RequestContext(request))


@login_required()
def comprar_view(request):
    if request.method == "POST":
        form = ClienteAgregarCompraForm(request.POST)
        if form.is_valid():
            # Obtener los datos del POST
            enlace_list = request.POST.getlist('enlace')
            descripcion_list = request.POST.getlist('descripcion')
            comentario_list = request.POST.getlist('comentario')
            compra = Compra(user=request.user, fecha_solicitud=date.today())
            compra.save()

            # Guardar todas las COMPRAS_DETALLES y asociar a Compra
            for i in range(len(enlace_list)):
                compra_detalle = CompraDetalle(enlace=enlace_list[i],
                                               descripcion=descripcion_list[i],
                                               comentario=comentario_list[i],
                                               fecha_solicitud=date.today(),
                                               estado='PC')
                compra_detalle.save()
                compra.detalle.add(compra_detalle)
            compra.save()

            messages.success(request, 'Solicitud de Compra recibida correctamente.')
            messages.info(request, 'Recibirá un mail de Cotización de la Órden de Compra en la brevedad posible.')
            return HttpResponseRedirect(reverse('vista_profile'))
        else:
            form = ClienteAgregarCompraForm(request.POST)
            ctx = {'form': form}
            return render_to_response('home/comprar.html', ctx, context_instance=RequestContext(request))
    else:
        form = ClienteAgregarCompraForm()
        ctx = {'form': form}
        return render_to_response('home/comprar.html', ctx, context_instance=RequestContext(request))


@login_required()
def profile_view(request):
    cliente = Cliente.objects.get(user=request.user)
    paquetes = Paquete.objects.filter(user=request.user, entregado=False)
    compras = Compra.objects.filter(user=request.user, pagado=False)
    msj = 1 if not cliente.codigo else 0
    ctx = {'msj': msj, 'paquetes': paquetes, 'compras': compras}
    return render_to_response('home/profile.html', ctx, context_instance=RequestContext(request))


@login_required()
def cliente_historial_view(request):
    cliente = Cliente.objects.get(user=request.user)
    paquetes = Paquete.objects.filter(user=request.user).order_by('-id')
    compras = Compra.objects.filter(user=request.user).order_by('-id')
    msj = 1 if not cliente.codigo else 0
    ctx = {'msj': msj, 'paquetes': paquetes, 'compras': compras}
    return render_to_response('home/historial.html', ctx, context_instance=RequestContext(request))


def login_view(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect('/')
    else:
        error = None
        redirect_to = request.REQUEST.get('next', '')
        print redirect_to
        if request.method == "POST":
            form = LoginForm(request.POST)
            if form.is_valid():
                username = form.cleaned_data['username']
                password = form.cleaned_data['password']
                usuario = authenticate(username=username, password=password)
                if usuario is not None and usuario.is_active:
                    login(request, usuario)
                    if redirect_to:
                        return HttpResponseRedirect(redirect_to)
                    return HttpResponseRedirect('/profile')
                else:
                    form = LoginForm()
                    error = "Datos incorrectos."
            else:
                form = LoginForm()
                error = "Debe completar todos los datos."
        else:
            form = LoginForm()
        ctx = {'form': form, 'error': error}
        return render_to_response('home/login.html', ctx, context_instance=RequestContext(request))


def registrar_view(request):
    if request.method == "POST":
        form = RegistrarForm(request.POST)
        if check_email(request.POST.get('email')):  # Habia errores en el AJAX por eso valido aca
            form = RegistrarForm(request.POST)
            print 'ERROR: El mail es {0}'.format(request.POST.get('email'))
            ctx = {'form': form, 'error': True}
            return render_to_response('home/registrar.html', ctx, context_instance=RequestContext(request))
        else:
            if form.is_valid():
                #Obtener los datos del POST
                nombre = form.cleaned_data['nombre']
                apellido = form.cleaned_data['apellido']
                email = form.cleaned_data['email']
                password = form.cleaned_data['password']
                cedula = form.cleaned_data['cedula']
                celular = form.cleaned_data['celular']
                telefono = form.cleaned_data['telefono']
                direccion = form.cleaned_data['direccion']
                ruc = form.cleaned_data['ruc']
                sucursal = form.cleaned_data['sucursal']
                vendedor = form.cleaned_data['vendedor']
                codigo = generar_codigo()

                # Crear Usuario
                user = User()
                user.username = email.lower()
                user.set_password(password)
                user.email = email.lower()
                user.first_name = nombre.title()
                user.last_name = apellido.title()
                user.save()

                # Crear Cliente y asociar con Usuario
                p = Cliente()
                p.user = user
                p.codigo = codigo
                p.cedula = cedula
                p.celular = celular
                p.telefono = telefono
                p.direccion = direccion.title()
                p.ruc = ruc
                p.completo = True
                if vendedor is None:
                    p.categoria_id = 1
                p.sucursal = sucursal
                p.vendedor = vendedor
                p.save()

                # Enviar por Mail al Cliente
                envio_mail(clientes=[p], archivo='bienvenido', bcc='nuevo@pytrade.com.py')
                ctx = {'form': RegistrarForm(), 'registro_exito': True}
                return render_to_response('home/registrar.html', ctx, context_instance=RequestContext(request))
            else:
                form = RegistrarForm(request.POST)
                ctx = {'form': form}
                return render_to_response('home/registrar.html', ctx, context_instance=RequestContext(request))
    else:
        form = RegistrarForm()
        ctx = {'form': form}
        return render_to_response('home/registrar.html', ctx, context_instance=RequestContext(request))


def check_email(email):
    #data = Cliente.objects.filter(user__email=email)
    data = User.objects.filter(email=email)
    if len(data) > 0:
        return True
    else:
        return False


@login_required
def logout_view(request):
    logout(request)
    return HttpResponseRedirect('/')


@login_required
def perfil_usuario_view(request):
    error = msj = ""
    if request.method == 'POST':
        cliente = request.user.profile
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            if not cliente.codigo:
                cliente.codigo = generar_codigo()
                cliente.completo = True
                cliente.save()
                envio_mail(clientes=[cliente], archivo='bienvenido', bcc='nuevo@pytrade.com.py')
            form.save()
            ctx = {'msj': 3}  # Actualización correcta de Datos
            return render_to_response('home/profile.html', ctx, context_instance=RequestContext(request))
        else:
            form = ClienteForm(request.POST)
            error = 'Error en algún campo.'
            ctx = {'form': form, 'msj': msj, 'cliente': cliente, 'error': error}
            return render_to_response('home/perfil.html', ctx, context_instance=RequestContext(request))
    else:
        user = request.user
        profile = user.profile
        form = ClienteForm(instance=profile)
        #cliente = Cliente.objects.get(user=user)
        if not profile.codigo:
            msj = 1  # El msj debe ser para el primer registro
        elif not profile.completo:
            msj = 2  # El msj debe ser que esta incompleto el perfil
        ctx = {'form': form, 'msj': msj, 'cliente': profile, 'error': error}
        return render_to_response('home/perfil.html', ctx, context_instance=RequestContext(request))


def wsemail_view(request):
    email = request.POST.get('email')
    data = Cliente.objects.filter(user__email=email)
    if len(data) > 0:
        return HttpResponse('{"response": "used"}', mimetype='application/json')
    else:
        return HttpResponse('{"response": "nodata"}', mimetype='application/json')


def parsear(tipo, data):
    return serializers.serialize(tipo, data, use_natural_keys=True)


def wscodigo_view(request):
    codigo = request.POST.get('codigo_cliente')
    data = Cliente.objects.filter(codigo=codigo)
    if len(data) > 0:
        nombre = data[0].user.get_full_name().encode('utf-8')
        return HttpResponse(simplejson.dumps(nombre), mimetype='application/json')
    else:
        return HttpResponse('{"response": "nodata"}', mimetype='application/json')

# Rest Framework
# from rest_framework import generics, permissions
# from rest_framework.exceptions import NotFound
# from pytrade.apps.home.serializers import PrePaqueteSerializer, UserSerializer
# from django.core.exceptions import ObjectDoesNotExist
#
#
# class wsagregar_prepaquete(generics.CreateAPIView):
#     queryset = PrePaquete.objects.all()
#     serializer_class = PrePaqueteSerializer
#     permission_classes = (permissions.IsAuthenticated, )
#
#     def perform_create(self, serializer):
#         codigo_cliente = self.request.data['codigo_cliente']
#         try:
#             Cliente.objects.get(codigo=codigo_cliente[-5:])
#         except ObjectDoesNotExist:
#             raise NotFound(detail='Codigo Cliente %s no existe' % codigo_cliente)
#         else:
#             serializer.save(owner=self.request.user)
#
#
# class UserList(generics.ListAPIView):
#     queryset = User.objects.all()
#     serializer_class = UserSerializer