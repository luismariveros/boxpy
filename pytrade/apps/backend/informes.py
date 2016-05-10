from pytrade.apps.backend.views import *
from pytrade.apps.backend.funciones import *
from pytrade.apps.backend.forms import CabeceraInformeForm


def i_cargas_cliente_view(request):
    clientes = Cliente.objects.annotate(peso=Sum('user__ticket__peso_sistema'),
                                        cantidad_paquetes=Sum('user__ticket__cantidad_paquete'),
                                        cantidad_tickets=Count('user__ticket'),
                                        dolar=Sum('user__ticket__monto_dolar'),
                                        gs=Sum('user__ticket__monto_gs'),
                                        fecha=Max('user__ticket__fecha')).order_by('-peso')
    sin_paquete = clientes.filter(cantidad_paquetes=None).count()
    resumen = clientes.aggregate(total_peso=Sum('peso'),
                                 total_paquetes=Sum('cantidad_paquetes'),
                                 total_tickets=Sum('cantidad_tickets'),
                                 total_dolar=Sum('dolar'),
                                 total_gs=Sum('gs'))

    ctx = {'clientes': clientes, 'resumen': resumen, 'sin_paquete': sin_paquete}
    return render_to_response('informes/informe_carga_cliente.html', ctx, context_instance=RequestContext(request))


def i_ingresos_egresos_view(request):
    efectivo_gs = efectivo_dolar = tickets_total_gs = tickets_total_dolar = ingresos_otros_total_gs = ingresos_otros_total_dolar = egreso_total_gs = egreso_total_dolar = compras_total_gs = compras_total_dolar = 0

    if request.method == 'GET' and request.GET:
        f_desde = datetime.strptime(request.GET.get('fecha_desde'), "%Y-%m-%d")
        f_hasta = datetime.strptime(request.GET.get('fecha_hasta') + ' 23:59', "%Y-%m-%d %H:%M")
    else:
        f_desde = date.today()
        f_hasta = datetime(f_desde.year, f_desde.month, f_desde.day, 23, 59)
    # Tickets
    #tickets = Ticket.objects.filter(fecha__year=2015, fecha__month=9, fecha__day=30)
    tickets = Ticket.objects.filter(fecha__range=(f_desde, f_hasta))
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
    compras = Compra.objects.filter(pago__created_at__range=(f_desde, f_hasta)).distinct()
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
    ingresos_otros = Movimiento.objects.filter(motivo__tipo='INGRESO', created_at__range=(f_desde, f_hasta))
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
    egresos = Movimiento.objects.filter(motivo__tipo='EGRESO', created_at__range=(f_desde, f_hasta))
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
    ingreso_total_gs = tickets_total_gs + ingresos_otros_total_gs + compras_total_gs
    ingreso_total_dolar = tickets_total_dolar + ingresos_otros_total_dolar + compras_total_dolar

    # Calcular SALDO CAJA EFECTIVO TOTAL
    saldo_gs = ingreso_total_gs - egreso_total_gs
    saldo_dolar = ingreso_total_dolar - egreso_total_dolar
    print egresos.__dict__

    ctx = {'tickets_gs': tickets_gs, 'tickets_dolar': tickets_dolar,
           'tickets': tickets,
           'tickets_total_gs': tickets_total_gs, 'tickets_total_dolar': tickets_total_dolar,
           'compras_gs': compras_gs, 'compras_dolar': compras_dolar,
           'compras': compras,
           'compras_total_gs': compras_total_gs, 'compras_total_dolar': compras_total_dolar,
           'ingresos_otros_gs': ingresos_otros_gs, 'ingresos_otros_dolar': ingresos_otros_dolar,
           'ingresos_otros': ingresos_otros,
           'ingresos_otros_total_gs': ingresos_otros_total_gs, 'ingresos_otros_total_dolar': ingresos_otros_total_dolar,
           'egresos_gs': egresos_gs, 'egresos_dolar': egresos_dolar,
           'egresos': egresos,
           'egreso_total_gs': egreso_total_gs, 'egreso_total_dolar': egreso_total_dolar,
           'efectivo_gs': efectivo_gs, 'efectivo_dolar': efectivo_dolar,
           'ingreso_total_gs': ingreso_total_gs, 'ingreso_total_dolar': ingreso_total_dolar,
           'saldo_gs': saldo_gs, 'saldo_dolar': saldo_dolar,
           'form': CabeceraInformeForm(), 'f_desde': f_desde, 'f_hasta': f_hasta,
           }
    return render_to_response('informes/informe_ingreso_egreso.html', ctx, context_instance=RequestContext(request))