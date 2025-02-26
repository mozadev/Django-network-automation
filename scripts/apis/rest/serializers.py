from django.contrib.auth.models import Group, User
from rest_framework import serializers
from datetime import datetime, date, timedelta
from .models import AnexosRegistros, AnexosUpload
from .models import TicketReport


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
    commit_pe = serializers.ChoiceField(required=True, choices=["N", "Y"], allow_blank=False, html_cutoff=1, initial="N", style={"base_template": "radio.html"}, label="¿Guardar/Commitear los cambios en el PE?")
    commit_acceso = serializers.ChoiceField(required=True, choices=["N", "Y"], allow_blank=False, html_cutoff=1, initial="N", style={"base_template": "radio.html"}, label="¿Guardar/Commitear los cambios en el ACCESO?")
    commit_cpe = serializers.ChoiceField(required=True, choices=["N", "Y"], allow_blank=False, html_cutoff=1, initial="N", style={"base_template": "radio.html"}, label="¿Guardar/Commitear los cambios en el CPE?")
    email = serializers.EmailField(required=False, label="Correo en dónde se enviará los detalles")


class InterfacesStatusHuaweiSerializer(serializers.Serializer):
    upload_excel = serializers.FileField(allow_empty_file=False, label="UPLOAD IP GESTION")
    

class ReadCorreosPSTSerializer(serializers.Serializer):
    upload_pst = serializers.FileField(allow_empty_file=False, label="UPLOAD PST FILE")


class UpgradeSOHuaweiSwitchSerializer(serializers.Serializer):
    user_tacacs = serializers.CharField(required=True, label="Usuario SWITCH")
    pass_tacacs = serializers.CharField(required=True, style={'input_type': 'password'}, label="Password SWITCH")
    ip_ftp = serializers.IPAddressField(required=True, protocol="IPv4",label="SERVIDOR FTP", help_text="Ejemplo: 172.19.216.127")
    pass_ftp = serializers.ChoiceField(required=True, choices=["N", "Y"], allow_blank=False, html_cutoff=1, initial="N", style={"base_template": "radio.html"}, label="Las credenciales del SERVIDOR FTP,¿son las mismas del SWITCH?")
    ip_switch = serializers.CharField(required=True, label="IPv4 del SWITCH", help_text="Ingresar las IPv4 separados por un Enter", max_length=1000, style={"base_template": "textarea.html", "rows": 3})
    so_upgrade = serializers.CharField(required=False, label="Nuevo Sistema Operativo Huawei", help_text="Ejemplo: testing.cc", default=None)
    parche_upgrade = serializers.CharField(required=False, label="Nuevo Parche del Sistema Operativo Huawei", help_text="Ejemplo: testing.pat", default=None)
    download = serializers.ChoiceField(required=True, choices=["N", "Y"], allow_blank=False, html_cutoff=1, initial="N", style={"base_template": "radio.html"}, label="¿Descargar los ficheros?")


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
    sga_csv = serializers.FileField(allow_empty_file=False, label="UPLOAD SGA EXCEL", required=True)
    sga_fecha = serializers.DateField(initial=date.today(), label="FECHA DEL SGA", required=True)

    def validate_sga_csv(self, value):
        if not value.name.endswith('.xlsx'):
            raise serializers.ValidationError("Solo se permiten archivos con formato .xlsx del SGA")
        if value.content_type != 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
            raise serializers.ValidationError("El archivo debe ser de tipo .xlsx")
        return value



class ReadInDeviceSerializer(serializers.Serializer):
    user_tacacs = serializers.CharField(required=True, label="Usuario")
    pass_tacacs = serializers.CharField(required=True, style={'input_type': 'password'}, label="Password")
    upload_ip = serializers.FileField(allow_empty_file=False, label="UPLOAD LIST OF IP", required=True)
    commands = serializers.CharField(required=True, label="Commands", help_text="Ingresar los comandos de solo lectura", max_length=1000, style={"base_template": "textarea.html", "rows": 3})
    email = serializers.EmailField(required=False, label="Correo en dónde se enviará los ficheros de salida")

    def validate_upload_ip(self, value):
        if not value.name.endswith('.xlsx'):
            raise serializers.ValidationError("Solo se permiten archivos con formato .xlsx")
        if value.content_type != 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
            raise serializers.ValidationError("El archivo debe ser de tipo .xlsx")
        return value
    

class CreateInformeSerializer(serializers.Serializer):
    cliente = serializers.CharField(required=True, label="Cliente", max_length=100)
    fecha_inicial = serializers.DateField(initial=date.today(), label="FECHA INICIAL", required=True)
    fecha_final = serializers.DateField(initial=date.today(), label="FECHA FINAL", required=True)
    data = serializers.FileField(allow_empty_file=False, label="UPLOAD DATA", required=True)

    def validate_data(self, value):
        if not value.name.endswith('.xlsx'):
            raise serializers.ValidationError("Solo se permiten archivos con formato .xlsx")
        if value.content_type != 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
            raise serializers.ValidationError("El archivo debe ser de tipo .xlsx")
        return value
    

    def validate(self, data):
        fecha_inicial = data.get('fecha_inicial')
        fecha_final = data.get('fecha_final')

        if fecha_inicial and fecha_final and fecha_inicial > fecha_final:
            raise serializers.ValidationError({
                "fecha_inicial": "La fecha inicial no puede ser mayor que la fecha final."
            })

        return data


class UploadSGATicketsFromFASTAPISerializer(serializers.Serializer):
    fecha_incio = serializers.DateField(
        initial=date.today,
        label="Fecha de Inicio",
        required=True,
        error_messages={
            'required': 'Este campo es obligatorio.',
            'invalid': 'Formato de fecha inválido. Use YYYY-MM-DD.'
        }
    )
    fecha_fin = serializers.DateField(
        initial = date.today,
        label = "Fecha de Fin",
        required=True,
        error_messages={
            'required': 'Este campo es obligatorio.',
            'invalid': 'Formato de fecha inválido. Use YYYY-MM-DD.'
        }
    )

    def validate(self, data):
        fecha_inicio = data.get('fecha_inicio')
        fecha_fin = data.get('fecha_fin')
    
        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            raise serializers.ValidationError({
                "Fecha_inicio": "La fecha de inicio no puede ser mayor que la fecha de fin."
            })
        return data


class TicketReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketReport
        fields = "__all__"
    
