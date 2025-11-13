from django.db import models
from django.utils import timezone

class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    garantia = models.IntegerField(default=1)  # Duración de la garantía en días
    marca = models.ForeignKey(
        "marca.Marca", on_delete=models.CASCADE, related_name="productos"
    )
    categoria = models.ForeignKey(
        "categoria.Categoria", on_delete=models.CASCADE, related_name="productos"
    )
    imagen = models.URLField(blank=True, null=True)
    estado = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    # Atributos para el descuento
    descuento = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00
    )  # 0.00 es el descuento inicial
    fecha_inicio_descuento = models.DateTimeField(null=True, blank=True)
    fecha_fin_descuento = models.DateTimeField(null=True, blank=True)

    # Precio con descuento calculado
    precio_con_descuento = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00
    )

    def __str__(self):
        return self.nombre



    # ... tus campos ...

    def save(self, *args, **kwargs):
        # ✅ Verificamos que ambas fechas existan antes de comparar
        if (
            self.fecha_inicio_descuento
            and self.fecha_fin_descuento
            and self.fecha_inicio_descuento <= timezone.now().date() <= self.fecha_fin_descuento
        ):
            # Descuento activo → aplicar precio con descuento
            if self.descuento:
                self.precio_con_descuento = self.precio - (self.precio * self.descuento / 100)
        else:
            # Sin descuento o fuera de rango → restaurar precio normal
            self.precio_con_descuento = self.precio

        super().save(*args, **kwargs)





