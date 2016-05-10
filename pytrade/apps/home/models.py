from django.db import models
from django.contrib.auth.models import User, UserManager
from django.conf import settings


class Vendedor(models.Model):
    user = models.OneToOneField(User)
    cedula = models.CharField(max_length=30, null=True, blank=True)
    celular = models.CharField(max_length=15)

    def __unicode__(self):
        return "%s %s" % (self.user.first_name, self.user.last_name)

    class Meta:
        db_table = "pytrade_vendedores"
        verbose_name_plural = "Vendedores"


class Categoria(models.Model):
    nombre = models.CharField(max_length=30)
    comentarios = models.CharField(max_length=50, null=True, blank=True)
    costo = models.DecimalField(max_digits=5, decimal_places=2)

    def __unicode__(self):
        return self.nombre

    class Meta:
        db_table = "pytrade_categorias"


class Sucursal(models.Model):
    categoria = models.ForeignKey('Categoria')
    nombre = models.CharField(max_length=100)
    mail_info = models.EmailField(null=True, blank=True)
    mail_gerente = models.EmailField(null=True, blank=True)
    direccion = models.CharField(max_length=300)
    telefono = models.CharField(max_length=60, null=True, blank=True)
    celular = models.CharField(max_length=60, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __unicode__(self):
        return self.nombre

    class Meta:
        db_table = "pytrade_sucursales"
        verbose_name_plural = "sucursales"


class Usuario(models.Model):
    user = models.OneToOneField(User)
    sucursal = models.ForeignKey(Sucursal)

    def __unicode__(self):
        return "%s (%s)" % (self.user.username, self.sucursal)

    class Meta:
        db_table = "pytrade_usuarios"


class Cliente(models.Model):
    user = models.OneToOneField(User)
    categoria = models.ForeignKey('Categoria', default=settings.DEFAULT_CATEGORIA_CLIENTE)
    codigo = models.CharField(max_length=100, blank=True)
    cedula = models.CharField(max_length=15, db_index=True)
    ruc = models.CharField(max_length=20, null=True, blank=True)
    celular = models.CharField(max_length=15)
    telefono = models.CharField(max_length=60, null=True, blank=True)
    direccion = models.CharField(max_length=200, null=True, blank=True)
    completo = models.BooleanField(default=False)
    contrato = models.NullBooleanField(default=False)
    vendedor = models.ForeignKey(Vendedor, null=True, blank=True)
    sucursal = models.ForeignKey(Sucursal, default=settings.DEFAULT_SUCURSAL_CLIENTE)

    def __unicode__(self):
        return "%s %s" % (self.user.first_name, self.user.last_name)

    class Meta:
        db_table = "pytrade_clientes"


# class PrePaquete(models.Model):
#     owner = models.ForeignKey('auth.User', related_name='prepaquetes')
#     fecha = models.DateField()
#     codigo_cliente = models.CharField(max_length=70)
#     cliente = models.CharField(max_length=500)
#     codigo_paquete = models.CharField(max_length=70)
#     descripcion = models.CharField(max_length=600)
#     peso = models.DecimalField(max_digits=10, decimal_places=2)
#     tracking = models.CharField(max_length=600)
#     proveedor = models.CharField(max_length=600)
#     #proveedor = models.ForeignKey('home.Proveedor', null=True, blank=True)
#     valor_dolar = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
#     guardado = models.NullBooleanField(default=False, null=True, blank=True)
#     created_at = models.DateTimeField(db_column='fecha_creacion', auto_now_add=True)


# Sobre escribi natural_key del User [Usado al serializar JSON]
class UserManager(models.Manager):
    def unatural_key(self):
        return self.get_full_name()
    User.natural_key = unatural_key

#def user_new_unicode(self):
#    return "%s - PT%s" % (self.get_full_name(), self.cliente.codigo)
# Reemplaza el metodo __unicode__ en class User
#User.__unicode__ = user_new_unicode
User.profile = property(lambda u: Cliente.objects.get_or_create(user=u)[0])


class ClienteFactura(models.Model):
    cliente = models.ForeignKey('Cliente')
    nombre = models.TextField(max_length=500)
    ruc = models.CharField(max_length=30)

    def __unicode__(self):
        return "%s %s" % (self.nombre, self.ruc)