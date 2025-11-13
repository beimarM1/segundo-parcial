from rest_framework import serializers
from .models import Mantenimiento
from producto.models import Producto
from venta.models import Venta
from users.models import CustomUser


class ProductoSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = ['id', 'nombre', 'precio', 'imagen']


class UsuarioSimpleSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'nombre_completo']
    
    def get_nombre_completo(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class VentaSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venta
        fields = ['id', 'fecha', 'total', 'estado']


class MantenimientoSerializer(serializers.ModelSerializer):
    """Serializer completo para lectura con detalles anidados"""
    producto = ProductoSimpleSerializer(read_only=True)
    cliente = UsuarioSimpleSerializer(read_only=True)
    tecnico = UsuarioSimpleSerializer(read_only=True)
    venta = VentaSimpleSerializer(read_only=True)
    
    # Campos para escritura (IDs)
    producto_id = serializers.PrimaryKeyRelatedField(
        queryset=Producto.objects.all(),
        source='producto',
        write_only=True
    )
    venta_id = serializers.PrimaryKeyRelatedField(
        queryset=Venta.objects.all(),
        source='venta',
        write_only=True
    )

    class Meta:
        model = Mantenimiento
        fields = [
            'id',
            'producto', 'producto_id',
            'cliente',
            'tecnico',
            'venta', 'venta_id',
            'fecha_solicitud',
            'fecha_realizacion',
            'tipo_mantenimiento',
            'estado',
            'descripcion',
            'cubierto_por_garantia',
            'costo',
            'notas_tecnico'
        ]
        read_only_fields = [
            'fecha_solicitud',
            'cliente',
            'cubierto_por_garantia'
        ]


class MantenimientoCreateSerializer(serializers.ModelSerializer):
    """Serializer específico para creación de mantenimientos por clientes"""
    
    class Meta:
        model = Mantenimiento
        fields = [
            'producto_id',
            'venta_id',
            'tipo_mantenimiento',
            'descripcion'
        ]
        extra_kwargs = {
            'producto_id': {'source': 'producto'},
            'venta_id': {'source': 'venta'}
        }
    
    producto_id = serializers.PrimaryKeyRelatedField(
        queryset=Producto.objects.all(),
        source='producto'
    )
    venta_id = serializers.PrimaryKeyRelatedField(
        queryset=Venta.objects.all(),
        source='venta'
    )


class MantenimientoAsignarTecnicoSerializer(serializers.ModelSerializer):
    """Serializer para que admin asigne técnico"""
    
    class Meta:
        model = Mantenimiento
        fields = ['tecnico', 'estado', 'notas_tecnico']
    
    tecnico = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.filter(rol__nombre='Técnico')
    )
    
    def validate_estado(self, value):
        if value not in ['pendiente', 'en_proceso']:
            raise serializers.ValidationError(
                "Solo puedes asignar técnico a mantenimientos pendientes o en proceso"
            )
        return value


class MantenimientoActualizarEstadoSerializer(serializers.ModelSerializer):
    """Serializer para actualizar estado y detalles del mantenimiento"""
    
    class Meta:
        model = Mantenimiento
        fields = ['estado', 'fecha_realizacion', 'costo', 'notas_tecnico']
    
    def validate(self, data):
        if data.get('estado') == 'completado' and not data.get('fecha_realizacion'):
            raise serializers.ValidationError({
                'fecha_realizacion': 'Debe especificar la fecha de realización al completar'
            })
        return data