from django.db import models
from django.conf import settings
from producto.models import Producto
from datetime import datetime
from dateutil.relativedelta import relativedelta  # Correcta importación de relativedelta


class Venta(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
        ('cancelado', 'Cancelado'),
        ('entregado', 'Entregado'),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')

    def __str__(self):
        return f"Venta #{self.id} - {self.usuario.username}"


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad}"



class Garantia(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='garantias_producto')
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='garantia_venta')
    fecha_inicio = models.DateField(auto_now_add=True)
    fecha_fin = models.DateField()
    estado = models.CharField(max_length=50, choices=[('activa', 'Activa'), ('caducada', 'Caducada')])
  


    def __str__(self):
        return f"Garantía de {self.producto.nombre} - {self.estado}"