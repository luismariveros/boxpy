#encoding=utf8
from django.db import models
from django.contrib.auth.models import User
from datetime import date
from django.db.models import Sum
from decimal import Decimal
#import django_filters


class Configuracion(models.Model):
    dolar = models.IntegerField()
    ultimo_valor = models.IntegerField()
    monto_minimo = models.IntegerField()
    comision = models.IntegerField(default=10)

    def __unicode__(self):
        return "Dolar=%s|Ult. Valor=%s|Monto=%s" % (self.dolar, self.ultimo_valor, self.monto_minimo)

    class Meta:
        db_table = 'pytrade_config'
        verbose_name_plural = "configuraciones"


class Moneda(models.Model):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=10)
    cotizacion = models.IntegerField()

    def __unicode__(self):
        return self.codigo

    def natural_key(self):
        return self.codigo

    class Meta:
        db_table = 'pytrade_moneda'


# class Empresa(models.Model):
#     nombre = models.CharField(max_length=100)
#     codigo = models.CharField(max_length=100)
#     mail = models.EmailField(null=True, blank=True)
#
#     def __unicode__(self):
#         return "%s - %s" % (self.nombre, self.codigo)
#
#     class Meta:
#         db_table = 'pytrade_empresas'


class Proveedor(models.Model):
    nombre = models.CharField(max_length=100)
    url = models.URLField()

    def __unicode__(self):
        return self.nombre

    class Meta:
        db_table = 'pytrade_proveedor'
        verbose_name_plural = "proveedores"


class FormaPago(models.Model):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=15)
    comision = models.IntegerField()

    def __unicode__(self):
        return self.nombre

    class Meta:
        db_table = 'pytrade_formapago'


class Compra(models.Model):
    user = models.ForeignKey(User)
    detalle = models.ManyToManyField('CompraDetalle', blank=True, null=True)
    pago = models.ManyToManyField('Pago', blank=True, null=True)
    valor_compra_dolar = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)  # Suma Detalle Dolares
    valor_compra_gs = models.BigIntegerField(blank=True, null=True)  # Suma Detalle Guaranies
    comision_dolar = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Configuracion.comision/100
    comision_gs = models.BigIntegerField(null=True, blank=True)
    # Por Admin cuando el Cliente Paga Completamente
    pagado = models.BooleanField(default=False)
    # Fechas por Sistema
    fecha_solicitud = models.DateField()

    def get_total_gs(self):
        if self.valor_compra_gs and self.comision_gs:
            return self.valor_compra_gs + self.comision_gs

    def get_total_dolar(self):
        if self.valor_compra_dolar and self.comision_dolar:
            return Decimal(self.valor_compra_dolar) + Decimal(self.comision_dolar)

    def get_saldo(self):
        pago_dolar = self.pago.filter(moneda__codigo='USD')
        pago_gs = self.pago.filter(moneda__codigo='Gs')
        cotizacion = Moneda.objects.get(codigo='USD').cotizacion
        if pago_dolar and pago_gs:  # Hubo pagos en Dolar y en Gs
            pago = pago_dolar.aggregate(dolar=Sum('monto'))
            pago_gs = pago_gs.aggregate(gs=Sum('monto'))
            pago['gs'] = pago_gs['gs']
            saldo = {'dolar': self.valor_compra_dolar + self.comision_dolar - pago['dolar'] - (pago['gs']/cotizacion)}
            saldo['gs'] = saldo['dolar'] * cotizacion
        elif pago_dolar:  # Hubo pagos en Dolar
            pago = pago_dolar.aggregate(dolar=Sum('monto'))
            saldo = {'dolar': self.valor_compra_dolar + self.comision_dolar - pago['dolar']}
            saldo['gs'] = saldo['dolar'] * cotizacion
        elif pago_gs:  # Hubo pagos en Gs
            pago = pago_gs.aggregate(gs=Sum('monto'))
            saldo = {'gs': self.valor_compra_gs + self.comision_gs - pago['gs']}
            saldo['dolar'] = saldo['gs'] / cotizacion
        return saldo

    def __unicode__(self):
        return "ID=%s de %s" % (self.id, self.user.get_full_name())

    class Meta:
        db_table = 'pytrade_compras'


class CompraDetalle(models.Model):
    ESTADO_COMPRA = (
        ('PC', 'Para Cotizar'),
        ('CZ', 'Cotizado'),
        ('P', 'Pagado'),
        ('C', 'Comprado')
    )
    # Por el Cliente cuando SOLICITA una Compra
    enlace = models.URLField(max_length=350)
    descripcion = models.CharField(max_length=200)
    comentario = models.TextField()
    # Por Admin cuando COTIZA una Compra
    valor_producto = models.DecimalField(max_digits=10, decimal_places=2, null=True)  # Dolares
    valor_envio_interno = models.DecimalField(max_digits=10, decimal_places=2, null=True)  # Dolares
    valor_impuesto = models.DecimalField(max_digits=10, decimal_places=2, null=True)  # Dolares
    # Por Sistema cuando COTIZA una Compra
    valor_dolar = models.DecimalField(max_digits=10, decimal_places=2, blank= True, null=True)  # Dolares (Total)
    valor_gs = models.BigIntegerField(blank=True, null=True)  # Guaranies (Total)
    # Por Admin cuando COMPLETA la Post Compra
    tracking = models.CharField(max_length=200, null=True, blank=True)
    proveedor = models.ForeignKey(Proveedor, null=True, blank=True)
    # Por Sistema
    comprado = models.BooleanField(default=False)
    estado = models.CharField(max_length=50, choices=ESTADO_COMPRA)
    fecha_solicitud = models.DateField()
    fecha_compra = models.DateField(blank=True, null=True)

    def __unicode__(self):
        return "CompraDetalle=%s - USD=%s - [%s]" % (self.id, self.valor_dolar, self.fecha_solicitud)

    class Meta:
        db_table = 'pytrade_compra_detalles'
        verbose_name_plural = "compras Detalles"


class Ubicacion(models.Model):
    nombre = models.CharField(max_length=20)
    codigo = models.CharField(max_length=15, null=True, blank=True)
    #fisica = models.BooleanField()

    def __unicode__(self):
        return "%s" % self.nombre

    class Meta:
        db_table = 'pytrade_ubicacion'
        verbose_name_plural = "ubicaciones"


class Paquete(models.Model):
    def url(self, filename):
        ruta = "MultimediaData/Paquetes/%s/%s" % (self.id, str(filename))
        return ruta
    # CSV en Origen (Miami)
    user = models.ForeignKey(User)
    codigo = models.CharField(max_length=70, null=True, blank=True)
    fecha = models.DateField(null=True, blank=True)
    descripcion = models.CharField(max_length=500)
    peso = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    tracking = models.CharField(max_length=200, null=True, blank=True)
    valor_dolar = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    # Por Personal de PyTrade
    ubicacion = models.ForeignKey('Ubicacion')
    entregado = models.BooleanField(default=False)
    costo_delivery = models.BigIntegerField(default=0)
    costo_seguro = models.BigIntegerField(default=0)
    # Guardo la cotizacion del dolar cuando se carga el CVS de Miami
    dolar = models.IntegerField()
    # Por Clientes
    seguro = models.BooleanField(default=False)
    valor_asegurado = models.DecimalField(max_digits=10, decimal_places=2, null=True, default=0)
    factura = models.ImageField(upload_to=url, null=True, blank=True)
    delivery = models.BooleanField(default=False)
    sucursal = models.ForeignKey('home.Sucursal')
    # CSV en Asuncion
    fecha_destino = models.DateField(null=True, blank=True)
    # Operaciones
    # Monto del envio calculado por el Sistema al Cargar el CVS de Miami (En Gs y Dolar)
    costo_envio_gs = models.BigIntegerField(default=0)
    costo_envio_dolar = models.DecimalField(max_digits=12, decimal_places=2, null=True, default=0)
    # Sistema
    created_at = models.DateTimeField(db_column='fecha_creacion', auto_now_add=True)
    proveedor = models.ForeignKey(Proveedor, null=True, blank=True)
    mail_origen = models.BooleanField(default=False)
    mail_destino = models.BooleanField(default=False)

    def __unicode__(self):
        return "%s %s" % (self.user.username, self.descripcion)

    class Meta:
        db_table = 'pytrade_paquetes'


class Carga(models.Model):
    def path(self, filename):
        url = "reportes/%s/%s/%s/%s" % (self.origen, date.today().strftime('%Y'), date.today().strftime('%m'),  filename)
        return url
    origen = models.ForeignKey(Ubicacion)
    paquete = models.ManyToManyField(Paquete)
    archivo = models.FileField(upload_to=path)
    carga_asociada = models.ForeignKey('self', null=True, blank=True)
    cantidad_paquetes = models.IntegerField(null=True)
    kilo_carga = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    kilos = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    created_at = models.DateTimeField(auto_now=False, auto_now_add=True)

    def __unicode__(self):
        return self.archivo.__str__()

    class Meta:
        db_table = 'pytrade_carga'


class Manifiesto(models.Model):
    fecha_arribo = models.DateField()
    origen = models.ForeignKey(Ubicacion)
    paquete = models.ManyToManyField(Paquete)
    bolsa_cantidad = models.IntegerField()
    bolsa_peso = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now=False, auto_now_add=True)

    def __unicode__(self):
        return "ID=%s - Bolsas=%s" % (self.id, self.bolsa_cantidad)

    class Meta:
        db_table = 'pytrade_manifiesto'


class Pago(models.Model):
    formapago = models.ForeignKey(FormaPago)  # Forma de Pago
    moneda = models.ForeignKey(Moneda, default=Moneda.objects.get(codigo='Gs'))  # Moneda de Pago
    monto = models.DecimalField(max_digits=30, decimal_places=2)
    created_at = models.DateTimeField(db_column='fecha', auto_now_add=True)

    def __unicode__(self):
        return "%s -> %s %s [%s]" % (self.id, self.monto, self.moneda.codigo, self.formapago.nombre)

    class Meta:
        db_table = 'pytrade_pagos'


class Ticket(models.Model):
    user = models.ForeignKey(User)
    sucursal = models.ForeignKey('home.Sucursal')
    pago = models.ManyToManyField(Pago)
    #formapago = models.ForeignKey(FormaPago)
    #moneda = models.ForeignKey(Moneda, default=Moneda.objects.get(codigo='Gs'))  # Moneda de Pago
    paquete = models.ManyToManyField(Paquete)
    numero = models.CharField(max_length=60, blank=True)
    fecha = models.DateTimeField(auto_now_add=True, null=True)
    # Operaciones
    # Peso del Envio calculado por el Sistema (En Kg)
    peso_sistema = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    cantidad_paquete = models.IntegerField(default=1)
    # Peso del Envio Cobrado por el Personal de PyTrade cuando entrega el Paquete (En Kg)
    peso_cobrado = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    monto_seguro = models.BigIntegerField(default=0)
    monto_gs = models.BigIntegerField()
    monto_dolar = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    descuentos = models.IntegerField(default=0, blank=True)

    def __unicode__(self):
        return "%s - ID=%s" % (self.user.get_full_name(), self.id)

    class Meta:
        db_table = 'pytrade_tickets'

    def get_total_gs(self):
        p = self.pago.filter(moneda__codigo='Gs').aggregate(total_gs=Sum('monto'))
        return p['total_gs']

    def get_total_dolar(self):
        p = self.pago.filter(moneda__codigo='USD').aggregate(total_dolar=Sum('monto'))
        return p['total_dolar']


class Caja(models.Model):
    def path(self, filename):
        path = "arqueo-caja/%s/%s/%s/%s" % (self.sucursal, self.created_at.strftime('%Y'), self.created_at.strftime('%m'),  filename)
        return path
    TIPO_CAJA = (
        ("APERTURA", "APERTURA"),
        ("CIERRE", "CIERRE"),
    )
    user = models.ForeignKey(User)
    sucursal = models.ForeignKey('home.Sucursal')
    caja_asociada = models.ForeignKey('self', null=True, blank=True)
    tipo = models.CharField(max_length=30, choices=TIPO_CAJA)
    monto_gs = models.BigIntegerField(blank=True)
    monto_dolar = models.DecimalField(max_digits=10, decimal_places=2, blank=True)
    faltante_gs = models.BigIntegerField(default=0, blank=True)
    faltante_dolar = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    sobrante_gs = models.BigIntegerField(default=0, blank=True)
    sobrante_dolar = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    cerrada = models.BooleanField(default=False)
    comentario = models.CharField(max_length=2000, blank=True)
    arqueo = models.FileField(upload_to=path)
    created_at = models.DateTimeField(db_column='fecha', auto_now_add=True)

    def __unicode__(self):
        return "ID: %s %s Gs: %s Dolar:%s" % (self.id, self.tipo, self.monto_gs, self.monto_dolar)

    class Meta:
        db_table = 'pytrade_cajas'


class Banco(models.Model):
    nombre = models.CharField(max_length=50)

    def __unicode__(self):
        return "%s" % self.nombre

    class Meta:
        db_table = 'pytrade_bancos'


class MotivoMovimiento(models.Model):
    TIPO_MOVIMIENTO = (
        ("EGRESO", "EGRESO"),
        ("INGRESO", "INGRESO"),
    )
    nombre = models.CharField(max_length=60)
    codigo = models.CharField(max_length=10, blank=True)
    tipo = models.CharField(max_length=30, choices=TIPO_MOVIMIENTO)
    created_at = models.DateTimeField(db_column='fecha', auto_now_add=True)

    def __unicode__(self):
        return "%s" % self.nombre

    class Meta:
        db_table = 'pytrade_motivomovimiento'
        verbose_name_plural = "motivos de Movimiento"


class Movimiento(models.Model):
    user = models.ForeignKey(User)
    sucursal = models.ForeignKey('home.Sucursal')
    formapago = models.ForeignKey(FormaPago, verbose_name='Forma de Pago')
    moneda = models.ForeignKey(Moneda, default=Moneda.objects.get(codigo='Gs'))  # Moneda de Pago
    motivo = models.ForeignKey(MotivoMovimiento)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    descripcion = models.CharField(max_length=100, blank=True, verbose_name='Descripción')
    created_at = models.DateTimeField(db_column='fecha', auto_now_add=True)

    def __unicode__(self):
        return "%s %s-> %s %s" % (self.motivo.tipo, self.motivo, self.monto, self.moneda)

    class Meta:
        db_table = 'pytrade_movimientos'


# Sobre escribi natural_key del Proveedor [Usado al serializar JSON]
class ProveedorManager(models.Manager):
    def unatural_key(self):
        return self.nombre
    Proveedor.natural_key = unatural_key


# Clase para comunicar con el sistema tere
class PreManifiesto(models.Model):
    lote = models.IntegerField()
    fecha = models.DateField()
    codigo = models.CharField(max_length=70)
    cliente = models.CharField(max_length=500)
    peso = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    descripcion = models.CharField(max_length=500)
    valor_dolar = models.DecimalField(max_digits=12, decimal_places=2)
    tipo = models.CharField(max_length=10)

    def __unicode__(self):
        return "Lote:%s - %s %s | %s kg" % (self.lote, self.codigo, self.cliente, self.peso)

    class Meta:
        db_table = 'pytrade_premanifiestos'


class Talonario(models.Model):
    sucursal = models.ForeignKey('home.Sucursal')
    timbrado = models.TextField(max_length=25)
    desde = models.IntegerField()
    hasta = models.IntegerField()
    actual = models.IntegerField()
    fecha_vigencia_inicio = models.DateField()
    fecha_vigencia_fin = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return "%s %s [%s-%s]" % (self.timbrado, self.sucursal, self.desde, self.hasta)

    class Meta:
        db_table = 'systrack_talonarios'


class Factura(models.Model):
    cliente = models.ForeignKey('home.ClienteFactura')
    sucursal = models.ForeignKey('home.Sucursal')
    moneda = models.ForeignKey('Moneda')
    numero = models.CharField(max_length=30)
    monto_cambio = models.DecimalField(max_digits=15, decimal_places=2)
    fecha = models.DateField()
    plazo = models.IntegerField(default=0)  # Se utiliza para Contado/Credito
    total = models.DecimalField(max_digits=15, decimal_places=2)
    total_iva = models.DecimalField(max_digits=15, decimal_places=2)
    neto = models.DecimalField(max_digits=15, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return "%s %s" % (self.numero, self.cliente)

    class Meta:
        db_table = 'systrack_facturas'

    def get_total_exenta(self):
        r = self.facturadetalle_set.all().aggregate(e=Sum('exenta'))
        return r['e']

    def get_total_iva(self):
        r = self.facturadetalle_set.all().aggregate(i=Sum('iva'))
        return r['i']


class FacturaDetalle(models.Model):
    factura = models.ForeignKey('Factura')
    ticket = models.ForeignKey('Ticket')
    cantidad = models.IntegerField(default=1)
    descripcion = models.TextField(max_length=100, default='Servicio de Flete')
    exenta = models.DecimalField(max_digits=15, decimal_places=2)
    iva = models.DecimalField(max_digits=15, decimal_places=2)

    def __unicode__(self):
        return "Fact Nro: %s Ticket:[%s] %s" % (self.factura.id,self.ticket.id,  self.ticket.user.get_full_name())

    class Meta:
        db_table = 'systrack_facturadetalles'
