from django.db import models

# Create your models here.


class AnexosUpload(models.Model):
    key = models.CharField(primary_key=True, max_length=10)
    anexo = models.CharField(max_length=10, null=False)


class AnexosRegistros(models.Model):
    anexo = models.ForeignKey("AnexosUpload", on_delete=models.CASCADE, null=False)
    status = models.BooleanField(null=False)
    registro = models.DateTimeField(null=False)