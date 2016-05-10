#encoding=utf8
from django.forms.formsets import formset_factory
from django.forms import TextInput
from django.forms.models import modelformset_factory
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext, Context
from django.template.loader import render_to_string, get_template
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test, permission_required
from django.contrib.auth.models import User
from pytrade.apps.home.models import *
from pytrade.apps.backend.models import *
#from pytrade.apps.backend.filters import *
from django.core import serializers
from django.core.urlresolvers import reverse
from django.core.mail import EmailMultiAlternatives
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponseRedirect, HttpResponse
from django.db import transaction
from pytrade.apps.home.forms import ClienteAgregarCompraForm
from pytrade.apps.backend.forms import *
from django.core.exceptions import ObjectDoesNotExist
from pytrade.apps.home.views import envio_mail
from datetime import date, datetime, timedelta
from django.conf import settings
from django.db.models import Sum, Count, Max
import ho.pisa as pisa
import cStringIO as StringIO
import cgi
import csv
import simplejson
import sys
import os
from decimal import Decimal
from math import ceil
# Archivos python externos
from pytrade.apps.backend.informes import *
from pytrade.apps.backend.funciones import *

# Impresion de Codigo de Barras en PDF
from reportlab.graphics.barcode import createBarcodeDrawing
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm


# Envio de mail a los Gerentes sobre el cierre.
def envio_mail_gerentes(sucursal, caja_apertura, caja_cierre):
    htmly = get_template('emails/caja-cierre.html')
    origen = 'PyTrade <no-reply@pytrade.com.py>'
    destino = 'riveros@gmail.com' if settings.DESARROLLO else sucursal.mail_gerente
    asunto = '[PyTrade] Caja cerrada'
    d = Context({'caja_apertura': caja_apertura, 'caja_cierre': caja_cierre})
    html_content = htmly.render(d)
    msg = EmailMultiAlternatives(asunto, html_content, origen, [destino])
    msg.attach_alternative(html_content, 'text/html')
    msg.send()


# Envio de mail al realizar la COTIZACION de una Compra.
def envio_mail_cotizacion(user, compra):
    htmly = get_template('emails/compra_cotizar.html')
    origen = 'PyTrade <no-reply@pytrade.com.py>'
    destino = 'riveros@gmail.com' if settings.DESARROLLO else user.email
    asunto = '[PyTrade] Cotización Órden de Compra'
    d = Context({'user': user, 'compra': compra})
    html_content = htmly.render(d)
    msg = EmailMultiAlternatives(asunto, html_content, origen, [destino], bcc=[settings.TO_COMPRAS])
    msg.attach_alternative(html_content, 'text/html')
    msg.send()


######
## Comienzo de view (asociados a urls)
######
@login_required()
@user_passes_test(verificar_login, login_url='/')
def index_view(request):
    ctx = {}
    return render_to_response('backend/index.html', ctx, context_instance=RequestContext(request))


# tipo=1, El Formulario de Resultado llama a paquete_entregar_view
# tipo=2, El Formulario de Resultado llama a comprarPedido_view
# tipo=3, El Formulario de Resultado llama a cliente_historial_view
@login_required()
@user_passes_test(verificar_login, login_url='/')
def cliente_busqueda_view(request, tipo):
    if request.GET:
        form = BusquedaClienteForm(request.GET)
        if form.is_valid():
            resultado = form.get_result_queryset()
        else:
            resultado = []
        ctx = {'form': form, 'resultado': resultado, 'tipo': tipo}
        return render_to_response('backend/resultado.html', ctx, context_instance=RequestContext(request))
    else:
        #if bool(request.user.groups.filter(name='Sucursales')):
        #    usuario = Usuario.objects.get(user=request.user)
        #    form = BusquedaClienteForm(initial={'sucursal': usuario.sucursal_id})
        #else:
        #    form = BusquedaClienteForm()
        form = BusquedaClienteForm()
        ctx = {'form': form, 'tipo': tipo}
        return render_to_response('backend/resultado.html', ctx, context_instance=RequestContext(request))


# Funcion para obtener el historial de un cliente
@login_required()
@user_passes_test(verificar_login, login_url='/')
def cliente_historial_view(request, user):
    cliente = Cliente.objects.get(user=user)
    paquetes = Paquete.objects.filter(user=user).order_by('-fecha')
    tickets = filtrar_sucursal(request.user, Ticket.objects.filter(user=user).order_by('-fecha'))
    info_paquetes = paquetes.aggregate(peso=Sum('peso'), cantidad=Count('id'))
    info_tickets = tickets.aggregate(cantidad=Count('id'), cantidad_paquete=Sum('cantidad_paquete'),
                                     total_kilo=Sum('peso_cobrado'), total_gs=Sum('monto_gs'), total_dolar=Sum('monto_dolar'))
    ctx ={'paquetes': paquetes, 'cliente': cliente, 'tickets': tickets, 'info_paquetes': info_paquetes, 'info_tickets': info_tickets}
    return render_to_response('backend/cliente_historial.html', ctx, context_instance=RequestContext(request))


# Funcion para entregar los paquetes que estan en Asunción filtrado por cliente
@login_required()
@user_passes_test(verificar_login, login_url='/')
def paquete_entregar_view(request, user):
    if not filtrar_sucursal(request.user, Caja.objects.filter(tipo='APERTURA', cerrada=False)):
        messages.error(request, 'No hay caja abierta. Realizar la Apertura de Caja primero.')
        return HttpResponseRedirect(reverse('vista_backend'))

    if request.POST:
        form = PaqueteEntregarForm(request.POST)
        if form.is_valid():
            peso_total_cobrado = form.cleaned_data.get('pesocobrado')
            monto_cobrado_gs = form.cleaned_data.get('cobrado_gs')
            monto_cobrado_dolar = form.cleaned_data.get('cobrado_dolar')
            contrato = form.cleaned_data.get('contrato')
            delivery = form.cleaned_data.get('delivery')
            paquetes_list = request.POST.getlist('paquetes[]')
            montopago_list = request.POST.getlist('montopago[]')
            formapago_list = request.POST.getlist('formapago')
            moneda_lista = request.POST.getlist('moneda')

            cli = Cliente.objects.get(user=user)
            if contrato:  # El cliente firmo el contrato
                cli.contrato = True
                cli.save()

            paquetes = Paquete.objects.filter(id__in=paquetes_list)
            if paquetes:  # Este control lo realizo debido a que algunas veces guardo 2 Tickets de un mismo cliente.
                peso_total_sistema = monto_total_seguro = 0
                for p in paquetes:
                    peso_total_sistema += p.peso
                    monto_total_seguro += p.costo_seguro
                    p.entregado = True
                    p.save()

                # Genero un ticket para asociar a los paquetes entregados
                ticket = Ticket()
                ticket.user = cli.user
                ticket.cantidad_paquete = paquetes.count()
                ticket.peso_cobrado = peso_total_cobrado
                ticket.peso_sistema = peso_total_sistema
                ticket.monto_gs = monto_cobrado_gs
                ticket.monto_dolar = monto_cobrado_dolar
                ticket.monto_seguro = monto_total_seguro
                ticket.sucursal = get_sucursal(request.user)
                ticket.save()
                ticket.paquete = paquetes

                # Guardar todos los pagos y asociar al Ticket
                for i in range(len(montopago_list)):
                    pago = Pago(monto=montopago_list[i], formapago_id=formapago_list[i], moneda_id=moneda_lista[i])
                    pago.save()
                    ticket.pago.add(pago)
                ticket.save()

                ctx = {'cliente': cli, 'paquetes': paquetes, 'ticket': ticket, 'pagos': ticket.pago.all()}
                html = render_to_string('backend/ticket_pdf.html', ctx, context_instance=RequestContext(request))

                return generar_pdf(html)
            else:
                messages.error(request, 'El Cliente no tiene paquetes en esta sucursal.')
                return HttpResponseRedirect(reverse('vista_backend'))
        else:
            print form.errors
            messages.error(request, form.errors)
            #form = EntregarPaquetesForm(request.POST)
            #ctx = {'form': form}
            #return render_to_response('backend/paquete_entregar.html', ctx, context_instance=RequestContext(request))
            return HttpResponseRedirect(reverse('vista_backend'))
    else:
        peso_total_sistema = precioxkilo = monto_total_seguro = monto_total_sistema_gs = monto_total_sistema_dolar = 0
        try:
            cli = Cliente.objects.get(user=user)
            try:
                #paquetes_gral = Paquete.objects.filter(user=cli.user, ubicacion__fisica=True).exclude(entregado=True)
                paquetes_gral = Paquete.objects.filter(user=cli.user,ubicacion__codigo='ASU').exclude(entregado=True)
                paquetes = filtrar_sucursal(request.user, paquetes_gral)
                if bool(request.user.groups.filter(name='Sucursales')):
                    if not paquetes.count():
                        messages.error(request, 'El Cliente no tiene paquetes en esta sucursal.')
                        if paquetes_gral.count():
                            msj = 'El Cliente tiene ' + str(paquetes_gral.count()) + ' paquete/s en la sucursal ' + str(paquetes_gral[0].sucursal)
                            messages.info(request, msj)
                        return HttpResponseRedirect(reverse('vista_backend'))

                #tickets_gs = tickets.filter(pago__moneda=Moneda.objects.get(codigo='Gs')).values('pago__formapago').annotate(total=Sum('pago__monto'))
                #paquetes_peso_total = paquetes.aggregate(peso_total=Sum('peso'))
                info_paquetes = paquetes.aggregate(peso=Sum('peso'), cantidad=Count('id'))

                #if info_paquetes['peso'] >= 10:
                #    costo_kilo = Categoria.objects.get(nombre='Promo').costo
                #else:
                #    costo_kilo = cli.categoria.costo
                costo_kilo = cli.categoria.costo
                dolar = Moneda.objects.get(codigo='USD').cotizacion
                monto_minimo = Configuracion.objects.get(id=1).monto_minimo

                for p in paquetes:
                    p.dolar = dolar
                    p.costo_envio_gs = calcular_costo_gs(p.peso, costo_kilo, dolar)
                    p.costo_envio_dolar = calcular_costo_dolar(p.peso, costo_kilo, dolar, p.costo_envio_gs)
                    p.save()
                    peso_total_sistema += p.peso
                    monto_total_seguro += p.costo_seguro
                    monto_total_sistema_gs += p.costo_envio_gs
                    monto_total_sistema_dolar += p.costo_envio_dolar

                if monto_total_sistema_gs <= Configuracion.objects.get(id=1).monto_minimo:
                    monto_total_sistema_gs = Configuracion.objects.get(id=1).monto_minimo
                    monto_total_sistema_dolar = round(monto_total_sistema_gs / Decimal(dolar), 2)

                if not cli.contrato:
                    messages.error(request, 'El Cliente debe firmar el Contrato.')
            except ObjectDoesNotExist:
                paquetes = None
        except ObjectDoesNotExist:
            cli = paquetes = None
            peso_total_sistema = monto_total_seguro = precioxkilo = 0
        form = PaqueteEntregarForm(initial={'pesocobrado': peso_total_sistema,
                                             'cobrado_gs': monto_total_sistema_gs,
                                             'cobrado_dolar': monto_total_sistema_dolar,
                                             'formapago': FormaPago.objects.get(codigo='EF'),
                                             'moneda': Moneda.objects.get(codigo='Gs')})

        ctx = {'form': form, 'cliente': cli, 'paquetes': paquetes, 'montocobrado': monto_total_sistema_gs,
               'peso': peso_total_sistema, 'costo_kilo': costo_kilo, 'costo_seguro': monto_total_seguro,
               'monto_total_dolar': monto_total_sistema_dolar, 'monto_minimo': monto_minimo}
        return render_to_response('backend/paquete_entregar.html', ctx, context_instance=RequestContext(request))


@login_required()
@user_passes_test(verificar_login, login_url='/')
def wspaquete_entregar_view(request):
    try:
        cliente_user = request.POST.get('cliente_user')
        peso_total_cobrado = request.POST.get('pesocobrado')
        monto_cobrado_gs = request.POST.get('cobrado_gs')
        monto_cobrado_dolar = request.POST.get('cobrado_dolar')
        contrato = request.POST.get('contrato')
        delivery = request.POST.get('delivery')
        paquetes_list = request.POST.getlist('paquetes[]')
        montopago_list = request.POST.getlist('montopago[]')
        formapago_list = request.POST.getlist('formapago')
        moneda_list = request.POST.getlist('moneda')

        cliente = Cliente.objects.get(user__username=cliente_user)

        if contrato:  # El cliente firmo el contrato
            cliente.contrato = True
            cliente.save()

        paquetes = Paquete.objects.filter(id__in=paquetes_list)
        if paquetes:  # Este control lo realizo debido a que algunas veces guardo 2 Tickets de un mismo cliente.
            peso_total_sistema = monto_total_seguro = 0
            for p in paquetes:
                peso_total_sistema += p.peso
                monto_total_seguro += p.costo_seguro
                p.entregado = True
                if delivery:
                    p.delivery = True
                p.save()

            # Genero un ticket para asociar a los paquetes entregados
            ticket = Ticket()
            ticket.user = cliente.user
            ticket.cantidad_paquete = paquetes.count()
            ticket.peso_cobrado = peso_total_cobrado
            ticket.peso_sistema = peso_total_sistema
            ticket.monto_gs = monto_cobrado_gs
            ticket.monto_dolar = monto_cobrado_dolar
            ticket.monto_seguro = monto_total_seguro
            ticket.sucursal = get_sucursal(request.user)
            ticket.save()
            ticket.paquete = paquetes

            # Guardar todos los pagos y asociar al Ticket
            for i in range(len(montopago_list)):
                pago = Pago(monto=montopago_list[i], formapago_id=formapago_list[i], moneda_id=moneda_list[i])
                pago.save()
                ticket.pago.add(pago)
            ticket.save()
    except:
        msj = 'ERROR Inesperado. %s' % sys.exc_info()
        return HttpResponse('{"response": "Error"}', mimetype='application/json')
    t = Ticket.objects.filter(id=ticket.id)
    return HttpResponse(parsear(t), mimetype='application/json')



@login_required()
@user_passes_test(verificar_login, login_url='/')
def paquete_list_view(request):
    p = filtrar_sucursal(request.user, Paquete.objects.filter(entregado=False)).order_by('-id')
    for x in p:
        if x.carga_set.count() > 1:
            print x, x.id, x.carga_set.all()
    miami = p.filter(ubicacion__codigo='MIA').count()
    transito = p.filter(ubicacion__codigo='TRAN').count()
    noentregado = p.filter(ubicacion__codigo='ASU').count()
    delivery = p.filter(ubicacion__codigo='ASU', delivery=True).count()
    ctx = {'paquetes': p, 'miami': miami, 'transito': transito, 'noentregado': noentregado, 'delivery': delivery}
    return render_to_response('backend/paquete_list.html', ctx, context_instance=RequestContext(request))


@login_required()
@user_passes_test(verificar_login, login_url='/')
def paquete_agrupar_list(request):
    paquetes = Paquete.objects.filter(ubicacion__codigo='ASU', entregado=False).values('user').order_by('-cant').annotate(cant=Count('id'))

    for p in paquetes:
        user = User.objects.get(id=p['user'])
        p['user'] = user

    ctx = {'paquetes': paquetes}
    return render_to_response('backend/paquete_agrupar_list.html', ctx, context_instance=RequestContext(request))


@login_required()
@user_passes_test(verificar_login, login_url='/')
def ticket_list_view(request):
    tickets = filtrar_sucursal(request.user, Ticket.objects.all().order_by('-fecha'))

    paginator = Paginator(tickets, 200)

    page = request.GET.get('page')
    try:
        t = paginator.page(page)
        page = int(page)
    except PageNotAnInteger:
        t = paginator.page(1)
    except EmptyPage:
        t = paginator.page(paginator.num_pages)

    lista = [1]
    if paginator.num_pages > 1 and type(page) is int():
        lista = set([1, 2, page-1, page, page+1, paginator.num_pages-1, paginator.num_pages])

    if page == 1:
        lista.remove(0)

    ctx = {'tickets': t, 'lista': lista}
    return render_to_response('backend/ticket_list.html', ctx, context_instance=RequestContext(request))


@login_required()
@user_passes_test(verificar_login, login_url='/')
def cliente_list_view(request):
    c = filtrar_sucursal(request.user, Cliente.objects.all()).order_by('-id')
    ctx = {'clientes': c}
    return render_to_response('backend/cliente_list.html', ctx, context_instance=RequestContext(request))


# Funciones:
# 1) Listar las compras. 2) Borrar una compra si user tiene permiso
# El borrado se realiza a traves de Modal y llamada Ajax (backend-compras.js)
@login_required()
@user_passes_test(verificar_login, login_url='/')
def compra_list_view(request):
    if request.method == 'POST':
        if "compra_id" in request.POST:
            try:
                compra_id = request.POST['compra_id']
                c = Compra.objects.get(pk=compra_id)
                mensaje = {"status": "True", "compra_id": c.id}
                c.delete()  # Eliminar el registro
                return HttpResponse(simplejson.dumps(mensaje), mimetype='application/json')
            except:
                mensaje = {"status": "False"}
                return HttpResponse(simplejson.dumps(mensaje), mimetype='application/json')

    #filtro = CompraFilter(request.GET, queryset=Compra.objects.all())
    #print filtro.qs
    #paginator = Paginator(filtro.qs, 15)
    #page = request.GET.get('page')
    #try:
    #    d = paginator.page(page)
    #except PageNotAnInteger:
    #    d = paginator.page(1)
    #except EmptyPage:
    #    d = paginator.page(paginator.num_pages)

    # Parche para que funcione Filter con Paginator
    #from django.utils.encoding import iri_to_uri
    #parametros = request.GET.copy()
    #if parametros.get('page'):
    #    parametros.pop("page")
    #parametros = '&' + iri_to_uri(parametros.urlencode()) if parametros else ''

    #ctx = {'datos': d, 'filtro': filtro, 'parametros': parametros}
    ctx = {'datos': Compra.objects.all().order_by('-fecha_solicitud')}
    return render_to_response('backend/compra_list.html', ctx, context_instance=RequestContext(request))


@login_required()
@user_passes_test(verificar_login, login_url='/')
def carga_list_view(request):
    cargas = Carga.objects.all().order_by('-id')
    #f = CargaFilter(request.GET, queryset=Carga.objects.all().order_by('-id'))
    paginator = Paginator(cargas, 15)

    page = request.GET.get('page')
    try:
        c = paginator.page(page)
    except PageNotAnInteger:
        c = paginator.page(1)
    except EmptyPage:
        c = paginator.page(paginator.num_pages)
    ctx = {'cargas': c}
    return render_to_response('backend/carga_list.html', ctx, context_instance=RequestContext(request))


@login_required()
@user_passes_test(verificar_login, login_url='/')
def caja_list_view(request):
    cajas = filtrar_sucursal(request.user, Caja.objects.filter(tipo='CIERRE').order_by('-created_at'))
    paginator = Paginator(cajas, 15)

    page = request.GET.get('page')
    try:
        c = paginator.page(page)
    except PageNotAnInteger:
        c = paginator.page(1)
    except EmptyPage:
        c = paginator.page(paginator.num_pages)
    ctx = {'cajas': c}
    return render_to_response('backend/caja_list.html', ctx, context_instance=RequestContext(request))


@login_required()
@user_passes_test(verificar_login, login_url='/')
def manifiesto_list_view(request):
    manifiestos = Manifiesto.objects.all().order_by('-created_at')
    paginator = Paginator(manifiestos, 15)

    page = request.GET.get('page')
    try:
        m = paginator.page(page)
    except PageNotAnInteger:
        m = paginator.page(1)
    except EmptyPage:
        m = paginator.page(paginator.num_pages)
    ctx = {'manifiestos': m}
    return render_to_response('backend/manifiesto_list.html', ctx, context_instance=RequestContext(request))


@login_required()
@user_passes_test(verificar_login, login_url='/')
def carga_importar_view(request):
    if request.method == 'POST':
        form = CargaForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.commit_manually():
                origen = form.cleaned_data.get('origen')
                nombre_archivo = request.FILES['archivo']
                carga = Carga(archivo=request.FILES['archivo'], origen=origen)
                carga.save()
                suma_kilos = 0
                error = False

                # Procesar cabecera de la carga
                if origen.nombre == "Asuncion":
                    kilo_carga = form.cleaned_data.get('kilo_carga')
                    carga_asociada = form.cleaned_data.get('carga_asociada')
                    carga.carga_asociada = carga_asociada
                    carga.kilo_carga = kilo_carga

                archivo_csv = csv.reader(open(settings.MEDIA_ROOT + '/' + carga.archivo.__str__()), delimiter=';')
                for i, registro in enumerate(archivo_csv):
                    if i > 0:  # La primera linea no se procesa
                        try:
                            if origen.nombre == 'Miami':
                                import random
                                fecha = registro[0].split('/')
                                codigo_cliente = registro[1].strip()  # Eliminar espacios
                                codigo_paquete = registro[2]
                                nombre = (registro[3].strip()).decode('utf-8').upper()
                                descripcion = registro[4]
                                peso = Decimal(registro[5].replace(',', '.')) if registro[5] else 0
                                tracking = registro[6] if registro[6] else '.'
                                nombre_proveedor = registro[7].strip().upper()
                                valor_dolar = Decimal(registro[8].replace(',', '.')) if registro[8] else random.randrange(20, 80)

                                # Controlar que el codigo_paquete no este en el sistema
                                if form.cleaned_data.get('controlar_warehouse') and Paquete.objects.filter(codigo=codigo_paquete).count():
                                    msj = '[Linea %s] Código Warehouse del Paquete ya existe en el sistema.' % (i+1)
                                    messages.error(request, msj)
                                    error = True
                                try:
                                    proveedor = Proveedor.objects.get(nombre=nombre_proveedor)
                                except ObjectDoesNotExist:
                                    msj = '[Linea %s] Proveedor %s no existe. Favor <a href="/backend/proveedor/">agregar.</a>' % (i+1, nombre_proveedor)
                                    messages.error(request, msj)
                                    error = True
                                else:
                                    try:
                                        user = Cliente.objects.select_related().get(codigo=codigo_cliente[-5:]).user

                                        # Controlar que el Codigo Cliente coincida con el Nombre Registrado
                                        if form.cleaned_data.get('controlar_nombre') and user.get_full_name().upper() != nombre:
                                            msj = "[Linea %s] " % (i+1)
                                            msj += user.get_full_name().upper() + " es distinto a " + registro[3]
                                            messages.error(request, msj)
                                            error = True

                                        paquete = Paquete()
                                        paquete_save(paquete, user, peso, codigo_paquete=codigo_paquete,
                                                     fecha="%s-%s-%s" % (fecha[0], fecha[1], fecha[2]),
                                                     descripcion=descripcion, tracking=tracking, ubicacion_id=origen.id,
                                                     proveedor=proveedor, valor_dolar=valor_dolar)
                                        carga.paquete.add(paquete)
                                        suma_kilos += peso
                                    except ObjectDoesNotExist:

                                        msj = '[Linea %s] Cliente NO existe. Código = %s.' % (i+1, codigo_cliente)
                                        messages.error(request, msj)
                                        error = True
                            if origen.nombre == 'Asuncion':
                                paquete_id = registro[0]
                                peso = Decimal(registro[6])
                                valor_dolar = Decimal(registro[7])
                                suma_kilos += peso

                                try:
                                    paquete = Paquete.objects.get(id=paquete_id)
                                    paquete_save(paquete, paquete.user, peso, ubicacion_id=origen.id,
                                                 fecha_destino=date.today(), valor_dolar=valor_dolar)
                                    carga.paquete.add(paquete)
                                    if carga_asociada:
                                        carga_asociada.paquete.add(paquete)
                                except ObjectDoesNotExist:
                                    messages.error(request, 'Paquete no encontrado.')
                                    error = True
                        except:
                            print 'entro'
                            msj = '[Linea %s] ERROR Inesperado. %s' % (i+1, sys.exc_info())
                            messages.error(request, msj)
                            error = True

                if error:
                    transaction.rollback()
                    os.remove(os.path.join(settings.MEDIA_ROOT, str(carga.archivo)))  # Eliminar el archivo creado
                    return HttpResponseRedirect(reverse('vista_importar_carga'))
                else:
                    carga.cantidad_paquetes = i
                    carga.kilos = suma_kilos
                    if origen.nombre == "Asuncion" and carga_asociada:
                        carga_asociada.kilos += suma_kilos
                        carga_asociada.save()

                    carga.save()
                    transaction.commit()
                    msj = 'Se cargó exitosamente el archivo \'%s\'. ' % nombre_archivo
                    messages.success(request, msj)
                    msj = 'Total de Kilos=%s, Cantidad de Paquetes=%s' % (suma_kilos, i)
                    messages.info(request, msj)
                    return HttpResponseRedirect(reverse('vista_lista_cargas'))
    else:
        form = CargaForm()
    cargas = Carga.objects.all().order_by('-id')[:10]
    ctx = {'form': form, 'cargas': cargas}
    return render_to_response('backend/carga_importar.html', ctx, context_instance=RequestContext(request))



@login_required()
@user_passes_test(verificar_login, login_url='/')
def paquete_agregar_view(request):
    if request.method == 'POST':
        form = PaqueteForm(request.POST)
        if form.is_valid():
            fecha = form.cleaned_data.get('fecha')
            codigo_cliente = form.cleaned_data.get('codigo_cliente')
            ubicacion = form.cleaned_data.get('ubicacion')
            peso = form.cleaned_data.get('peso')
            descripcion = form.cleaned_data.get('descripcion')
            tracking = form.cleaned_data.get('tracking')
            proveedor = form.cleaned_data.get('proveedor')
            codigo_paquete = form.cleaned_data.get('codigo')
            user = get_user('PT' + str(codigo_cliente))

            paquete = Paquete()
            if ubicacion == Ubicacion.objects.get(codigo='ASU'):
                paquete_save(paquete, user, peso, codigo_paquete=codigo_paquete, fecha=fecha - timedelta(days=7),
                             descripcion=descripcion, tracking=tracking, ubicacion_id=ubicacion.id,
                             proveedor=proveedor, fecha_destino=fecha)
            else:
                paquete_save(paquete, user, peso, codigo_paquete=codigo_paquete, fecha=fecha, descripcion=descripcion,
                             tracking=tracking, ubicacion_id=ubicacion.id, proveedor=proveedor)
            messages.success(request, 'Paquete agregado correctamente.')
            if '_addanother' in request.POST:
                return HttpResponseRedirect(reverse('vista_paquete_agregar'))
            if '_barcode' in request.POST:
                return generar_barcode(paquete.id)
            return HttpResponseRedirect(reverse('vista_backend'))
        else:
            form = PaqueteForm(request.POST)
    else:
        form = PaqueteForm(initial={'fecha': date.today(), 'ubicacion': Ubicacion.objects.get(codigo='MIA')})
    ctx = {'form': form, 'contenido': True}
    return render_to_response('backend/paquete_agregar_miami.html', ctx, context_instance=RequestContext(request))



@login_required()
@user_passes_test(verificar_login, login_url='/')
def paquete_editar_view(request, id=None):
    paquete = get_object_or_404(Paquete, pk=id) if id else Paquete()

    if request.method == 'POST':
        form = PaqueteEditarForm(request.POST, instance=paquete)
        if form.is_valid():

            user = paquete.user
            codigo_paquete = form.cleaned_data.get('codigo')
            # fecha = form.cleaned_data.get('fecha')
            # descripcion = form.cleaned_data.get('descripcion')
            peso = form.cleaned_data.get('peso')
            # tracking = form.cleaned_data.get('tracking')
            # ubicacion = form.cleaned_data.get('ubicacion')
            # proveedor = form.cleaned_data.get('proveedor')
            # #dolar = Moneda.objects.get(pk=2).cotizacion
            # #costo_kilo = Cliente.objects.get(user=user).categoria.costo
            # #costo_envio_dolar = ceil(peso * costo_kilo * 100) / 100  # Para redondear hacia arriba 2 decimales
            # #costo_envio_gs = costo_envio_dolar * dolar
            # #paquete_save(paquete, user, peso, fecha=fecha, descripcion=descripcion, tracking=tracking, ubicacion_id=ubicacion.id, proveedor=proveedor)

            paquete_save(paquete, user, peso)
            # paquete.user = user
            # paquete.fecha = fecha
            # paquete.descripcion = descripcion
            # paquete.peso = peso
            # paquete.tracking = tracking
            # paquete.ubicacion = ubicacion
            # paquete.dolar = dolar
            # paquete.costo_envio_dolar = costo_envio_dolar
            # paquete.costo_envio_gs = costo_gs(costo_envio_gs)
            # paquete.proveedor = proveedor
            # paquete.sucursal = Cliente.objects.get(user=user).sucursal
            # paquete.save()
            form.save()
            messages.success(request, 'Paquete actualizado correctamente')
            if '_addanother' in request.POST:
                return HttpResponseRedirect(reverse('vista_paquete_agregar'))
            return HttpResponseRedirect(reverse('vista_backend'))
            #return generar_barcode(paquete.id)
    else:
        form = PaqueteEditarForm(instance=paquete)
    ctx = {'form': form, 'editar': True}
    return render_to_response('backend/paquete_abm.html', ctx, context_instance=RequestContext(request))


@login_required()
@user_passes_test(verificar_login, login_url='/')
def paquete_exportar_view(request):
    if request.GET:
        form = ExportarPaqueteForm(request.GET)
        if form.is_valid():
            origen = form.cleaned_data.get('origen')

            # get the response object, this can be used as a stream.
            response = HttpResponse(mimetype='text/csv')
            # force download.
            response['Content-Disposition'] = 'attachment;filename="%s_%s.csv"' % (origen, date.today())

            # the csv writer
            writer = csv.writer(response, delimiter=';')

            paquetes = Paquete.objects.filter(ubicacion=origen).exclude(entregado=True)
            paquetes = filtrar_sucursal(request.user, paquetes).order_by('id')

            writer.writerow(['ID', 'Fecha', 'Codigo Paquete', 'Codigo Cliente', 'Nombre',
                             'Descripcion', 'Peso', 'Dolar', 'Tracking', 'Sucursal'])

            for p in paquetes:
                row = [str(p.id),
                       str(p.fecha),
                       str(p.codigo),
                       str(p.user.cliente.codigo),
                       str(p.user.first_name.encode('UTF-8', 'replace') + " " + p.user.last_name.encode('UTF-8', 'replace')),
                       str(p.descripcion.encode('UTF-8', 'replace')),
                       str(p.peso),
                       str(p.valor_dolar),
                       str(p.tracking.encode('UTF-8', 'replace') if p.tracking else '-'),
                       str(p.sucursal)]
                writer.writerow(row)
                #if p.id == 10112:
                #    print p.tracking, type(p.tracking), str(p.tracking)
            return response
    else:
        form = ExportarPaqueteForm()
        ctx = {'form': form}
        return render_to_response('backend/paquete_exportar.html', ctx, context_instance=RequestContext(request))


@login_required()
@user_passes_test(verificar_login, login_url='/')
def carga_detalle_view(request, id):
    carga = get_object_or_404(Carga, pk=id)
    #form = CargaForm(isinstance())
    ctx = {'carga': carga}
    return render_to_response('backend/carga_detalle.html', ctx, context_instance=RequestContext(request))


@login_required()
@user_passes_test(verificar_login, login_url='/')
def ticket_detalle_view(request, id):
    ticket = get_object_or_404(Ticket, pk=id)
    pagos = ticket.pago.all()
    cli = Cliente.objects.get(user_id=ticket.user_id)
    paquetes = ticket.paquete.all()
    ctx = {'cliente': cli, 'paquetes': paquetes, 'ticket': ticket, 'pagos': pagos}
    html = render_to_string('backend/ticket_pdf.html', ctx, context_instance=RequestContext(request))
    return generar_pdf(html)


@login_required()
@user_passes_test(verificar_login, login_url='/')
def factura_detalle_view(request, factura_id):
    factura = get_object_or_404(Factura, pk=factura_id)
    from num2es import TextNumber
    letras = unicode(TextNumber(int(factura.total))).upper()
    nro_decimal = factura.total - int(factura.total)
    if nro_decimal:
        n = int((factura.total - int(factura.total))*100)  # Obtengo el numero decimal en int
        letras += ' con ' + unicode(TextNumber(n)).upper()
    ctx = {'factura': factura, 'total_letras': letras, 'pagesize': 'A4'}
    html = render_to_string('backend/factura_pdf.html', ctx, context_instance=RequestContext(request))
    return generar_pdf(html)



@login_required()
@user_passes_test(verificar_login, login_url='/')
def factura_cliente_view(request, ticket_id):
    t = get_object_or_404(Ticket, pk=ticket_id)

    if request.method == 'POST':
        form = FacturaAgregarForm(request.POST)
        if form.is_valid():
            nro = form.cleaned_data.get('numero')
            plazo = form.cleaned_data.get('plazo')
            cliente = form.cleaned_data.get('cliente')
            factura = Factura()
            factura.cliente = cliente
            factura.sucursal = get_sucursal(request.user)
            factura.moneda = Moneda.objects.get(codigo='Gs')
            factura.numero = nro
            factura.monto_cambio = Moneda.objects.get(codigo='USD').cotizacion
            factura.fecha = date.today()
            factura.plazo = plazo
            factura.total = t.monto_gs
            factura.total_iva = 0
            factura.neto = 0
            factura.save()

            detalle = FacturaDetalle()
            detalle.ticket = t
            exenta = t.monto_gs * 75 / 100
            detalle.exenta = exenta
            detalle.iva = t.monto_gs - exenta
            detalle.factura = factura
            detalle.save()

            factura.total_iva = factura.get_total_iva() / 11
            factura.save()

            talonario = Talonario.objects.get(sucursal=get_sucursal(request.user))
            talonario.actual += 1
            talonario.save()

            return factura_detalle_view(request, factura.id)
    else:
        try:
            factura_anterior = FacturaDetalle.objects.get(ticket=ticket_id)
        except ObjectDoesNotExist:
            nro_factura = Talonario.objects.get(sucursal=get_sucursal(request.user)).actual
            facturas_sobrantes = Talonario.objects.get(sucursal=get_sucursal(request.user)).hasta - nro_factura
            c = ClienteFactura.objects.filter(cliente=t.user.cliente)
            form = FacturaAgregarForm(initial={'total': t.monto_gs, 'fecha': datetime.today(), 'numero': nro_factura})
            ctx = {'clientes': c, 'ticket': t, 'form': form}
            if facturas_sobrantes < 50:
                messages.error(request, 'Solicitar nuevo Talonario de Facturas. Sobran %s facturas' % facturas_sobrantes)
            return render_to_response('backend/factura_cliente_abm.html', ctx, context_instance=RequestContext(request))
        else:
            url = "/backend/factura/%s/" % factura_anterior.factura.id
            msj = 'Ya existe Factura del Ticket %s. <br />El Nro de Factura=%s del %s. ' % (t.id, factura_anterior.factura.numero, factura_anterior.factura.fecha)
            msj += '<a href="'+url+'" target="_blank">Ver</a>'
            messages.error(request, msj)
            return HttpResponseRedirect(reverse('vista_lista_tickets'))




@login_required()
@user_passes_test(verificar_login, login_url='/')
def manifiesto_detalle_view(request, id):
    manifiesto = get_object_or_404(Manifiesto, pk=id)
    ctx = {'manifiesto': manifiesto}
    return render_to_response('backend/manifiesto_detalle.html', ctx, context_instance=RequestContext(request))


def ticket_cambio_estado_view(request):
    if not filtrar_sucursal(request.user, Caja.objects.filter(tipo='APERTURA', cerrada=False)):
        messages.error(request, '<p>No hay caja abierta.</p>Realizar la Apertura de Caja primero.')
        return HttpResponseRedirect(reverse('vista_backend'))

    if request.method == 'POST':
        form = TicketEstadoForm(request.POST)
        tickets_list = request.POST.getlist('ticketsID[]')
        if form.is_valid():
            estado = form.cleaned_data.get('estado')
            estado_nuevo = form.cleaned_data.get('estado_nuevo')
            tickets = Ticket.objects.filter(id__in=tickets_list)
            for t in tickets:
                pagos = t.pago.filter(formapago=estado)
                for p in pagos:
                    p.formapago = estado_nuevo
                    p.save()
                t.fecha = datetime.now()
                t.save()
            messages.success(request, 'Se realizó correctamente el cambio de Estado de %s.' % len(tickets))
            return HttpResponseRedirect(reverse('vista_cambio_estado_ticket'))
    else:
        form = TicketEstadoForm()
    ctx = {'form': form}
    return render_to_response('backend/ticket_cambio_estado.html', ctx, context_instance=RequestContext(request))



@login_required()
@user_passes_test(verificar_login, login_url='/')
def caja_detalle_view(request, id):
    tickets_total_gs = tickets_total_dolar = ingresos_otros_total_gs = ingresos_otros_total_dolar = egreso_total_gs = egreso_total_dolar = compras_total_gs = compras_total_dolar = 0
    caja_solicitada = get_object_or_404(Caja, pk=id)
    caja_asociada = caja_solicitada.caja_asociada
    #print caja_solicitada.created_at
    #print caja_asociada.created_at

    fecha = caja_solicitada.created_at
    #print fecha
    efectivo_gs = caja_asociada.monto_gs
    efectivo_dolar = caja_asociada.monto_dolar

    # Tickets
    tickets = Ticket.objects.filter(fecha__year=fecha.year, fecha__month=fecha.month, fecha__day=fecha.day)
    tickets = filtrar_sucursal(request.user, tickets)

    tickets_gs = tickets.filter(pago__moneda=Moneda.objects.get(codigo='Gs')).values('pago__formapago').annotate(total=Sum('pago__monto'))
    tickets_dolar = tickets.filter(pago__moneda=Moneda.objects.get(codigo='USD')).values('pago__formapago').annotate(total=Sum('pago__monto'))

    # Calcular Total de Tickets y Total Efectivo
    for t in tickets_gs:
        formapago = FormaPago.objects.get(id=t['pago__formapago'])
        t['pago__formapago'] = formapago
        tickets_total_gs += t['total']
        if formapago == FormaPago.objects.get(codigo='EF'):
            efectivo_gs += int(t['total'])

    for t in tickets_dolar:
        formapago = FormaPago.objects.get(id=t['pago__formapago'])
        t['pago__formapago'] = formapago
        tickets_total_dolar += t['total']
        if formapago == FormaPago.objects.get(codigo='EF'):
            efectivo_dolar += t['total']

    # Compras
    compras = Compra.objects.filter(pago__created_at__year=fecha.year, pago__created_at__month=fecha.month, pago__created_at__day=fecha.day).distinct()
    #compras = filtrar_sucursal(request.user, compras)

    compras_gs = Pago.objects.filter(compra__in=compras, moneda=Moneda.objects.get(codigo='Gs')).values('formapago').annotate(total=Sum('monto'))
    compras_dolar = Pago.objects.filter(compra__in=compras, moneda=Moneda.objects.get(codigo='USD')).values('formapago').annotate(total=Sum('monto'))

    # Calcular Total de Compras
    for c in compras_gs:
        formapago = FormaPago.objects.get(id=c['formapago'])
        c['formapago'] = formapago
        compras_total_gs += c['total']
        if formapago == FormaPago.objects.get(codigo='EF'):
            efectivo_gs += int(c['total'])

    for c in compras_dolar:
        formapago = FormaPago.objects.get(id=c['formapago'])
        c['formapago'] = formapago
        compras_total_dolar += c['total']
        if formapago == FormaPago.objects.get(codigo='EF'):
            efectivo_dolar += c['total']

    # Ingresos - Otros
    ingresos_otros = Movimiento.objects.filter(motivo__tipo='INGRESO', created_at__year=fecha.year, created_at__month=fecha.month, created_at__day=fecha.day)
    ingresos_otros = filtrar_sucursal(request.user, ingresos_otros)
    ingresos_otros_gs = ingresos_otros.filter(moneda=Moneda.objects.get(codigo='Gs')).values('formapago', 'motivo').annotate(total=Sum('monto')).order_by('formapago')
    ingresos_otros_dolar = ingresos_otros.filter(moneda=Moneda.objects.get(codigo='USD')).values('formapago', 'motivo').annotate(total=Sum('monto')).order_by('formapago')

    # Calcular suma de Ingresos Otros y Total Efectivo
    for i in ingresos_otros_gs:
        formapago = FormaPago.objects.get(id=i['formapago'])
        i['formapago'] = formapago
        i['motivo'] = MotivoMovimiento.objects.get(id=i['motivo'])
        ingresos_otros_total_gs += i['total']
        if formapago == FormaPago.objects.get(codigo='EF'):
            efectivo_gs += int(i['total'])
    for i in ingresos_otros_dolar:
        formapago = FormaPago.objects.get(id=i['formapago'])
        i['formapago'] = formapago
        i['motivo'] = MotivoMovimiento.objects.get(id=i['motivo'])
        ingresos_otros_total_dolar += i['total']
        if formapago == FormaPago.objects.get(codigo='EF'):
            efectivo_dolar += i['total']

    # Egresos
    egresos = Movimiento.objects.filter(motivo__tipo='EGRESO', created_at__year=fecha.year, created_at__month=fecha.month, created_at__day=fecha.day)
    #print egresos, fecha
    egresos_gs = egresos.filter(moneda=Moneda.objects.get(codigo='Gs')).values('formapago').annotate(total=Sum('monto'))
    egresos_dolar = egresos.filter(moneda=Moneda.objects.get(codigo='USD')).values('formapago').annotate(total=Sum('monto'))

    # Calcular suma de Egresos
    for e in egresos_gs:
        e['formapago'] = FormaPago.objects.get(id=e['formapago'])
        egreso_total_gs += int(e['total'])
    for e in egresos_dolar:
        e['formapago'] = FormaPago.objects.get(id=e['formapago'])
        egreso_total_dolar += e['total']

    # Calcular Ingreso Total
    ingreso_total_gs = tickets_total_gs + caja_solicitada.monto_gs
    ingreso_total_dolar = tickets_total_dolar + caja_solicitada.monto_dolar

    # Calcular SALDO CAJA EFECTIVO TOTAL
    saldo_gs = efectivo_gs - egreso_total_gs + caja_solicitada.sobrante_gs - caja_solicitada.faltante_gs
    saldo_dolar = efectivo_dolar - egreso_total_dolar + caja_solicitada.sobrante_dolar - caja_solicitada.faltante_dolar

    ctx = {'caja_solicitada': caja_solicitada,
           'tickets_gs': tickets_gs, 'tickets_dolar': tickets_dolar,
           'tickets_total_gs': tickets_total_gs, 'tickets_total_dolar': tickets_total_dolar,
           'ingresos_otros_gs': ingresos_otros_gs, 'ingresos_otros_dolar': ingresos_otros_dolar,
           'ingresos_otros_total_gs': ingresos_otros_total_gs, 'ingresos_otros_total_dolar': ingresos_otros_total_dolar,
           'egresos_gs': egresos_gs, 'egresos_dolar': egresos_dolar,
           'egreso_total_gs': egreso_total_gs, 'egreso_total_dolar': egreso_total_dolar,
           'efectivo_gs': efectivo_gs, 'efectivo_dolar': efectivo_dolar,
           'ingreso_total_gs': ingreso_total_gs, 'ingreso_total_dolar': ingreso_total_dolar,
           'saldo_gs': saldo_gs, 'saldo_dolar': saldo_dolar}
    return render_to_response('backend/caja_detalle.html', ctx, context_instance=RequestContext(request))


@login_required()
@user_passes_test(verificar_login, login_url='/')
def enviar_mail_view(request):
    if request.method == 'POST':
        form = EnviarMailForm(request.POST)
        if form.is_valid():
            destino = form.cleaned_data.get('destino')

            if destino.id != 2:  # Destino NO ES Asuncion
                users = User.objects.filter(paquete__ubicacion=destino, paquete__entregado=False, paquete__mail_origen=False).distinct('email')
                for u in users:
                    lista = []
                    paquetes_nuevos = u.paquete_set.filter(user=u, ubicacion=destino, entregado=False, mail_origen=False)
                    paquetes_pendientes = u.paquete_set.filter(user=u, ubicacion=destino, entregado=False, mail_origen=True)
                    lista.append(paquetes_nuevos)
                    #lista.append(paquetes_pendientes)

                    for p in paquetes_nuevos:
                        p.mail_origen = True
                        p.save()
                    envio_mail(clientes=[u],
                               archivo='paquetes_'+str(destino.id),
                               datos=lista)
                               #request=request)
            else:  # Destino es Asuncion
                users = User.objects.filter(paquete__ubicacion=destino, paquete__entregado=False, paquete__mail_destino=False).distinct('email')
                for u in users:
                    lista = []
                    paquetes_nuevos = u.paquete_set.filter(user=u, ubicacion=destino, entregado=False, mail_destino=False)
                    paquetes_pendientes = u.paquete_set.filter(user=u, ubicacion=destino, entregado=False, mail_destino=True)
                    lista.append(paquetes_nuevos)
                    #lista.append(paquetes_pendientes)
                    for p in paquetes_nuevos:
                        p.mail_destino = True
                        p.save()
                    envio_mail(clientes=[u],
                               archivo='paquetes_'+str(destino.id),
                               datos=lista)
            messages.success(request, 'Notificaciones por Mail enviadas correctamente')
            return HttpResponseRedirect(reverse('vista_backend'))
    else:
        form = EnviarMailForm()
        ctx = {'form': form}
        return render_to_response('backend/enviar_mail.html', ctx, context_instance=RequestContext(request))

@login_required()
@user_passes_test(verificar_login, login_url='/')
def compra_agregar_view(request):
    if request.method == 'POST':
        form = CompraAgregarForm(request.POST)
        if form.is_valid():
            # Obtener los datos del POST
            enlace_list = request.POST.getlist('enlace')
            descripcion_list = request.POST.getlist('descripcion')
            comentario_list = request.POST.getlist('comentario')
            codigo_cliente = form.cleaned_data.get('codigo_cliente')
            user = get_user('PT' + str(codigo_cliente))
            # Crear el objeto Compra
            compra = Compra(user=user, fecha_solicitud=date.today())
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

            messages.success(request, 'Orden de Compra agregada correctamente.')
            return HttpResponseRedirect(reverse('vista_backend'))
        else:
            form = CompraAgregarForm(request.POST)
            ctx = {'form': form}
            return render_to_response('backend/compra_agregar.html', ctx, context_instance=RequestContext(request))
    else:
        form = CompraAgregarForm()
    ctx = {'form': form}
    return render_to_response('backend/compra_agregar.html', ctx, context_instance=RequestContext(request))



@login_required()
@user_passes_test(verificar_login, login_url='/')
def compra_cotizar_view(request, id):
    c = get_object_or_404(Compra, pk=id)
    CompraDetalleFormSet = modelformset_factory(CompraDetalle, form=CompraCotizarPedidoForm, max_num=c.detalle.count())

    if request.method == 'POST':
        formset = CompraDetalleFormSet(request.POST)
        if formset.is_valid():
            porcentaje_comision = Configuracion.objects.get(pk=1).comision
            cotizacion = Moneda.objects.get(codigo='USD').cotizacion
            compra_detalles = formset.save(commit=False)
            for cd in compra_detalles:
                valor_dolar = Decimal(cd.valor_producto) + Decimal(cd.valor_impuesto) + Decimal(cd.valor_envio_interno)
                valor_gs = costo_gs(valor_dolar * cotizacion)
                cd.valor_dolar = Decimal(valor_dolar)
                cd.valor_gs = valor_gs
                cd.estado = 'CZ'
                cd.save()

            valor_compra_dolar = valor_compra_gs = 0
            for d in CompraDetalle.objects.filter(compra__id=id):
                valor_compra_dolar += d.valor_dolar
                valor_compra_gs += d.valor_gs

            if valor_compra_dolar < 50:
                comision = 5
            else:
                comision = ceil(porcentaje_comision * valor_compra_dolar)/100  # Para redondear hacia arriba 2 decimales
            c.comision_dolar = comision
            c.comision_gs = costo_gs(comision * cotizacion)
            c.valor_compra_dolar = Decimal(valor_compra_dolar)
            c.valor_compra_gs = valor_compra_gs
            c.save()

            if 'enviar_mail' in request.POST and request.POST['enviar_mail']:  # Enviar por mail la cotizacion al Cliente
                envio_mail_cotizacion(c.user, c)

            messages.success(request, 'Órden de Compra cotizada correctamente.')
            return HttpResponseRedirect(reverse('vista_lista_compras'))
        else:
            formset = CompraDetalleFormSet(request.POST)
            ctx = {'formset': formset, 'compra': c}
            return render_to_response('backend/compra_abm.html', ctx, context_instance=RequestContext(request))
    else:
        formset = CompraDetalleFormSet(queryset=CompraDetalle.objects.filter(compra__id=id))
        ctx = {'formset': formset, 'compra': c}
        return render_to_response('backend/compra_abm.html', ctx, context_instance=RequestContext(request))


@login_required()
@user_passes_test(verificar_login, login_url='/')
def compra_pagar_pedido_view(request, id):
    if request.method == 'POST':
        form = CompraPagarForm(request.POST)
        if form.is_valid():
            montopago_list = request.POST.getlist('montopago[]')
            formapago_list = request.POST.getlist('formapago')
            moneda_lista = request.POST.getlist('moneda')

            c = Compra.objects.get(pk=id)

            # Guardar todos los pagos y asociar al Ticket
            for i in range(len(montopago_list)):
                pago = Pago(monto=montopago_list[i], formapago_id=formapago_list[i], moneda_id=moneda_lista[i])
                pago.save()
                c.pago.add(pago)
            c.save()
            messages.success(request, 'Pago de Compra guardado correctamente.')
            if c.get_saldo()['dolar'] <= 0:
                c.pagado = True
                c.save()
                return HttpResponseRedirect(reverse('vista_lista_compras'))
            ctx = {'form': CompraPagarForm(), 'compra': c}
        else:
            ctx = {'form': CompraPagarForm(request.POST), 'compra': Compra.objects.get(pk=id)}
    else:
        try:
            compra = Compra.objects.get(pk=id, pagado=False)
        except ObjectDoesNotExist:
            compra = None
        form = CompraPagarForm()
        ctx = {'form': form, 'compra': compra}
    return render_to_response('backend/compra_pagar.html', ctx, context_instance=RequestContext(request))


def barcode_view(request, paquete):
    p = None
    if paquete:
        p = get_object_or_404(Paquete, pk=paquete)

    if not p.fecha:
        p.fecha = datetime.now()

    response = HttpResponse(mimetype='application/pdf')
    response['Content-Disposition'] = 'filename="somefilename.pdf"'

    c = canvas.Canvas(response)
    c.setPageSize((155, 74))
    c.setFont("Helvetica", 8)
    c.drawString(2*mm, 22*mm, p.fecha.strftime("%d/%m/%Y %H:%M") + "  ID=" + p.id.__str__())
    c.drawString(2*mm, 18*mm, 'PT' + p.user.cliente.codigo + "-" + p.user.get_full_name())
    barcode128 = createBarcodeDrawing('Code128', value=str(p.id), barHeight=10*mm, humanReadable=False, barWidth=1.2)
    barcode128.drawOn(c, 5*mm, 4*mm)

    c.showPage()
    c.save()
    return response


def generar_listado_mail_view(request):
    if request.GET:
        if 'tipo' in request.GET:
            tipo = int(request.GET['tipo'])
            if tipo == 0:
                users = User.objects.filter(is_active=True, is_staff=False)
            elif tipo == 1:  # En Miami
                users = User.objects.filter(paquete__ubicacion=1, paquete__entregado=False).distinct('email')
            elif tipo == 2:  # En Asunción
                users = User.objects.filter(paquete__ubicacion=2, paquete__entregado=False).distinct('email')
            else:
                users = []

            users = filtrar_sucursal(request.user, users)

            # get the response object, this can be used as a stream.
            response = HttpResponse(mimetype='text/plain')
            # force download.
            response['Content-Disposition'] = 'attachment;filename="clientes-%s.txt"' % (date.today())

            # the csv writer
            writer = csv.writer(response, delimiter=';')

            row = []
            for u in users:
                row.append(str(u.email.encode('UTF-8', 'replace')))
            writer.writerow(row)

            return response
    else:
        form = ExportarListadoMail()
    ctx = {'form': form}
    return render_to_response('backend/exportar_listado_mail.html', ctx, context_instance=RequestContext(request))


@login_required()
@user_passes_test(verificar_login, login_url='/')
def proveedor_abm_view(request, id=None):
    proveedor = get_object_or_404(Proveedor, pk=id) if id else Proveedor()
    if request.method == 'POST':
        form = ProveedorForm(request.POST, instance=proveedor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Proveedor guardado correctamente.')
            if '_addanother' in request.POST:
                return HttpResponseRedirect(reverse('vista_agregar_proveedor'))
            return HttpResponseRedirect(reverse('vista_backend'))
        else:
            form = ProveedorForm(request.POST)
    else:
        form = ProveedorForm(instance=proveedor)
    proveedores = Proveedor.objects.all().order_by('id')
    ctx = {'form': form, 'proveedores': proveedores}
    return render_to_response('backend/proveedor_abm.html', ctx, context_instance=RequestContext(request))


@login_required()
@user_passes_test(verificar_login, login_url='/')
def caja_apertura_view(request):
    if request.method == 'POST':
        form = CajaAperturaForm(request.POST)
        if form.is_valid():
            ultimo_cierre = filtrar_sucursal(request.user, Caja.objects.filter(tipo='CIERRE').order_by('-created_at'))
            caja = Caja()
            caja.monto_gs = ultimo_cierre[0].monto_gs
            caja.monto_dolar = ultimo_cierre[0].monto_dolar
            caja.user = request.user
            caja.sucursal = get_sucursal(request.user)
            caja.tipo = 'APERTURA'
            caja.save()
            messages.success(request, 'Apertura de Caja procesada correctamente')
            return HttpResponseRedirect(reverse('vista_backend'))
    else:
        caja_abierta = Caja.objects.filter(tipo='APERTURA', cerrada=False).order_by('-created_at')
        caja_abierta = filtrar_sucursal(request.user, caja_abierta)
        if caja_abierta:
            url = "/backend/caja/cierre/%s" % caja_abierta[0].id
            msj = 'No se realizó el cierre de la última Caja.<br>Favor cerrar la <a href="' + url + '">Caja</a>.'
            messages.error(request, msj)
            ctx = {}
        else:
            ultimo_cierre = filtrar_sucursal(request.user, Caja.objects.filter(tipo='CIERRE').order_by('-created_at'))
            if len(ultimo_cierre):
                monto_gs = ultimo_cierre[0].monto_gs
                monto_dolar = ultimo_cierre[0].monto_dolar
                form = CajaAperturaForm(initial={'monto_gs': monto_gs, 'monto_dolar': monto_dolar})
            else:
                form = CajaAperturaForm()
            ctx = {'form': form}
        return render_to_response('backend/caja_apertura.html', ctx, context_instance=RequestContext(request))


@login_required()
@user_passes_test(verificar_login, login_url='/')
def caja_abierta_view(request):
    caja_abierta = filtrar_sucursal(request.user, Caja.objects.filter(tipo='APERTURA', cerrada=False).order_by('created_at'))
    ctx = {'caja_abierta': caja_abierta}
    return render_to_response('backend/caja_abierta.html', ctx, context_instance=RequestContext(request))


@login_required()
@user_passes_test(verificar_login, login_url='/')
def caja_cierre_view(request, id):
    if request.method == 'POST':
        form = CajaCierreForm(request.POST, request.FILES)
        if form.is_valid():
            saldo_gs = form.cleaned_data.get('saldo_gs')
            sobrante_gs = form.cleaned_data.get('sobrante_gs')
            faltante_gs = form.cleaned_data.get('faltante_gs')
            saldo_dolar = form.cleaned_data.get('saldo_dolar')
            sobrante_dolar = form.cleaned_data.get('sobrante_dolar')
            faltante_dolar = form.cleaned_data.get('faltante_dolar')
            comentario = form.cleaned_data.get('comentario')
            caja_solicitada = get_object_or_404(Caja, pk=id)
            caja_solicitada.cerrada = True
            caja_solicitada.save()
            caja = Caja(arqueo=request.FILES['arqueo'])
            caja.user = request.user
            caja.sucursal = get_sucursal(request.user)
            caja.tipo = "CIERRE"
            caja.monto_gs = saldo_gs + sobrante_gs - faltante_gs
            caja.sobrante_gs = sobrante_gs
            caja.faltante_gs = faltante_gs
            caja.monto_dolar = saldo_dolar + sobrante_dolar - faltante_dolar
            caja.sobrante_dolar = sobrante_dolar
            caja.faltante_dolar = faltante_dolar
            caja.cerrada = True
            caja.comentario = comentario
            caja.caja_asociada = caja_solicitada
            caja.created_at = datetime.today()
            caja.save()
            envio_mail_gerentes(get_sucursal(request.user), caja_solicitada, caja)
            messages.success(request, 'Caja cerrada correctamente.')
            return HttpResponseRedirect(reverse('vista_backend'))

    tickets_total_gs = tickets_total_dolar = ingresos_otros_total_gs = ingresos_otros_total_dolar = 0
    compras_total_gs = compras_total_dolar = egreso_total_gs = egreso_total_dolar = 0
    caja_solicitada = get_object_or_404(Caja, pk=id)
    caja_abierta = filtrar_sucursal(request.user, Caja.objects.filter(tipo='APERTURA', cerrada=False).order_by('created_at'))
    if caja_solicitada.id != caja_abierta[0].id:  # Para controlar los cambios en la URL
        messages.error(request, 'Error: No coinciden las Cajas')

    fecha = caja_solicitada.created_at
    efectivo_gs = caja_solicitada.monto_gs
    efectivo_dolar = caja_solicitada.monto_dolar

    # Tickets
    tickets = Ticket.objects.filter(fecha__year=fecha.year, fecha__month=fecha.month, fecha__day=fecha.day)
    tickets = filtrar_sucursal(request.user, tickets)

    tickets_gs = tickets.filter(pago__moneda=Moneda.objects.get(codigo='Gs')).values('pago__formapago').annotate(total=Sum('pago__monto'))
    tickets_dolar = tickets.filter(pago__moneda=Moneda.objects.get(codigo='USD')).values('pago__formapago').annotate(total=Sum('pago__monto'))

    # Calcular Total de Tickets y Total Efectivo
    for t in tickets_gs:
        formapago = FormaPago.objects.get(id=t['pago__formapago'])
        t['pago__formapago'] = formapago
        tickets_total_gs += t['total']
        if formapago == FormaPago.objects.get(codigo='EF'):
            efectivo_gs += int(t['total'])

    for t in tickets_dolar:
        formapago = FormaPago.objects.get(id=t['pago__formapago'])
        t['pago__formapago'] = formapago
        tickets_total_dolar += t['total']
        if formapago == FormaPago.objects.get(codigo='EF'):
            efectivo_dolar += t['total']

    # Compras
    compras = Compra.objects.filter(pago__created_at__year=fecha.year, pago__created_at__month=fecha.month, pago__created_at__day=fecha.day).distinct()
    #compras = filtrar_sucursal(request.user, compras)

    compras_gs = Pago.objects.filter(compra__in=compras, moneda=Moneda.objects.get(codigo='Gs')).values('formapago').annotate(total=Sum('monto'))
    compras_dolar = Pago.objects.filter(compra__in=compras, moneda=Moneda.objects.get(codigo='USD')).values('formapago').annotate(total=Sum('monto'))

    # Calcular Total de Compras
    for c in compras_gs:
        formapago = FormaPago.objects.get(id=c['formapago'])
        c['formapago'] = formapago
        compras_total_gs += c['total']
        if formapago == FormaPago.objects.get(codigo='EF'):
            efectivo_gs += int(c['total'])

    for c in compras_dolar:
        formapago = FormaPago.objects.get(id=c['formapago'])
        c['formapago'] = formapago
        compras_total_dolar += c['total']
        if formapago == FormaPago.objects.get(codigo='EF'):
            efectivo_dolar += c['total']

    # Ingresos - Otros
    ingresos_otros = Movimiento.objects.filter(motivo__tipo='INGRESO', created_at__year=fecha.year, created_at__month=fecha.month, created_at__day=fecha.day)
    ingresos_otros = filtrar_sucursal(request.user, ingresos_otros)
    ingresos_otros_gs = ingresos_otros.filter(moneda=Moneda.objects.get(codigo='Gs')).values('formapago', 'motivo').annotate(total=Sum('monto')).order_by('formapago')
    ingresos_otros_dolar = ingresos_otros.filter(moneda=Moneda.objects.get(codigo='USD')).values('formapago', 'motivo').annotate(total=Sum('monto')).order_by('formapago')

    # Calcular suma de Ingresos Otros
    for i in ingresos_otros_gs:
        formapago = FormaPago.objects.get(id=i['formapago'])
        i['formapago'] = formapago
        i['motivo'] = MotivoMovimiento.objects.get(id=i['motivo'])
        ingresos_otros_total_gs += i['total']
        if formapago == FormaPago.objects.get(codigo='EF'):
            efectivo_gs += int(i['total'])
    for i in ingresos_otros_dolar:
        formapago = FormaPago.objects.get(id=i['formapago'])
        i['formapago'] = formapago
        i['motivo'] = MotivoMovimiento.objects.get(id=i['motivo'])
        ingresos_otros_total_dolar += i['total']
        if formapago == FormaPago.objects.get(codigo='EF'):
            efectivo_dolar += i['total']

    # Egresos
    egresos = Movimiento.objects.filter(motivo__tipo='EGRESO', created_at__year=fecha.year, created_at__month=fecha.month, created_at__day=fecha.day)
    egresos_gs = egresos.filter(moneda=Moneda.objects.get(codigo='Gs')).values('formapago').annotate(total=Sum('monto'))
    egresos_dolar = egresos.filter(moneda=Moneda.objects.get(codigo='USD')).values('formapago').annotate(total=Sum('monto'))

    # Calcular suma de Egresos
    for e in egresos_gs:
        e['formapago'] = FormaPago.objects.get(id=e['formapago'])
        egreso_total_gs += int(e['total'])
    for e in egresos_dolar:
        e['formapago'] = FormaPago.objects.get(id=e['formapago'])
        egreso_total_dolar += e['total']

    # Calcular Ingreso Total
    ingreso_total_gs = tickets_total_gs + caja_solicitada.monto_gs
    ingreso_total_dolar = tickets_total_dolar + caja_solicitada.monto_dolar

    # Calcular SALDO CAJA EFECTIVO TOTAL
    saldo_gs = efectivo_gs - egreso_total_gs
    saldo_dolar = efectivo_dolar - egreso_total_dolar

    form = CajaCierreForm(initial={'saldo_gs': saldo_gs, 'saldo_dolar': saldo_dolar,
                                   'sobrante_gs': 0, 'sobrante_dolar': 0,
                                   'faltante_gs': 0, 'faltante_dolar': 0})

    ctx = {'form': form, 'caja_solicitada': caja_solicitada,
           'tickets_gs': tickets_gs, 'tickets_dolar': tickets_dolar,
           'tickets_total_gs': tickets_total_gs, 'tickets_total_dolar': tickets_total_dolar,
           'compras_gs': compras_gs, 'compras_dolar': compras_dolar,
           'compras_total_gs': compras_total_gs, 'compras_total_dolar': compras_total_dolar,
           'ingresos_otros_gs': ingresos_otros_gs, 'ingresos_otros_dolar': ingresos_otros_dolar,
           'ingresos_otros_total_gs': ingresos_otros_total_gs, 'ingresos_otros_total_dolar': ingresos_otros_total_dolar,
           'egresos_gs': egresos_gs, 'egresos_dolar': egresos_dolar,
           'egreso_total_gs': egreso_total_gs, 'egreso_total_dolar': egreso_total_dolar,
           'efectivo_gs': efectivo_gs, 'efectivo_dolar': efectivo_dolar,
           'ingreso_total_gs': ingreso_total_gs, 'ingreso_total_dolar': ingreso_total_dolar,
           'saldo_gs': saldo_gs, 'saldo_dolar': saldo_dolar}
    return render_to_response('backend/caja_cierre.html', ctx, context_instance=RequestContext(request))


@login_required()
@user_passes_test(verificar_login, login_url='/')
def caja_egreso_abm_view(request):
    if not filtrar_sucursal(request.user, Caja.objects.filter(tipo='APERTURA', cerrada=False)):
        messages.error(request, 'No hay caja abierta. Realizar la Apertura de Caja primero.')
        return HttpResponseRedirect(reverse('vista_backend'))

    if request.method == 'POST':
        form = MovimientoForm(request.POST)
        if form.is_valid():
            formapago = form.cleaned_data.get('formapago')
            moneda = form.cleaned_data.get('moneda')
            motivo_egreso = form.cleaned_data.get('motivo')
            descripcion = form.cleaned_data.get('descripcion')
            monto = form.cleaned_data.get('monto')
            egreso = Movimiento()
            egreso.user = request.user
            egreso.sucursal = get_sucursal(request.user)
            egreso.formapago = formapago
            egreso.moneda = moneda
            egreso.motivo = motivo_egreso
            egreso.descripcion = descripcion
            egreso.monto = monto
            egreso.save()
            messages.success(request, 'Egreso guardado correctamente.')
            if '_addanother' in request.POST:
                return HttpResponseRedirect(reverse('vista_agregar_egreso'))
            return HttpResponseRedirect(reverse('vista_backend'))
    else:
        form = MovimientoForm(initial={'formapago': FormaPago.objects.get(codigo='EF'), 'moneda': Moneda.objects.get(codigo='Gs')})

    motivos = MotivoMovimiento.objects.filter(tipo='EGRESO').order_by('id')
    ctx = {'form': form, 'motivos': motivos}
    return render_to_response('backend/caja_egreso_abm.html', ctx, context_instance=RequestContext(request))


@login_required()
@user_passes_test(verificar_login, login_url='/')
def manifiesto_agregar_view(request):
    if request.method == 'POST':
        form = ManifiestoAgregarForm(request.POST)
        if form.is_valid():
            manifiesto = form.save()  # Guardar el Formulario e Instanciar
            paquetes_list = request.POST.getlist('paquetes[]')
            paquetes = Paquete.objects.filter(id__in=paquetes_list)
            bolsa_peso = paquetes.aggregate(total=Sum('peso'))

            manifiesto.paquete = paquetes
            manifiesto.bolsa_peso = bolsa_peso['total']
            manifiesto.save()
            messages.success(request, 'Manifiesto agregado correctamente.')
            return HttpResponseRedirect(reverse('vista_lista_manifiesto'))
        else:
            form = ManifiestoAgregarForm(request.POST)
    else:
        form = ManifiestoAgregarForm(initial={'fecha_arribo': date.today()})
    ctx = {'form': form}
    return render_to_response('backend/manifiesto_agregar.html', ctx, context_instance=RequestContext(request))


def wsmotivo_egreso_view(request):
    try:
        nombre = request.POST.get('nombre_motivo')
        motivo = MotivoMovimiento()
        motivo.nombre = nombre
        motivo.tipo = 'EGRESO'
        motivo.save()
    except:
        return HttpResponse('{"response": "Hubo un error"}', mimetype='application/json')
    return HttpResponse(parsear(MotivoMovimiento.objects.filter(id=motivo.id)), mimetype='application/json')


def wsdetalle_compra_guardar_view(request):
    try:
        id_detalle = int(request.POST.get('id_detalle'))
        detalle_compra = CompraDetalle.objects.get(pk=id_detalle)
        detalle_compra.fecha_compra = date.today()
        detalle_compra.estado = 'CZ'
        detalle_compra.save()
    except:
        msj = 'ERROR Inesperado. %s' % sys.exc_info()
        return HttpResponse('{"response": "Error" }', mimetype='application/json')
    return HttpResponse('{"response": "OK"}', mimetype='application/json')


def wscompra_divisa_view(request):
    try:
        monto_gs = request.POST.get('monto_compra_divisa_gs')
        monto_dolar = request.POST.get('monto_compra_divisa_dolar')
        sucursal = get_sucursal(request.user)
        formapago = FormaPago.objects.get(codigo='EF')

        # Realizar un Ingreso del Monto Dolar a la Caja Dolar
        ingreso = Movimiento()
        ingreso.user = request.user
        ingreso.sucursal = sucursal
        ingreso.formapago = formapago
        ingreso.moneda = Moneda.objects.get(codigo='USD')
        ingreso.motivo = MotivoMovimiento.objects.get(codigo='CUSD')
        ingreso.monto = monto_dolar
        ingreso.save()

        # Realizar un Egreso del Monto Gs a la Caja Gs
        egreso = Movimiento()
        egreso.user = request.user
        egreso.sucursal = sucursal
        egreso.formapago = formapago
        egreso.moneda = Moneda.objects.get(codigo='Gs')
        egreso.motivo = MotivoMovimiento.objects.get(codigo='VGS')
        egreso.monto = monto_gs
        egreso.save()
    except:
        msj = 'ERROR Inesperado. %s' % sys.exc_info()
        return HttpResponse('{"response": "Error"}', mimetype='application/json')
    return HttpResponse('{"response": "OK"}', mimetype='application/json')


def wsticket_cambio_estado_view(request):
    try:
        estado = request.POST.get('estado')
        if FormaPago.objects.get(id=estado) == FormaPago.objects.get(codigo='PEND'):
            tickets = filtrar_sucursal(request.user, Ticket.objects.filter(pago__formapago_id=estado))
        else:
            tickets = filtrar_sucursal(request.user, Ticket.objects.filter(pago__formapago_id=estado))[:10]
    except:
        return HttpResponse('{"response": "Hubo un error"}', mimetype='application/json')
    return HttpResponse(parsear(tickets), mimetype='application/json')


def wsmanifiesto_paquetes_view(request):
    try:
        origen = request.POST.get('origen')
        paquetes = Paquete.objects.filter(ubicacion_id=origen, entregado=False).order_by('id')
    except:
        return HttpResponse('{"response": "Hubo un error"}', mimetype='application/json')
    return HttpResponse(parsear(paquetes), mimetype='application/json')


def wsfactura_cliente_view(request):
    try:
        cliente_id = request.POST.get('cliente')
        nombre = request.POST.get('nombre')
        ruc = request.POST.get('ruc')
        cliente = Cliente.objects.get(id=cliente_id)
        if ClienteFactura.objects.filter(cliente=cliente, ruc=ruc):
            raise ValueError('RUC ya existente')
        cliente_factura = ClienteFactura(cliente=cliente, nombre=nombre.upper(), ruc=ruc)
        cliente_factura.save()
    except ValueError:
        return HttpResponse('{"response": "rucduplicado"}', mimetype='application/json')
    except:
        return HttpResponse('{"response": "error"}', mimetype='application/json')
    return HttpResponse(parsear(ClienteFactura.objects.filter(id=cliente_factura.id)), mimetype='application/json')



# from rest_framework import viewsets
# from pytrade.apps.home.serializers import PaqueteSerializer
# from django.http import Http404
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from rest_framework import generics
# from rest_framework import permissions
#
#
# class PaqueteList(generics.ListCreateAPIView):
#     queryset = Paquete.objects.exclude(codigo__isnull=True).order_by('-codigo')[:5]
#     serializer_class = PaqueteSerializer
#     permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
#
#     def perform_authentication(self, request):
#         print request.user
#         pass
#
#
# class PaqueteDetail(generics.RetrieveUpdateDestroyAPIView):
#     queryset = Paquete.objects.all()
#     serializer_class = PaqueteSerializer
#
#
# class PaqueteViewSet(viewsets.ModelViewSet):
#     queryset = Paquete.objects.all()[:5]
#     serializer_class = PaqueteSerializer