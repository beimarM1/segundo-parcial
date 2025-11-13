from rest_framework import serializers
from .models import Descuento

# ✅ Serializer SIN producto_detalle (para evitar recursión)
class DescuentoSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Descuento.
    """
    esta_vigente = serializers.SerializerMethodField()
    dias_restantes = serializers.SerializerMethodField()
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)

    class Meta:
        model = Descuento
        fields = [
            'id',
            'producto',
            'porcentaje',
            'fecha_inicio',
            'producto_nombre',  # Este es el nombre del producto
            'fecha_fin',
            'descripcion',
            'activo',
            'fecha_creacion',
            'esta_vigente',
            'dias_restantes'
        ]

    def get_esta_vigente(self, obj):
        """Retorna si el descuento está vigente."""
        return obj.esta_vigente()

    def get_dias_restantes(self, obj):
        """Retorna los días restantes de la promoción."""
        from django.utils import timezone
        if obj.esta_vigente():
            hoy = timezone.now().date()
            dias = (obj.fecha_fin - hoy).days
            return dias
        return 0

    def validate(self, data):
        """Validaciones personalizadas."""
        if data.get('fecha_inicio') and data.get('fecha_fin'):
            if data['fecha_fin'] < data['fecha_inicio']:
                raise serializers.ValidationError(
                    "La fecha de fin no puede ser anterior a la fecha de inicio."
                )
        
        if data.get('porcentaje'):
            if data['porcentaje'] <= 0 or data['porcentaje'] > 100:
                raise serializers.ValidationError(
                    "El porcentaje debe estar entre 0 y 100."
                )
        
        return data


# ✅ Serializer COMPLETO con producto_detalle (solo para vistas de descuentos)
class DescuentoConProductoSerializer(serializers.ModelSerializer):
    """
    Serializer que incluye detalles del producto.
    Usar SOLO en endpoints de descuentos.
    """
    from producto.serializers import ProductoSerializer
    producto_detalle = ProductoSerializer(source='producto', read_only=True)
    esta_vigente = serializers.SerializerMethodField()
    dias_restantes = serializers.SerializerMethodField()

    class Meta:
        model = Descuento
        fields = [
            'id',
            'producto',
            'producto_detalle',
            'porcentaje',
            'fecha_inicio',
            'fecha_fin',
            'descripcion',
            'activo',
            'fecha_creacion',
            'esta_vigente',
            'dias_restantes'
        ]

    def get_esta_vigente(self, obj):
        return obj.esta_vigente()

    def get_dias_restantes(self, obj):
        from django.utils import timezone
        if obj.esta_vigente():
            hoy = timezone.now().date()
            return (obj.fecha_fin - hoy).days
        return 0


class DescuentoCreateSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para crear descuentos.
    """
    class Meta:
        model = Descuento
        fields = [
            'producto',
            'porcentaje',
            'fecha_inicio',
            'fecha_fin',
            'descripcion',
            'activo'
        ]