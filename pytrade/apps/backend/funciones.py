from pytrade.apps.backend.views import *


# Funcion utilizar en el decorator user_passes_test
def verificar_login(user):
    try:
        # Validar que USER no sea cliente
        Cliente.objects.get(user=user)
        return False
    except ObjectDoesNotExist:
        return True


# Funcion que devuelve el USER de un codigo (PT12345) de cliente
def get_user(codigo):
    codigo = codigo[-5:]
    return Cliente.objects.get(codigo=codigo).user


# Funcion que devuelve la SUCURSAL de un USER (Cliente o Usuario de Sistema)
# Defecto: Casa Central (ID=1)
def get_sucursal(user):
    try:
        return Cliente.objects.get(user=user).sucursal
    except ObjectDoesNotExist:
        try:
            return Usuario.objects.get(user=user).sucursal
        except ObjectDoesNotExist:
            return Sucursal.objects.get(id=1)


# Funcion para generar el archivo PDF y devolverlo mediante HttpResponse
def generar_pdf(html):
    result = StringIO.StringIO()
    pdf = pisa.pisaDocument(StringIO.StringIO(html.encode("UTF-8")), result)
    #print pdf
    if not pdf.err:
        return HttpResponse(result.getvalue(), mimetype='application/pdf')
    return HttpResponse('Error al generar el PDF: %s' % cgi.escape(html))


# Funcion para generar un Codigo de Barra dentro de un PDF y devolverlo mediante HttpResponse
def generar_barcode(paquete):
    p = None
    if paquete:
        p = get_object_or_404(Paquete, pk=paquete)
    if not p.fecha:
        p.fecha = datetime.now()
    response = HttpResponse(mimetype='application/pdf')
    response['Content-Disposition'] = 'filename="somefilename.pdf"'

    c = canvas.Canvas(response)
    c.setPageSize((520, 260))
    c.setFont("Helvetica", 6)
    c.drawString(1*mm, 7*mm, p.fecha.strftime("%d/%m/%Y %H:%M") + "  ID=" + p.id.__str__())
    c.drawString(1*mm, 5*mm, p.user.get_full_name() + ' - PT' + p.user.cliente.codigo)
    barcode128 = createBarcodeDrawing('Code128', value='12345678', barHeight=3*mm, humanReadable=False)
    barcode128.drawOn(c, -15, 1*mm)

    c.showPage()
    c.save()
    return response


# Funcion para guardar un paquete
def paquete_save(paquete, user, peso, codigo_paquete=None, fecha=None, descripcion=None, tracking=None,
                 ubicacion_id=None, proveedor=None, fecha_destino=None, valor_dolar=None):
    cliente = Cliente.objects.get(user=user)
    costo_kilo = cliente.categoria.costo
    costo_envio_dolar = ceil(Decimal(peso) * costo_kilo * 100) / 100  # Para redondear hacia arriba 2 decimales
    dolar = Moneda.objects.get(codigo='USD').cotizacion
    paquete.user = user
    paquete.peso = peso
    paquete.dolar = dolar
    paquete.costo_envio_dolar = costo_envio_dolar
    paquete.costo_envio_gs = costo_gs(costo_envio_dolar * dolar)
    paquete.sucursal = cliente.sucursal
    if codigo_paquete:
        paquete.codigo = codigo_paquete
    if fecha:
        paquete.fecha = fecha
    if descripcion:
        paquete.descripcion = descripcion
    if tracking:
        paquete.tracking = tracking
    if ubicacion_id:
        paquete.ubicacion_id = ubicacion_id
    if proveedor:
        paquete.proveedor = proveedor
    if fecha_destino:
        paquete.fecha_destino = fecha_destino
    if valor_dolar:
        paquete.valor_dolar = valor_dolar

    paquete.save()


# Funcion para calcular el costo de un paquete
# Parametros: peso, costo kilo, promocion, seguro, delivery, envolver,
def calcular_costo(peso, user, promocion=None, seguro=False, delivery=False, envolver=False):
    costo_dolar = peso * Cliente.objects.get(user=user).categoria.costo
    costo_gs = costo_dolar * Moneda.objects.get(codigo='USD').cotizacion


# Funcion para calcular el costo de un paquete en Gs.
def calcular_costo_gs(peso, costo_kilo, dolar):
    monto_minimo = Configuracion.objects.get(id=1).monto_minimo
    costo_envio_gs = costo_gs(peso * costo_kilo * dolar)
    if costo_envio_gs < monto_minimo:
        return monto_minimo
    return costo_envio_gs


# Funcion para calcular el costo de un paquete en USD.
def calcular_costo_dolar(peso, costo_kilo, dolar, costo_envio_gs):
    monto_minimo = Configuracion.objects.get(id=1).monto_minimo
    if costo_envio_gs <= monto_minimo:
        return round(monto_minimo / Decimal(dolar), 2)
    return ceil(Decimal(peso) * costo_kilo * 100) / 100  # Para redondear hacia arriba 2 decimales


# Funcion que devuelve el redondeo del monto en multiples de 500 gs
def costo_gs(monto, redondeo=500):
    if monto%redondeo > 0:
        return (int(monto/redondeo)+1)*redondeo
    else:
        return (int(monto/redondeo))*redondeo


# Funcion para filtrar los datos segun la sucursal del usuario
def filtrar_sucursal(user, datos):
    print user
    if bool(user.groups.filter(name='Sucursales')):
        for d in datos:
            print d.sucursal, type(d)
        usuario = Usuario.objects.get(user=user)
        print usuario, usuario.sucursal
        return datos.filter(sucursal=usuario.sucursal)
    else:
        return datos


# Funcion que devuelve en formato JSON
def parsear(datos):
    return serializers.serialize('json', datos, use_natural_keys=True)

