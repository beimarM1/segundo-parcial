from rest_framework.routers import DefaultRouter
from .views import DescuentoViewSet
from django.urls import path

router = DefaultRouter()
router.register(r'descuentos', DescuentoViewSet, basename='descuento')

# Añadir la ruta personalizada para productos con descuento
urlpatterns = [
    path('descuentos/productos-con-descuento/', DescuentoViewSet.as_view({'get': 'productos_con_descuento'}), name='productos-con-descuento'),
]

# Agregar las rutas generadas por el router
urlpatterns += router.urls
