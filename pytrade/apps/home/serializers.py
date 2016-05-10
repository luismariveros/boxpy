# from rest_framework import serializers
# from django.contrib.auth.models import User
# from pytrade.apps.home.models import PrePaquete
#
#
# class PrePaqueteSerializer(serializers.ModelSerializer):
#     owner = serializers.ReadOnlyField(source='owner.username')
#
#     class Meta:
#         model = PrePaquete
#         fields = ('id', 'owner', 'fecha', 'codigo_cliente', 'cliente', 'codigo_paquete', 'descripcion', 'peso', 'tracking', 'proveedor', 'valor_dolar')
#
#
# class UserSerializer(serializers.ModelSerializer):
#     prepaquetes = serializers.PrimaryKeyRelatedField(many=True, queryset=PrePaquete.objects.all())
#
#     class Meta:
#         model = User
#         fields = ('id', 'username', 'prepaquetes')