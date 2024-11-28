from django.contrib.auth.models import Group, User
from rest_framework import permissions, viewsets
from rest.serializers import GroupSerializer, UserSerializer, ChangeVRFSerializer, ChangeVrfFromExcelSerializer, SuspensionAndReconnectionSerializer
from rest.serializers import AnexosUploadCsvSerializer, InternetUpgradeSerializer, InterfacesStatusHuaweiSerializer, ReadCorreosPSTSerializer
from rest.serializers import UpgradeSOHuaweiSwitchSerializer, UploadCorreosTicketsSerializer, UploadSGATicketsSerializer
from .models import AnexosRegistros, AnexosUpload
from rest_framework.response import Response
from rest_framework import status
import rest.modules.update_vrf.utils as update_vrf
import rest.modules.suspension.utils as suspension_reconnection
import rest.modules.upload_anexos.utils as upload_anexos
import rest.modules.internet_upgrade.utils as internet_upgrade
import rest.modules.interfaces_status.utils as interfaces_status
import rest.modules.upgrade_so.utils as upgrade_so
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.reverse import reverse
from urllib.parse import urlparse
import pypff
from striprtf.striprtf import rtf_to_text

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

        
class AnexosUploadCsvViewSet(viewsets.ViewSet):
    """
    DOCSTRING
    """
    serializer_class = AnexosUploadCsvSerializer
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, pk=None):
        result = {}
        queryset = AnexosRegistros.objects.filter(key__key=pk).order_by("-registro").values()
        if queryset:
            n = len(queryset)
            fecha_final = queryset[0]["registro"]
            fecha_inicial = queryset[n - 1]["registro"]
            for i in queryset:
                if i["status"] == True:
                    fecha_inicial = i["registro"]
                    break
            duration = (fecha_final - fecha_inicial).total_seconds() / 3600
            result["duration_hrs"] = "%.2f" % duration
            result["data"] = queryset
        return Response(result, status=status.HTTP_200_OK)

    def list(self, request):
        dashboard = reverse("anexos-upload-dashboard-list", request=request)
        return Response({"ver-dashboard": dashboard}, status=status.HTTP_200_OK)
    
    def create(self, request):
        serializer = AnexosUploadCsvSerializer(data=request.data)
        if serializer.is_valid():
            upload_excel = serializer.validated_data["upload_excel"]
            upload_fecha = serializer.validated_data["upload_fecha"]
            
            data, status_upload =  upload_anexos.clean_data(upload_excel, upload_fecha)
            if status_upload == 200:
                new_register = []
                anexos_registros = AnexosRegistros.objects.filter(last=True)
                if anexos_registros.count() > 0:
                    first = False
                else:
                    first = True
                anexos_registros.update(last=False)

                for item in data:
                    i = {}
                    anexo, creado = AnexosUpload.objects.get_or_create(
                        key=item["key"],
                        anexo=item["anexo"],
                    )
                    if creado:
                        i["key"] = item["key"]
                        i["anexo"] = item["anexo"]
                        new_register.append(i)

                    AnexosRegistros.objects.create(key=anexo, status=item["status"], registro=item["registro"], last=True, first=first)

                    dashboard = reverse("anexos-upload-dashboard-list", request=request)
                return Response({"msg": "DATOS SUBIDOS EXITOSAMENTE", "ver-dashboard": dashboard, "nuevos": new_register}, status=status.HTTP_200_OK)
            else:
                return Response({"msg": "ERROR"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        

class AnexosUploadDashboard(viewsets.ViewSet):
    """
    DOCSTRING
    """
    permission_classes = [permissions.IsAuthenticated]
    #renderer_classes = [TemplateHTMLRenderer]
    #template_name="anexos_dashboard.html"
    

    def list(self, request):
        result={}
        queryset_first_up = AnexosRegistros.objects.filter(first=True, status=True)
        list_first_up = []
        for i in queryset_first_up:
            list_first_up.append(i.key.key)
        queryset = AnexosRegistros.objects.filter(last=True, status=False, key__key__in=list_first_up)
        
        result["count"] = queryset_first_up.count()
        result["down"]  = queryset.count()
        result["down_rate"] = "%.2f" % ((result["down"] / result["count"])  * 100) 
        result["up"]  = result["count"] - result["down"]
        result["up_rate"] = "%.2f" % (100 - float(result["down_rate"]))

        queryset_values = queryset.values("key__key", "key__anexo", "registro", "status", "last")
        for item in queryset_values:
            item_queryset = AnexosRegistros.objects.filter(key__key=item["key__key"]).order_by("-registro").values()
            if item_queryset:
                n = len(item_queryset)
                fecha_final = item_queryset[0]["registro"]
                fecha_inicial = item_queryset[n - 1]["registro"]
                for i in item_queryset:
                    if i["status"] == True:
                        fecha_inicial = i["registro"]
                        break
                duration = (fecha_final - fecha_inicial).total_seconds() / 3600

            item["duration_hrs"] = "%.2f" % duration
        
        result["data"] = queryset_values
        return Response({"data": result})
    

class AnexosUploadDashboard2(viewsets.ViewSet):
    """
    DOCSTRING
    """
    permission_classes = [permissions.IsAuthenticated]
    renderer_classes = [TemplateHTMLRenderer]
    template_name="anexos_dashboard2.html"
    def list(self, request):
        return Response(status=status.HTTP_200_OK)
    

class InternetUpgrade(viewsets.ViewSet):
    """
    Este es la documentación
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
            cid = serializer.validated_data["cid"]
            newbw = serializer.validated_data["newbw"]
            cid_list = cid.replace("\n", "").split("\r")
            result = internet_upgrade.to_server(user_tacacs, pass_tacacs, cid_list, "xd", commit, newbw)
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
            ip_switch = serializer.validated_data["ip_switch"]
            so_upgrade = serializer.validated_data["so_upgrade"]
            parche_upgrade = serializer.validated_data["parche_upgrade"]
            download = serializer.validated_data["download"]

            link = reverse("upgrade-so-huawei-switch-list", request=request)
            parsed_url = urlparse(link)
            base_url = f"{parsed_url.scheme}://{parsed_url.hostname}:{parsed_url.port}"
            ip_switch_list = ip_switch.replace("\n", "").split("\r")
            
            result = upgrade_so.to_router(ip_switch_list, base_url, so_upgrade, parche_upgrade, user_tacacs, pass_tacacs, download)
            return Response(result, status=status.HTTP_201_CREATED)
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
        