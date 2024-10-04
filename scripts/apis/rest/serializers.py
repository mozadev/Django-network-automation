from django.contrib.auth.models import Group, User
from rest_framework import serializers
from datetime import datetime
from .models import AnexosRegistros, AnexosUpload


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['url', 'username', 'email', 'groups']


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ['url', 'name']


class ChangeVRFSerializer(serializers.Serializer):
    user_tacacs = serializers.CharField(required=True, label="Usuario TACACS")
    pass_tacacs = serializers.CharField(style={'input_type': 'password'}, label="Password TACACS")
    router_pe = serializers.CharField(required=True, label="Equipo PE")
    subinterace_pe = serializers.CharField(required=True, label="Subinterface del PE")
    vrf_old = serializers.IntegerField(required=True, min_value=0, label="VRF actual", help_text="Ingresar la actual VRF que está en la subinterface")
    vrf_new = serializers.IntegerField(required=True, min_value=0, label="VRF NUEVA", help_text="Ingresar la nueva VRF que se creará")
    cliente = serializers.CharField(required=True, label="Cliente", help_text="Ingresar tal cual el grupo de la VRF, se buscará la vrf: RPVFM_cliente") 
    pass_cipher = serializers.CharField(required=True, label="Cipher Password")
    commit = serializers.ChoiceField(required=True, choices=["N", "Y"], allow_blank=False, html_cutoff=1, initial="N", style={"base_template": "radio.html"}, label="¿Guardar/Commitear loas cambios?")


class ChangeVrfFromExcelSerializer(serializers.Serializer):
    user_tacacs = serializers.CharField(required=True, label="Usuario TACACS")
    pass_tacacs = serializers.CharField(style={'input_type': 'password'}, label="Password TACACS")
    commit = serializers.ChoiceField(required=True, choices=["N", "Y"], allow_blank=False, html_cutoff=1, initial="N", style={"base_template": "radio.html"}, label="¿Guardar/Commitear loas cambios?")
    excel = serializers.FileField(allow_empty_file=False)


class SuspensionAndReconnectionSerializer(serializers.Serializer):
    user_tacacs = serializers.CharField(required=True, label="Usuario TACACS")
    pass_tacacs = serializers.CharField(style={'input_type': 'password'}, label="Password TACACS")
    suspender_reconectar = serializers.ChoiceField(required=True, choices=["SUSPENDER", "RECONECTAR"], allow_blank=False, html_cutoff=2, initial="SUSPENDER", style={"base_template": "select.html"}, label="SUSPENDER / RECONECTAR", html_cutoff_text=None)
    router_pe = serializers.CharField(required=True, label="Equipo PE")
    subinterace_pe = serializers.CharField(required=True, label="Subinterface del PE")
    commit = serializers.ChoiceField(required=True, choices=["N", "Y"], allow_blank=False, html_cutoff=1, initial="N", style={"base_template": "radio.html"}, label="¿Guardar/Commitear loas cambios?")


class AnexosUploadCsvSerializer(serializers.Serializer):
    upload_excel = serializers.FileField(allow_empty_file=False, label="UPLOAD ANEXO")
    upload_fecha = serializers.DateTimeField(initial=datetime.now(), label="FECHA DE UPLOAD")


class AnexosUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnexosUpload
        fields = "__all__"


class AnexosRegistrosSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnexosRegistros
        fields = "__all__"