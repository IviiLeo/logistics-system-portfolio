from django.db import models
from empleados.models import Transportista

class HojaDeRuta(models.Model):
    fecha = models.DateField()
    
    transportista = models.ForeignKey(
        Transportista, 
        on_delete=models.PROTECT, 
        related_name='hojas_asignadas'
    )

    def __str__(self):
        return f"HR-{self.id} | {self.fecha} | Transportista: {self.transportista}"
