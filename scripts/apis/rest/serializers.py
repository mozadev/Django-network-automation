from django.contrib.auth.models import Group, User
from rest_framework import serializers
from datetime import datetime, date
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



class InternetUpgradeSerializer(serializers.Serializer):
    user_tacacs = serializers.CharField(required=True, label="Usuario TACACS")
    pass_tacacs = serializers.CharField(style={'input_type': 'password'}, label="Password TACACS")
    cid = serializers.CharField(required=True, label="CID", help_text="Ingresar los ciruitos de internet separados por un enter", max_length=1000, style={"base_template": "textarea.html", "rows": 3})
    newbw = serializers.IntegerField(required=True, min_value=0, label="Nuevo Ancho de Banda (Mbps)")
    commit = serializers.ChoiceField(required=True, choices=["N", "Y"], allow_blank=False, html_cutoff=1, initial="N", style={"base_template": "radio.html"}, label="¿Guardar/Commitear los cambios?")
    

class InterfacesStatusHuaweiSerializer(serializers.Serializer):
    upload_excel = serializers.FileField(allow_empty_file=False, label="UPLOAD IP GESTION")
    

class ReadCorreosPSTSerializer(serializers.Serializer):
    upload_pst = serializers.FileField(allow_empty_file=False, label="UPLOAD PST FILE")


class UpgradeSOHuaweiSwitchSerializer(serializers.Serializer):
    ip_switch = serializers.CharField(required=True, label="IPv4 del SWITCH", help_text="Ingresar las IPv4 separados por un Enter", max_length=1000, style={"base_template": "textarea.html", "rows": 3})
    so_upgrade = serializers.CharField(required=True, label="Nuevo Sistema Operativo Huawei")
    parche_upgrade = serializers.CharField(required=True, label="Nuevo Parche del Sistema Operativo Huawei")


class UploadCorreosTicketsSerializer(serializers.Serializer):
    correos_zenaida_csv = serializers.FileField(allow_empty_file=False, label="UPLOAD CORREOS DE ZENAIDA EN CSV", required=True)
    correos_mpfn_csv = serializers.FileField(allow_empty_file=False, label="UPLOAD CORREOS OTROS-MPFN EN CSV", required=True)
    correos_entrada_csv = serializers.FileField(allow_empty_file=False, label="UPLOAD CORREOS DE BANDEJA DE ENTRADA EN CSV", required=True)
    correos_fecha = serializers.DateField(initial=date.today(), label="FECHA DE UPLOAD CORREO", required=True)

    def validate_correos_zenaida_csv(self, value):
        if not value.name.endswith('.csv'):
            raise serializers.ValidationError("Solo se permiten archivos con formato .csv de la bandeja ZENAIDA")
        if value.content_type != 'text/csv':
            raise serializers.ValidationError("El archivo debe ser de tipo CSV.")
        return value
    
    def validate_correos_mpfn_csv(self, value):
        if not value.name.endswith('.csv'):
            raise serializers.ValidationError("Solo se permiten archivos con formato .csv de la bandeja OTROS-MPFN")
        if value.content_type != 'text/csv':
            raise serializers.ValidationError("El archivo debe ser de tipo CSV.")
        return value
    
    def validate_correos_entrada_csv(self, value):
        if not value.name.endswith('.csv'):
            raise serializers.ValidationError("Solo se permiten archivos con formato .csv de la BANDEJA DE ENTRADA")
        if value.content_type != 'text/csv':
            raise serializers.ValidationError("El archivo debe ser de tipo CSV.")
        return value


class UploadSGATicketsSerializer(serializers.Serializer):
    sga_csv = serializers.FileField(allow_empty_file=False, label="UPLOAD SGA CSV", required=True)
    sga_fecha = serializers.DateField(initial=date.today(), label="FECHA DEL SGA", required=True)

    def validate_sga_csv(self, value):
        if not value.name.endswith('.csv'):
            raise serializers.ValidationError("Solo se permiten archivos con formato .csv del SGA")
        if value.content_type != 'text/csv':
            raise serializers.ValidationError("El archivo debe ser de tipo CSV.")
        return value

