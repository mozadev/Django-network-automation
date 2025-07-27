from django.contrib.auth.models import Group, User
from rest_framework import permissions, viewsets
from rest.serializers import GroupSerializer, UserSerializer, ChangeVRFSerializer, ChangeVrfFromExcelSerializer, SuspensionAndReconnectionSerializer
from rest.serializers import AnexosUploadCsvSerializer, InternetUpgradeSerializer, InterfacesStatusHuaweiSerializer, ReadCorreosPSTSerializer
from rest.serializers import UpgradeSOHuaweiSwitchSerializer, UploadCorreosTicketsSerializer, UploadSGATicketsSerializer, ReadInDeviceSerializer
from rest.serializers import CreateInformeSerializer
from .models import AnexosRegistros, AnexosUpload
from rest.serializers import GetTimeOfRebootSerializer, ConfigInDeviceSerializer, AnexoDocumentoSerializer, AnexoAnexoSerializer, AnexoRegistroSerializer
from rest.models import AnexoDocumento, AnexoAnexo, AnexoRegistro
from rest.filters import AnexoDocumentoFilters, AnexoAnexoFilters, AnexoRegistroFilters
from rest.paginations import AnexoRegistroPagination, AnexoAnexoPagination
from rest_framework.response import Response
from rest_framework import status
import rest.modules.update_vrf.utils as update_vrf
import rest.modules.suspension.utils as suspension_reconnection
import rest.modules.internet_upgrade.utils as internet_upgrade
import rest.modules.internet_upgrade.claro as internet_upgrade_v2
import rest.modules.interfaces_status.utils as interfaces_status
import rest.modules.upgrade_so.utils as upgrade_so
import rest.modules.read_in_device.utils as read_in_device
import rest.modules.create_informe.utils as create_informe
import rest.modules.get_time_of_reboot.utils as get_time_of_reboot
import rest.modules.config_in_device.utils as config_in_device
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.reverse import reverse
from urllib.parse import urlparse
import pypff
from datetime import datetime
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from .serializers import UpgradeSOHuaweiSwitchSerializer
from .modules.upgrade_so import utils
from .modules.upgrade_so.tasks import upgrade_multiple_switches_task, upgrade_multiple_switches_parallel_task, upgrade_multiple_switches_chord_task, upgrade_with_rollback_task
from celery.result import AsyncResult
from urllib.parse import urlparse
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class GroupViewSet(viewsets.ModelViewSet):
    """
    Esta es una descripción de la vista.

    ### Endpoint:
    - `GET /mi-vista/`

    ### Descripción:
    Este endpoint devuelve un mensaje de prueba.

    ### Parámetros:
    No requiere parámetros.

    ### Respuesta:
    ```json
    {
      "mensaje": "Hola, mundo"
    }
    ```
    """
    queryset = Group.objects.all().order_by('name')
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]


class ChangeVRFView(viewsets.ViewSet):
    """
    ## Aquí va la documentación de la API
    * uno
    * dos
    """
    serializer_class = ChangeVRFSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):

        return Response({"msg": "BIENVENIDO A LA API"})

    def create(self, request):
        serializer = ChangeVRFSerializer(data=request.data)
        if serializer.is_valid():
            user_tacacs = serializer.validated_data["user_tacacs"]
            pass_tacacs = serializer.validated_data["pass_tacacs"]
            router_pe = serializer.validated_data["router_pe"]
            subinterface_pe = serializer.validated_data["subinterace_pe"]
            vrf_old = serializer.validated_data["vrf_old"]
            vrf_new = serializer.validated_data["vrf_new"]
            cliente = serializer.validated_data["cliente"]
            pass_cipher = serializer.validated_data["pass_cipher"]
            commit = serializer.validated_data["commit"]

            action = "change_vrf"

            msg = {}
            serializer.validated_data["pass_tacacs"] = "*************"
            msg["data_ingresada"] = serializer.validated_data
            detail, status_code, url_file = update_vrf.to_router(action, user_tacacs, pass_tacacs, router_pe, subinterface_pe, vrf_new, vrf_old, cliente, pass_cipher, commit)
            msg["detail"] = detail
            msg["url_file"] = url_file

            if status_code == 200:
                return Response(msg, status=status.HTTP_200_OK)
            else:
                return Response(msg, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangeVrfFromExcelView(viewsets.ViewSet):
    """
    ## DOCSTRING
    las columnas del excel: 

    * router_pe
    * subinterface_pe
    * vrf_old
    * vrf_new
    * cliente
    * asnumber
    * pass_cipher 

    """

    serializer_class = ChangeVrfFromExcelSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        return Response({"msg": "BIENVENIDO A LA API"})

    
    def create(self, request):
        serializer = ChangeVrfFromExcelSerializer(data=request.data)
        if serializer.is_valid():
            user_tacacs = serializer.validated_data["user_tacacs"]
            pass_tacacs = serializer.validated_data["pass_tacacs"]
            commit = serializer.validated_data["commit"]
            excel = serializer.validated_data["excel"]
            cleaned_excel, status_code =  update_vrf.clean_excel_changevrf(excel)
            
            action = "change_vrf_from_excel"

            if status_code == 200:
                result = []
                for item in cleaned_excel:
                    result_item = {}
                    router_pe = item["router_pe"]
                    subinterface_pe = item["subinterface_pe"]
                    vrf_old = item["vrf_old"]
                    vrf_new = item["vrf_new"]
                    cliente = item["cliente"]
                    pass_cipher = item["pass_cipher"]
                    result_item["detail"], result_item["status_code"], result_item["url_file"] = update_vrf.to_router(action, user_tacacs, pass_tacacs, router_pe, subinterface_pe, vrf_new, vrf_old, cliente, pass_cipher, commit)
                    result.append(result_item)
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response({"msg": cleaned_excel}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
       

class SuspensionAndReconnectionView(viewsets.ViewSet):
    """
    DOCSTRING 
    """
    serializer_class = SuspensionAndReconnectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):

        return Response({"msg": "BIENVENIDO A SUSPENSION & RECONNECTION"})

    def create(self, request):
        # to_router(action, user_tacacs, pass_tacacs, pe, sub_interface, suspension, commit)
        serializer = SuspensionAndReconnectionSerializer(data=request.data)
        if serializer.is_valid():
            user_tacacs = serializer.validated_data["user_tacacs"]
            pass_tacacs = serializer.validated_data["pass_tacacs"]
            commit = serializer.validated_data["commit"]
            suspender_reconectar = serializer.validated_data["suspender_reconectar"]
            router_pe = serializer.validated_data["router_pe"]
            subinterface_pe = serializer.validated_data["subinterace_pe"]
            
            if suspender_reconectar == "SUSPENDER":
                action = "suspension"
                suspension = True
            else:
                action = "reconnection"
                suspension = False
            
            msg = {}
            msg["detail"], msg["status"], msg["url"] = suspension_reconnection.to_router(action, user_tacacs, pass_tacacs, router_pe, subinterface_pe, suspension, commit)
            serializer.validated_data["pass_tacacs"] = "*************"
            msg["data_ingresada"] = serializer.validated_data

            if msg["status"] == 200:
                return Response(msg, status=status.HTTP_200_OK)
            else:
                return Response(msg, status=status.HTTP_400_BAD_REQUEST)

            
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    

class InternetUpgrade(viewsets.ViewSet):
    """
    Se tiene que ingresar un excel con los campos **cid**, **newbw** y un campo **action** la cual puede ser solamente
    dos valores: _upgrade_ o _downgrade_.
    """
    serializer_class = InternetUpgradeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        return Response(status=status.HTTP_200_OK)
    
    def create(self, request):
        serializer = InternetUpgradeSerializer(data=request.data)
        if serializer.is_valid():
            user_tacacs = serializer.validated_data["user_tacacs"]
            pass_tacacs = serializer.validated_data["pass_tacacs"]
            commit = serializer.validated_data["commit"]
            email = serializer.validated_data["email"]
            cid_newbw = serializer.validated_data["cid_newbw"]

            now = datetime.now()
            try:
                cid_list = internet_upgrade_v2.get_cid_newbw(cid_newbw)
                result = internet_upgrade_v2.proceso(user_tacacs, pass_tacacs, cid_list, now.strftime("%Y%m%d%H%M%S"), commit)
            except internet_upgrade_v2.CustomPexpectError as e:
                return Response({"ERROR": f"{e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception as e:
                return Response({"ERROR": f"{e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            if isinstance(result, list):
                if 2 < 1:
                    create_informe = internet_upgrade.CreateInforme(
                        "templates/informes/upgrade_internet_plantilla.docx", 
                        result,
                        "{fecha}".format(fecha=now.strftime("%d/%m/%Y %H:%M:%S")),
                        "media/internet_upgrade/informes/{now}.docx".format(now=now.strftime("%Y%m%d%H%M%S"))
                        )
                    informe = create_informe.create()
                    send_correos = internet_upgrade.SendMailHitss(informe, email)
                    send_correos.send_email()
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InterfacesStatusHuaweiViewSets(viewsets.ViewSet):
    """
    Esta es la API para obtener el status de las interfaces en cada equipo Huawei.  
    Las columnas en el excel de ingreso debe ser:   
    1. _ip_gestion_

    El comando para obtener los status es: 
    `
    display interface brief
    `

    Los status de las interfaces pueden ser:  
    1. **ACTIVO**: Cuando el Physical y Protocol están en UP.  
    2. **LIBRE**: Cuando el Physical y Protocol están en down.  
    3. **DESCONOCIDO**: Cuando es distinto a ACTIVO y LIBRE.  
    """
    serializer_class = InterfacesStatusHuaweiSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        return Response(status=status.HTTP_200_OK)
    
    def create(self, request):
        serializer = InterfacesStatusHuaweiSerializer(data=request.data)
        if serializer.is_valid() :
            upload_excel = serializer.validated_data["upload_excel"]

            list_ip_gestion = interfaces_status.list_ip(upload_excel)
            link = reverse("interfaces-status-huawei-list", request=request)
            parsed_url = urlparse(link)
            base_url = f"{parsed_url.scheme}://{parsed_url.hostname}:{parsed_url.port}"
            result = interfaces_status.to_server(list_ip_gestion, base_url)
            if result[0] == 400:
                return Response(result[1], status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response(result[1], status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        


class ReadCorreosPSTViewSets(viewsets.ViewSet):
    """
    """
    serializer_class = ReadCorreosPSTSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        return Response({"msg": "Hello"}, status=status.HTTP_200_OK)
    
    def create(self, request):
        serializer = ReadCorreosPSTSerializer(data=request.data)
        if serializer.is_valid():
            upload_pst = serializer.validated_data["upload_pst"]

            file_pst = pypff.file()
            file_pst.open("media/correos_pst/data.pst")
            root_folder = file_pst.get_root_folder()
            
            for subfolder in root_folder.sub_folders:
                for subsubfolder in subfolder.sub_folders:
                    if subsubfolder.get_name() == "ASBANC":
                        for message in subsubfolder.sub_messages:
                            print("===> ", message.subject)

        return Response({"msg": "hello"}, status=status.HTTP_200_OK)


class UpgradeSOHuaweiSwitchViewSets(viewsets.ViewSet):
    """
    Esta es la API para upgrade de SO de SWITCH HUAWEI
    """
    serializer_class = UpgradeSOHuaweiSwitchSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def list(self, request):
        return Response(status=status.HTTP_200_OK)
    
    def create(self, request):
        serializer = UpgradeSOHuaweiSwitchSerializer(data=request.data)
        if serializer.is_valid():
            user_tacacs = serializer.validated_data["user_tacacs"]
            pass_tacacs = serializer.validated_data["pass_tacacs"]
            ip_ftp = serializer.validated_data["ip_ftp"]
            pass_ftp = serializer.validated_data["pass_ftp"]
            ip_switch = serializer.validated_data["ip_switch"]
            so_upgrade = serializer.validated_data["so_upgrade"]
            parche_upgrade = serializer.validated_data["parche_upgrade"]
            download = serializer.validated_data["download"]

            link = reverse("upgrade-so-huawei-switch-list", request=request)
            parsed_url = urlparse(link)
            base_url = f"{parsed_url.scheme}://{parsed_url.hostname}:{parsed_url.port}"
            ip_switch_list = ip_switch.replace("\n", "").split("\r")
            
            # Preparar datos para Celery
            switches_data = []
            for ip in ip_switch_list:
                if ip.strip():  # Ignorar IPs vacías
                    switch_data = {
                        'ip': ip.strip(),
                        'user_tacacs': user_tacacs,
                        'pass_tacacs': pass_tacacs,
                        'ip_ftp': ip_ftp,
                        'pass_ftp': pass_ftp,
                        'so_upgrade': so_upgrade,
                        'parche_upgrade': parche_upgrade,
                        'download': download
                    }
                    switches_data.append(switch_data)
            
            # Ejecutar tarea de Celery (VERSIÓN PARALELA)
            task = upgrade_multiple_switches_parallel_task.delay(switches_data)
            
            return Response({
                'task_id': task.id,
                'status': 'started',
                'message': f'Upgrade iniciado para {len(switches_data)} switches',
                'estimated_time': '4-5 minutos por switch'
            }, status=status.HTTP_202_ACCEPTED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """
        Endpoint para consultar el estado de una tarea de upgrade
        """
        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response(
                {'error': 'task_id es requerido'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        task_result = AsyncResult(task_id)
        
        if task_result.ready():
            if task_result.successful():
                return Response({
                    'task_id': task_id,
                    'status': 'completed',
                    'result': task_result.result
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'task_id': task_id,
                    'status': 'failed',
                    'error': str(task_result.result)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            # Obtener información de progreso si está disponible
            info = task_result.info
            if info:
                return Response({
                    'task_id': task_id,
                    'status': 'in_progress',
                    'progress': info.get('current', 0),
                    'total': info.get('total', 100),
                    'status_message': info.get('status', 'Procesando...')
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'task_id': task_id,
                    'status': 'pending',
                    'message': 'Tarea en cola'
                }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'])
    def legacy_upgrade(self, request):
        """
        Endpoint legacy que usa el método original (para compatibilidad)
        """
        serializer = UpgradeSOHuaweiSwitchSerializer(data=request.data)
        if serializer.is_valid():
            user_tacacs = serializer.validated_data["user_tacacs"]
            pass_tacacs = serializer.validated_data["pass_tacacs"]
            ip_ftp = serializer.validated_data["ip_ftp"]
            pass_ftp = serializer.validated_data["pass_ftp"]
            ip_switch = serializer.validated_data["ip_switch"]
            so_upgrade = serializer.validated_data["so_upgrade"]
            parche_upgrade = serializer.validated_data["parche_upgrade"]
            download = serializer.validated_data["download"]

            link = reverse("upgrade-so-huawei-switch-list", request=request)
            parsed_url = urlparse(link)
            base_url = f"{parsed_url.scheme}://{parsed_url.hostname}:{parsed_url.port}"
            ip_switch_list = ip_switch.replace("\n", "").split("\r")
            
            # Usar método original
            result = utils.to_router(ip_switch_list, base_url, so_upgrade, parche_upgrade, user_tacacs, pass_tacacs, download, ip_ftp, pass_ftp)
            return Response(result, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def upgrade_parallel_group(self, request):
        """
        Endpoint para upgrade PARALELO usando group() (recomendado)
        """
        serializer = UpgradeSOHuaweiSwitchSerializer(data=request.data)
        if serializer.is_valid():
            user_tacacs = serializer.validated_data["user_tacacs"]
            pass_tacacs = serializer.validated_data["pass_tacacs"]
            ip_ftp = serializer.validated_data["ip_ftp"]
            pass_ftp = serializer.validated_data["pass_ftp"]
            ip_switch = serializer.validated_data["ip_switch"]
            so_upgrade = serializer.validated_data["so_upgrade"]
            parche_upgrade = serializer.validated_data["parche_upgrade"]
            download = serializer.validated_data["download"]

            link = reverse("upgrade-so-huawei-switch-list", request=request)
            parsed_url = urlparse(link)
            base_url = f"{parsed_url.scheme}://{parsed_url.hostname}:{parsed_url.port}"
            ip_switch_list = ip_switch.replace("\n", "").split("\r")
            
            # Preparar datos para Celery
            switches_data = []
            for ip in ip_switch_list:
                if ip.strip():  # Ignorar IPs vacías
                    switch_data = {
                        'ip': ip.strip(),
                        'user_tacacs': user_tacacs,
                        'pass_tacacs': pass_tacacs,
                        'ip_ftp': ip_ftp,
                        'pass_ftp': pass_ftp,
                        'so_upgrade': so_upgrade,
                        'parche_upgrade': parche_upgrade,
                        'download': download
                    }
                    switches_data.append(switch_data)
            
            # Ejecutar tarea de Celery PARALELA con group()
            task = upgrade_multiple_switches_parallel_task.delay(switches_data)
            
            return Response({
                'task_id': task.id,
                'status': 'started',
                'message': f'Upgrade PARALELO iniciado para {len(switches_data)} switches',
                'method': 'group() - Procesamiento simultáneo',
                'estimated_time': '4-5 minutos total (paralelo)'
            }, status=status.HTTP_202_ACCEPTED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def upgrade_parallel_chord(self, request):
        """
        Endpoint para upgrade PARALELO usando chord() (con callback)
        """
        serializer = UpgradeSOHuaweiSwitchSerializer(data=request.data)
        if serializer.is_valid():
            user_tacacs = serializer.validated_data["user_tacacs"]
            pass_tacacs = serializer.validated_data["pass_tacacs"]
            ip_ftp = serializer.validated_data["ip_ftp"]
            pass_ftp = serializer.validated_data["pass_ftp"]
            ip_switch = serializer.validated_data["ip_switch"]
            so_upgrade = serializer.validated_data["so_upgrade"]
            parche_upgrade = serializer.validated_data["parche_upgrade"]
            download = serializer.validated_data["download"]

            link = reverse("upgrade-so-huawei-switch-list", request=request)
            parsed_url = urlparse(link)
            base_url = f"{parsed_url.scheme}://{parsed_url.hostname}:{parsed_url.port}"
            ip_switch_list = ip_switch.replace("\n", "").split("\r")
            
            # Preparar datos para Celery
            switches_data = []
            for ip in ip_switch_list:
                if ip.strip():  # Ignorar IPs vacías
                    switch_data = {
                        'ip': ip.strip(),
                        'user_tacacs': user_tacacs,
                        'pass_tacacs': pass_tacacs,
                        'ip_ftp': ip_ftp,
                        'pass_ftp': pass_ftp,
                        'so_upgrade': so_upgrade,
                        'parche_upgrade': parche_upgrade,
                        'download': download
                    }
                    switches_data.append(switch_data)
            
            # Ejecutar tarea de Celery PARALELA con chord()
            task = upgrade_multiple_switches_chord_task.delay(switches_data)
            
            return Response({
                'task_id': task.id,
                'status': 'started',
                'message': f'Upgrade PARALELO con callback iniciado para {len(switches_data)} switches',
                'method': 'chord() - Procesamiento simultáneo + callback',
                'estimated_time': '4-5 minutos total (paralelo)'
            }, status=status.HTTP_202_ACCEPTED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def upgrade_with_rollback(self, request):
        """
        Endpoint para upgrade con rollback automático
        """
        serializer = UpgradeSOHuaweiSwitchSerializer(data=request.data)
        if serializer.is_valid():
            user_tacacs = serializer.validated_data["user_tacacs"]
            pass_tacacs = serializer.validated_data["pass_tacacs"]
            ip_ftp = serializer.validated_data["ip_ftp"]
            pass_ftp = serializer.validated_data["pass_ftp"]
            ip_switch = serializer.validated_data["ip_switch"]
            so_upgrade = serializer.validated_data["so_upgrade"]
            parche_upgrade = serializer.validated_data["parche_upgrade"]
            download = serializer.validated_data["download"]

            # Preparar datos para upgrade con rollback
            upgrade_data = {
                'switch_ip': ip_switch.strip(),
                'firmware_file': so_upgrade,
                'user_tacacs': user_tacacs,
                'pass_tacacs': pass_tacacs,
                'ip_ftp': ip_ftp,
                'pass_ftp': pass_ftp
            }
            
            # Ejecutar tarea de Celery con rollback
            task = upgrade_with_rollback_task.delay(upgrade_data)
            
            return Response({
                'task_id': task.id,
                'status': 'started',
                'message': f'Upgrade con rollback iniciado para {ip_switch}',
                'features': [
                    'Backup automático de configuración',
                    'Verificación de salud del switch',
                    'Rollback automático en caso de fallo',
                    'Monitoreo en tiempo real'
                ],
                'estimated_time': '5-10 minutos'
            }, status=status.HTTP_202_ACCEPTED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UploadCorreosTicketsViewSet(viewsets.ViewSet):
    """
    Esta es la API para procesar los correos a partir
    """
    serializer_class = UploadCorreosTicketsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        return Response(status=status.HTTP_200_OK)
    
    def create(self, request):
        serializer = UploadCorreosTicketsSerializer(data=request.data)
        if serializer.is_valid():
            return Response({"detail": "archivos subidos"}, status=status.HTTP_202_ACCEPTED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class UploadSGATicketsViewSet(viewsets.ViewSet):
    """
    Esta es la API para procesar los tickes del SGA
    """
    serializer_class = UploadSGATicketsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        return Response(status=status.HTTP_200_OK)
    
    def create(self, request):
        serializer = UploadSGATicketsSerializer(data=request.data)
        if serializer.is_valid():
            return Response({"detail": "archivos subidos"}, status=status.HTTP_202_ACCEPTED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        

class ReadInDeviceViewSet(viewsets.ViewSet):
    """
    El excel debe tener una columna con el nombre **ip**
    """
    serializer_class = ReadInDeviceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        return Response(status=status.HTTP_200_OK)
    
    def create(self, request):
        serializer = ReadInDeviceSerializer(data=request.data)
        if serializer.is_valid():
            try:
                try:
                    user_tacacs = serializer.validated_data["user_tacacs"]
                    pass_tacacs = serializer.validated_data["pass_tacacs"]
                    upload_ip = serializer.validated_data["upload_ip"]
                    commands = serializer.validated_data["commands"]
                    email = serializer.validated_data["email"]
                except KeyError:
                    email = None

                list_of_ip =  read_in_device.list_of_ip(upload_ip)
                commands = list(commands.split("\r\n"))
                session = read_in_device.session_in_device(user_tacacs, pass_tacacs, list_of_ip, commands, email)
                if isinstance(session, read_in_device.CustomPexpectError): 
                    raise session
                elif isinstance(session, read_in_device.NotEnterToDevice):
                    raise session
            except read_in_device.IPv4NotValidas as e:
                return Response({"detail": f"ERROR:  {e}", "status": e.code}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except read_in_device.CustomPexpectError as e:
                return Response({"detail": f"ERROR:  {e}", "status": e.code}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception as e:
                return Response({"detail": f"ERROR:  {e}", "status": 501}, status=status.HTTP_501_NOT_IMPLEMENTED)
            else:
                return Response(session, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        

class GetTimeOfRebootViewSet(viewsets.ViewSet):
    """
    API para obtener el tiempo de inicio del dispositivo Cisco/Huawei.  
    La API recibe las credendiales y se adjunta un excel con las ip de los dispositivos, 
    """
    serializer_class = GetTimeOfRebootSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        return Response(status=status.HTTP_200_OK)
    def create(self, request):
        serializer = GetTimeOfRebootSerializer(data=request.data)
        if serializer.is_valid():
            try:
                try:
                    user_tacacs = serializer.validated_data["user_tacacs"]
                    pass_tacacs = serializer.validated_data["pass_tacacs"]
                    upload_ip = serializer.validated_data["upload_ip"]
                    email = serializer.validated_data["email"]
                except KeyError:
                    email = None

                link = reverse("get-time-of-reboot-list", request=request)
                parsed_url = urlparse(link)
                base_url = f"{parsed_url.scheme}://{parsed_url.hostname}:{parsed_url.port}"

                list_ips = get_time_of_reboot.list_of_ip(upload_ip)
                result = get_time_of_reboot.session_in_device(user_tacacs, pass_tacacs, list_ips, email, base_url)
            except Exception as e:
                return Response({"detail": f"ERROR:  {e}", "status": 501}, status=status.HTTP_501_NOT_IMPLEMENTED)
            else:
                if isinstance(result, dict):
                    return Response(result, status=status.HTTP_200_OK)
                else:
                    return Response({"detail": f"ERROR:  {result}", "status": 500}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConfigInDeviceViewSet(viewsets.ViewSet):
    """
    El excel debe tener una columna con el nombre **cid**
    """
    serializer_class = ConfigInDeviceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        return Response(status=status.HTTP_200_OK)
    
    def create(self, request):
        serializer = ConfigInDeviceSerializer(data=request.data)
        if serializer.is_valid():
            try:
                try:
                    user_tacacs = serializer.validated_data["user_tacacs"]
                    pass_tacacs = serializer.validated_data["pass_tacacs"]
                    upload_cid = serializer.validated_data["upload_cid"]
                    commit = serializer.validated_data["commit"]
                    commands = serializer.validated_data["commands"]
                    email = serializer.validated_data["email"]
                except KeyError:
                    email = None

                link = reverse("config-in-device-list", request=request)
                parsed_url = urlparse(link)
                base_url = f"{parsed_url.scheme}://{parsed_url.hostname}:{parsed_url.port}"
                commands = list(commands.split("\r\n"))

                cids = config_in_device.list_of_cid(upload_cid)
                result = config_in_device.session_in_device(user_tacacs, pass_tacacs, cids, commands, commit, email, base_url)
            except read_in_device.CustomPexpectError as e:
                return Response({"detail": f"ERROR:  {e}", "status": e.code}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception as e:
                return Response({"detail": f"ERROR:  {e}", "status": 501}, status=status.HTTP_501_NOT_IMPLEMENTED)
            else:
                return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    


class CreateInformeViewSet(viewsets.ViewSet):
    """
    Esta es la API para crear informes
    """

    serializer_class = CreateInformeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        return Response(status=status.HTTP_200_OK)
    
    def create(self, request):
        serializer = CreateInformeSerializer(data=request.data)
        if serializer.is_valid():
            cliente = serializer.validated_data["cliente"]
            fecha_inicial = serializer.validated_data["fecha_inicial"]
            fecha_final = serializer.validated_data["fecha_final"]
            data = serializer.validated_data["data"]

            try:
                now = datetime.now()
                data_columns_validadas = create_informe.validate_required_columns_from_excel(data)

                fecha_inicial = fecha_inicial.strftime("%d/%m/%Y")
                fecha_final = fecha_final.strftime("%d/%m/%Y")

                result = {
                    "titulo": f"{fecha_inicial} hasta {fecha_final}",
                    "cliente": cliente,
                    "reportes": create_informe.create_reportes_by_ticket_by_client(data_columns_validadas)
                }
              
                crear_informe = create_informe.CreateInforme(
                    "templates/informes/plantilla_pronatel_logo.docx",
                    result,
                    "{fecha}".format(fecha=now.strftime("%Y%m%d%H%M%S")),
                    )
                url_informe = crear_informe.create()

                link = reverse("create-informe-list", request=request)
                parsed_url = urlparse(link)
                base_url = f"{parsed_url.scheme}://{parsed_url.hostname}:{parsed_url.port}"

            except Exception as e:
                return Response({"detail": f"ERROR: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                return Response({"detail": "EXITOSO", "docx": f"{base_url}/{url_informe}"}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        

        

class AnexoDocumentoViewSet(viewsets.ModelViewSet):
    """
    Subir los documentos de los anexos
    """
    queryset = AnexoDocumento.objects.filter(pk__gt=1)
    serializer_class = AnexoDocumentoSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = AnexoDocumentoFilters


class AnexoAnexoViewSet(viewsets.ModelViewSet):
    """
    Ver la lista de Anexos
    """
    queryset = AnexoAnexo.objects.filter(pk__gt=1)
    serializer_class = AnexoAnexoSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = AnexoAnexoFilters
    pagination_class = AnexoAnexoPagination


class AnexoRegistroViewSet(viewsets.ModelViewSet):
    """
    Ver los Registos de los anexos
    """
    queryset = AnexoRegistro.objects.all()
    serializer_class = AnexoRegistroSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = AnexoRegistroFilters
    pagination_class = AnexoRegistroPagination

