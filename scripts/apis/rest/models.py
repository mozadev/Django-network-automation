from django.db import models

# Create your models here.


class AnexosUpload(models.Model):
    key = models.CharField(primary_key=True, max_length=20)
    anexo = models.CharField(max_length=20, null=False)


class AnexosRegistros(models.Model):
    key = models.ForeignKey("AnexosUpload", on_delete=models.CASCADE, null=False)
    status = models.BooleanField(null=False)
    registro = models.DateTimeField(null=False)
    first = models.BooleanField(null=False, default=False)
    last = models.BooleanField(null=False, default=False)



    