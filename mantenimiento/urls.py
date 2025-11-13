from django.urls import path
from . import views

urlpatterns = [
    # CRUD básico
    path('mantenimientos/', 
         views.MantenimientoListCreateView.as_view(), 
         name='mantenimiento-list-create'),
    
    path('mantenimientos/<int:pk>/', 
         views.MantenimientoDetailView.as_view(), 
         name='mantenimiento-detail'),
    
    # Endpoints especializados para clientes
    path('mantenimientos/mis-mantenimientos/', 
         views.MisMantenimientosView.as_view(), 
         name='mis-mantenimientos'),
    
    # Endpoints para técnicos
    path('mantenimientos/mis-asignaciones/', 
         views.MantenimientosPorTecnicoView.as_view(), 
         name='mantenimientos-tecnico'),
    
    # Endpoints administrativos
    path('mantenimientos/<int:pk>/asignar-tecnico/', 
         views.MantenimientoAsignarTecnicoView.as_view(), 
         name='mantenimiento-asignar-tecnico'),
    
    path('mantenimientos/<int:pk>/actualizar-estado/', 
         views.MantenimientoActualizarEstadoView.as_view(), 
         name='mantenimiento-actualizar-estado'),
]