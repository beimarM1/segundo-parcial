from django.db import models
from producto.models import Producto
from users.models import CustomUser
from venta.models import Venta

class Mantenimiento(models.Model):
    TIPO_CHOICES = [
        ('preventivo', 'Preventivo'),
        ('correctivo', 'Correctivo')
    ]
    
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_proceso', 'En Proceso'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado')
    ]

    producto = models.ForeignKey(
        Producto, 
        on_delete=models.CASCADE,
        related_name='mantenimientos'
    )
    
    tecnico = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        limit_choices_to={'rol__nombre': 'Técnico'},
        related_name='mantenimientos_tecnico'
    )
    
    cliente = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'rol__nombre': 'Cliente'},
        related_name='mantenimientos_cliente'
    )
    
    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name='mantenimientos'
    )
    
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_realizacion = models.DateTimeField(null=True, blank=True)
    tipo_mantenimiento = models.CharField(max_length=50, choices=TIPO_CHOICES)
    estado = models.CharField(max_length=50, choices=ESTADO_CHOICES, default='pendiente')
    descripcion = models.CharField(max_length=255, null=False, default="Descripción no disponible")
    cubierto_por_garantia = models.BooleanField(default=False)
    costo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notas_tecnico = models.TextField(blank=True, null=True, help_text="Notas del técnico sobre el trabajo realizado")

    class Meta:
        ordering = ['-fecha_solicitud']
        verbose_name = 'Mantenimiento'
        verbose_name_plural = 'Mantenimientos'

    def __str__(self):
        return f"Mantenimiento #{self.id} - {self.producto.nombre} ({self.estado})"