from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.hashers import make_password

# Create your models here.

# Tabla 1: Persona (Base de empleado)
class Persona(models.Model):
    dni = models.CharField(
        max_length=8,
        unique=True,
        validators=[
            RegexValidator(regex=r'^\d{8}$', message='El DNI debe tener exactamente 8 números.')
        ]
    )
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    domicilio = models.CharField(max_length=200)
    numero_telefonico = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(regex=r'^\d+$', message='El número de teléfono debe contener solo dígitos.')
        ]
    )
    mail = models.EmailField(unique=True)  

    def __str__(self):
        return f"{self.nombre} {self.apellido} - DNI: {self.dni}"

# Tabla 2: Transportista (Hereda de Persona)
class Transportista(Persona):
    cbu = models.CharField(
        max_length=22,
        validators=[
            RegexValidator(regex=r'^\d{22}$', message='El CBU debe tener exactamente 22 números.')
        ]
    )
    alias = models.CharField(max_length=50)
    pin = models.CharField(max_length=128) # Como va a encriptarse, definimos longitud 128 caracteres.
    estado = models.BooleanField(default=True) # True = activo, False = inactivo

    def save(self, *args, **kwargs):
        if not self.pin.startswith('pbkdf2_'):
            # Verificamos primero que sean 4 dígitos antes de encriptarlo para cumplir tu regla
            if len(self.pin) == 4 and self.pin.isdigit():
                self.pin = make_password(self.pin)
            else: # Si desde la vista intentan mandarle un PIN inválido, la base de datos lo rechaza
                raise ValueError("El PIN ingresado debe ser de exactamente 4 números")
        super().save(*args, **kwargs)

# Tabla 3: Administrativo (Hereda de Persona)
class Administrativo(Persona):
    contrasena = models.CharField(max_length=128)
    ejecutivo = models.BooleanField(default=False) # True = tiene permisos ejecutivos
    estado = models.BooleanField(default=True)

    # Encriptamos la contraseña antes de guardar
    def save(self, *args, **kwargs):
        if not self.contrasena.startswith('pbkdf2_'):
            self.contrasena = make_password(self.contrasena)
        super().save(*args, **kwargs)
