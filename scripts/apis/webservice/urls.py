"""
URL configuration for webservice project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
#from django.contrib import admin
#from django.urls import path

#urlpatterns = [
#    path('admin/', admin.site.urls),
#]


from django.urls import include, path
from rest_framework import routers
from rest import views
from django.conf import settings
from django.conf.urls.static import static


router = routers.DefaultRouter()
#router.register(r'users', views.UserViewSet)
#router.register(r'groups', views.GroupViewSet)
router.register(r'change-vrf', views.ChangeVRFView, basename="change-vrf")
router.register(r'change-vrf-from-excel', views.ChangeVrfFromExcelView, basename="change-vrf-from-excel")
router.register(r'suspension-and-reconnection', views.SuspensionAndReconnectionView, basename="suspension-and-reconnection")
router.register(r'anexos-upload', views.AnexosUploadCsvViewSet, basename="anexos-upload")
router.register(r'anexos-upload-dashboard', views.AnexosUploadDashboard, basename="anexos-upload-dashboard")
router.register(r'anexos-upload-dashboard-v2', views.AnexosUploadDashboard2, basename="anexos-upload-dashboard-v2")
router.register(r'internet-upgrade', views.InternetUpgrade, basename='internet-upgrade')
router.register(r'interfaces-status-huawei', views.InterfacesStatusHuaweiViewSets, basename='interfaces-status-huawei')
router.register(r"read-pst-file", views.ReadCorreosPSTViewSets, basename='read-pst-file')
router.register(r'upgrade-so-huawei-switch', views.UpgradeSOHuaweiSwitchViewSets, basename='upgrade-so-huawei-switch')
router.register(r'upload-correos-tickets', views.UploadCorreosTicketsViewSet, basename='upload-correos-tickets')
router.register(r'upload-sga-tickets', views.UploadSGATicketsViewSet, basename='upload-sga-tickets')
router.register(r'read-in-device', views.ReadInDeviceViewSet, basename='read-in-device')
router.register(r'get-time-of-reboot', views.GetTimeOfRebootViewSet, basename='get-time-of-reboot')

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path('', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)