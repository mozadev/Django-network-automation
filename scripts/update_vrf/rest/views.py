from django.contrib.auth.models import Group, User
from rest_framework import permissions, viewsets
from rest_framework.views import APIView
from rest.serializers import GroupSerializer, UserSerializer, ChangeVRFSerializer, ChangeVrfFromExcelSerializer
from rest_framework.response import Response
from rest_framework import status
from rest.modules.utils import to_router, clean_excel_changevrf


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
            asnumber = serializer.validated_data["asnumber"]
            pass_cipher = serializer.validated_data["pass_cipher"]
            commit = serializer.validated_data["commit"]

            action = "change_vrf"

            msg = {}
            serializer.validated_data["pass_tacacs"] = "*************"
            msg["data_ingresada"] = serializer.validated_data
            detail, status_code, url_file = to_router(action, user_tacacs, pass_tacacs, router_pe, subinterface_pe, vrf_new, vrf_old, cliente, asnumber, pass_cipher, commit)
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
            cleaned_excel, status_code =  clean_excel_changevrf(excel)
            
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
                    asnumber = item["asnumber"]
                    pass_cipher = item["pass_cipher"]
                    result_item["detail"], result_item["status_code"], result_item["url_file"] = to_router(action, user_tacacs, pass_tacacs, router_pe, subinterface_pe, vrf_new, vrf_old, cliente, asnumber, pass_cipher, commit)
                    result.append(result_item)
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response({"msg": cleaned_excel}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
       