from django.db import models
from django.contrib.auth.models import User
import os
from datetime import datetime
from django.core.exceptions import ValidationError
import re

# Create your models here.

def anexo_name_file(instance, filename):
    ext = os.path.splitext(filename)[1]
    fecha_hora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nombre = f"{instance.usuario.id}_{fecha_hora}{ext}"
    return os.path.join("anexos", nombre)


class AnexoDocumento(models.Model):
    fecha = models.DateTimeField(auto_now_add=True, null=False, blank=False, help_text="Fecha de creación")
    creado_en = models.DateTimeField(null=False, blank=False, help_text="Ingresa la fecha y hora del documento de los Anexos")
    archivo = models.FileField(upload_to=anexo_name_file)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        ordering = ["-pk"]

    
class AnexoAnexo(models.Model):
    key = models.IntegerField(unique=True, null=False, blank=False)
    login = models.EmailField(max_length=100, null=False, blank=False)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    handle = models.EmailField(max_length=100, null=True, blank=True)
    location = models.CharField(max_length=100, null=False, blank=True)
    ip_address = models.CharField(max_length=22, help_text="Formato requerido: IPv4:puerto, ej: 192.168.0.1:8080", null=True, blank=True)
    device_mac = models.CharField(max_length=17, null=True, blank=True)
    device_model = models.CharField(max_length=100, null=True, blank=True)
    device_serial = models.CharField(max_length=100, null=True, blank=True)
    documento_find = models.ForeignKey(AnexoDocumento, on_delete=models.CASCADE, related_name="documento_in_anexo")

    def clean_login(self):
        if not self.login.endswith("@mpfn.gob.pe"):
            raise ValidationError("login debe pertenecer al dominio @mpfn.gob.pe")
        return self.login
    
    def clean_handle(self):
        if self.handle:
            if not self.handle.endswith("@mpfn.gob.pe"):
                raise ValidationError("handle debe pertenecer al dominio @mpfn.gob.pe")
        return self.handle
    
    def clean_ip_address(self):
        value = self.ip_address.strip()
        pattern = r'^(?P<ip>(?:\d{1,3}\.){3}\d{1,3}):(?P<puerto>\d{1,5})$'
        match = re.match(pattern, value)
        
        if not match:
            raise ValidationError("Debe tener el formato IPv4:puerto, ej: 192.168.0.1:8080")

        ip_parts = match.group("ip").split(".")
        if any(int(part) > 255 for part in ip_parts):
            raise ValidationError("La IP no es válida (un segmento es mayor a 255)")

        puerto = int(match.group("puerto"))
        if not (1 <= puerto <= 65535):
            raise ValidationError("El puerto debe estar entre 1 y 65535")

    def clean_mac(self):
        valor = self.device_mac.strip().lower()
        patron_mac = r'^([0-9a-f]{2}:){5}[0-9a-f]{2}$'
        if not re.match(patron_mac, valor):
            raise ValidationError("La dirección MAC no es válida. Debe tener el formato XX:XX:XX:XX:XX:XX")
        return valor

    class Meta:
        ordering = ["-pk"]


class AnexoRegistro(models.Model):
    status = models.BooleanField(default=False)
    anexo = models.ForeignKey(AnexoAnexo, on_delete=models.CASCADE, related_name="anexo_in_registro")
    documento = models.ForeignKey(AnexoDocumento, on_delete=models.CASCADE, related_name="documento_in_registro")

    class Meta:
        ordering = ["-pk"]