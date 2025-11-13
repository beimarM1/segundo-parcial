from datetime import datetime
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.views import APIView

from .models import Mantenimiento
from .serializers import (
    MantenimientoSerializer,
    MantenimientoCreateSerializer,
    MantenimientoAsignarTecnicoSerializer,
    MantenimientoActualizarEstadoSerializer
)
from venta.models import Venta, DetalleVenta, Garantia
from users.models import CustomUser


class MantenimientoListCreateView(generics.ListCreateAPIView):
    """
    GET: Lista todos los mantenimientos (admin) o del cliente autenticado
    POST: Crea una solicitud de mantenimiento
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        # Si es admin o técnico, ve todos
        if user.is_staff or (hasattr(user, 'rol') and user.rol.nombre == 'Técnico'):
            return Mantenimiento.objects.all().select_related(
                'producto', 'cliente', 'tecnico', 'venta'
            )
        
        # Si es cliente, solo ve los suyos
        return Mantenimiento.objects.filter(cliente=user).select_related(
            'producto', 'cliente', 'tecnico', 'venta'
        )
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return MantenimientoCreateSerializer
        return MantenimientoSerializer

    def perform_create(self, serializer):
        cliente = self.request.user
        producto = serializer.validated_data['producto']
        venta = serializer.validated_data['venta']
        
        # 1. Verificar que la venta pertenece al cliente
        if venta.usuario != cliente:
            raise ValidationError({
                'venta': 'Esta venta no pertenece al usuario autenticado'
            })
        
        # 2. Verificar que el producto está en esa venta
        detalle_existe = DetalleVenta.objects.filter(
            venta=venta,
            producto=producto
        ).exists()
        
        if not detalle_existe:
            raise ValidationError({
                'producto': 'Este producto no está incluido en la venta especificada'
            })
        
        # 3. Verificar si ya hay un mantenimiento pendiente o en proceso
        mantenimiento_activo = Mantenimiento.objects.filter(
            producto=producto,
            venta=venta,
            estado__in=['pendiente', 'en_proceso']
        ).exists()
        
        if mantenimiento_activo:
            raise ValidationError({
                'producto': 'Ya existe un mantenimiento activo para este producto'
            })
        
        # 4. Verificar si está cubierto por garantía
        cubierto_por_garantia = False
        garantia = Garantia.objects.filter(
            producto=producto,
            venta=venta,
            estado='activa'
        ).first()
        
        if garantia and garantia.fecha_fin >= timezone.now().date():
            cubierto_por_garantia = True
        
        # 5. Auto-asignar técnico si existe (opcional, puede dejarse None para que admin asigne)
        tecnico = None
        # tecnico = CustomUser.objects.filter(rol__nombre='Técnico').first()
        
        # 6. Guardar el mantenimiento
        serializer.save(
            cliente=cliente,
            tecnico=tecnico,
            cubierto_por_garantia=cubierto_por_garantia,
            estado='pendiente'
        )


class MantenimientoDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Ver detalle de un mantenimiento
    PUT/PATCH: Actualizar mantenimiento
    DELETE: Eliminar mantenimiento
    """
    serializer_class = MantenimientoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        if user.is_staff:
            return Mantenimiento.objects.all()
        
        # Clientes solo ven los suyos
        return Mantenimiento.objects.filter(cliente=user)


class MantenimientoAsignarTecnicoView(generics.UpdateAPIView):
    """
    Endpoint para que el administrador asigne un técnico a un mantenimiento
    PATCH /api/mantenimientos/{id}/asignar-tecnico/
    """
    queryset = Mantenimiento.objects.all()
    serializer_class = MantenimientoAsignarTecnicoSerializer
    permission_classes = [IsAdminUser]
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Solo se puede asignar si está pendiente
        if instance.estado not in ['pendiente', 'en_proceso']:
            return Response(
                {'error': 'Solo se puede asignar técnico a mantenimientos pendientes o en proceso'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Retornar con el serializer completo
        response_serializer = MantenimientoSerializer(instance)
        return Response(response_serializer.data)


class MantenimientoActualizarEstadoView(generics.UpdateAPIView):
    """
    Endpoint para actualizar el estado del mantenimiento
    PATCH /api/mantenimientos/{id}/actualizar-estado/
    Admin o el técnico asignado pueden actualizar
    """
    queryset = Mantenimiento.objects.all()
    serializer_class = MantenimientoActualizarEstadoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        
        # Solo admin o el técnico asignado puede actualizar
        if not user.is_staff and obj.tecnico != user:
            raise PermissionDenied('No tienes permiso para actualizar este mantenimiento')
        
        return obj
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        # Si se completa, asignar fecha automáticamente si no se envió
        if serializer.validated_data.get('estado') == 'completado':
            if not serializer.validated_data.get('fecha_realizacion'):
                serializer.validated_data['fecha_realizacion'] = timezone.now()
        
        serializer.save()
        
        response_serializer = MantenimientoSerializer(instance)
        return Response(response_serializer.data)


class MisMantenimientosView(generics.ListAPIView):
    """
    Endpoint para que el cliente vea sus propios mantenimientos
    GET /api/mantenimientos/mis-mantenimientos/
    """
    serializer_class = MantenimientoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Mantenimiento.objects.filter(
            cliente=self.request.user
        ).select_related('producto', 'tecnico', 'venta').order_by('-fecha_solicitud')


class MantenimientosPorTecnicoView(generics.ListAPIView):
    """
    Endpoint para que un técnico vea los mantenimientos asignados a él
    GET /api/mantenimientos/mis-asignaciones/
    """
    serializer_class = MantenimientoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if not hasattr(user, 'rol') or user.rol.nombre != 'Técnico':
            raise PermissionDenied('Solo los técnicos pueden acceder a este endpoint')
        
        return Mantenimiento.objects.filter(
            tecnico=user
        ).select_related('producto', 'cliente', 'venta').order_by('-fecha_solicitud')