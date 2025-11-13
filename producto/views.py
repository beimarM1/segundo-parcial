from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny
from bitacora.models import Bitacora
from users.views import get_client_ip
from .models import Producto
from .serializers import ProductoSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action


class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer
    permission_classes = [AllowAny]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['marca', 'categoria', 'estado']
    search_fields = ['nombre', 'descripcion', 'marca__nombre', 'categoria__nombre']
    ordering_fields = ['precio', 'fecha_creacion', 'nombre']

    def perform_create(self, serializer):
        producto = serializer.save()
        Bitacora.objects.create(
            usuario=self.request.user,
            accion=f"Creó producto: {producto.nombre}",
            ip=get_client_ip(self.request),
            estado=True
        )

    def perform_update(self, serializer):
        producto = serializer.save()
        Bitacora.objects.create(
            usuario=self.request.user,
            accion=f"Actualizó producto: {producto.nombre}",
            ip=get_client_ip(self.request),
            estado=True
        )

    def perform_destroy(self, instance):
        Bitacora.objects.create(
            usuario=self.request.user,
            accion=f"Eliminó producto: {instance.nombre}",
            ip=get_client_ip(self.request),
            estado=True
        )
        instance.delete()

    # Acción personalizada para actualizar el descuento
    @action(detail=True, methods=['patch'])
    def actualizar_descuento(self, request, pk=None):
        producto = self.get_object()  # Obtener el producto por pk
        descuento = request.data.get('descuento')
        fecha_inicio_descuento = request.data.get('fecha_inicio_descuento')
        fecha_fin_descuento = request.data.get('fecha_fin_descuento')

        if descuento is None or fecha_inicio_descuento is None or fecha_fin_descuento is None:
            return Response({"detail": "Faltan parámetros para actualizar el descuento."}, status=status.HTTP_400_BAD_REQUEST)

        # Actualizar el descuento y las fechas
        producto.descuento = descuento
        producto.fecha_inicio_descuento = fecha_inicio_descuento
        producto.fecha_fin_descuento = fecha_fin_descuento
        producto.save()

        # Registrar la acción en la bitácora
        Bitacora.objects.create(
            usuario=self.request.user,
            accion=f"Actualizó descuento para producto: {producto.nombre}",
            ip=get_client_ip(self.request),
            estado=True
        )

        # Retornar el producto actualizado
        serializer = ProductoSerializer(producto)
        return Response(serializer.data, status=status.HTTP_200_OK)
    