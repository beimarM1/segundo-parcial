from rest_framework import serializers
from .models import Producto

class ProductoSerializer(serializers.ModelSerializer):
    marca_nombre = serializers.CharField(source="marca.nombre", read_only=True)
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    precio_con_descuento = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )  # Agregar el campo precio_con_descuento

    class Meta:
        model = Producto
        fields = [
            "id",
            "nombre",
            "descripcion",
            "precio",
            "precio_con_descuento",  # Incluir el precio con descuento en el serializer
            "stock",
            "marca",
            "marca_nombre",
            "categoria",
            "categoria_nombre",
            "imagen",
            "estado",
            "garantia",
            "fecha_creacion",
            "descuento",  # Agregar descuento
            "fecha_inicio_descuento",  # Agregar fecha de inicio del descuento
            "fecha_fin_descuento",  # Agregar fecha de fin del descuento
        ]
