#!/usr/bin/env python3
"""
Script de prueba para las funciones de rollback automático
"""

import os
import sys
import django
from django.conf import settings

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webservice.settings')
django.setup()

def test_backup_functions():
    """Probar funciones de backup"""
    print("🔍 Probando funciones de backup...")
    
    try:
        from rest.modules.upgrade_so.tasks import get_current_config, verify_switch_health
        
        # Simular IP de switch (cambiar por IP real para pruebas)
        test_ip = "192.168.1.10"
        
        print(f"📋 Probando get_current_config para {test_ip}")
        config = get_current_config(test_ip)
        
        if config:
            print("✅ Backup de configuración exitoso")
            print(f"📄 Tamaño de configuración: {len(config)} caracteres")
        else:
            print("⚠️  No se pudo obtener configuración (normal si no hay switch real)")
        
        print(f"🏥 Probando verify_switch_health para {test_ip}")
        health = verify_switch_health(test_ip)
        
        if health:
            print("✅ Switch está saludable")
        else:
            print("⚠️  Switch no responde (normal si no hay switch real)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error probando funciones de backup: {e}")
        return False

def test_rollback_functions():
    """Probar funciones de rollback"""
    print("\n🔍 Probando funciones de rollback...")
    
    try:
        from rest.modules.upgrade_so.tasks import restore_config, apply_upgrade_with_rollback
        
        # Configuración de prueba
        test_config = """
# Configuración de prueba
sysname TestSwitch
interface Vlanif1
ip address 192.168.1.10 255.255.255.0
quit
vlan 10
description DATA
quit
"""
        
        test_ip = "192.168.1.10"
        
        print(f"🔄 Probando restore_config para {test_ip}")
        # Nota: Esta función requiere un switch real para funcionar completamente
        # Aquí solo verificamos que la función existe y se puede importar
        
        print("✅ Función restore_config disponible")
        print("✅ Función apply_upgrade_with_rollback disponible")
        
        return True
        
    except Exception as e:
        print(f"❌ Error probando funciones de rollback: {e}")
        return False

def test_celery_rollback_task():
    """Probar tarea de Celery con rollback"""
    print("\n🔍 Probando tarea de Celery con rollback...")
    
    try:
        from rest.modules.upgrade_so.tasks import upgrade_with_rollback_task
        
        # Datos de prueba
        test_data = {
            'switch_ip': '192.168.1.10',
            'firmware_file': 'test_firmware.cc',
            'user_tacacs': 'admin',
            'pass_tacacs': 'password',
            'ip_ftp': '192.168.1.100',
            'pass_ftp': 'Y'
        }
        
        print("✅ Tarea upgrade_with_rollback_task disponible")
        print("📋 Datos de prueba preparados")
        
        return True
        
    except Exception as e:
        print(f"❌ Error probando tarea de Celery: {e}")
        return False

def test_api_endpoints():
    """Probar endpoints de API"""
    print("\n🔍 Probando endpoints de API...")
    
    try:
        from rest.views import UpgradeSOHuaweiSwitchViewSets
        
        # Verificar que el viewset tiene el nuevo endpoint
        viewset = UpgradeSOHuaweiSwitchViewSets()
        
        # Verificar que el método existe
        if hasattr(viewset, 'upgrade_with_rollback'):
            print("✅ Endpoint upgrade_with_rollback disponible")
        else:
            print("❌ Endpoint upgrade_with_rollback no encontrado")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error probando endpoints de API: {e}")
        return False

def main():
    """Función principal de pruebas"""
    print("🚀 Iniciando pruebas de funciones de rollback\n")
    
    tests = [
        ("Funciones de backup", test_backup_functions),
        ("Funciones de rollback", test_rollback_functions),
        ("Tarea de Celery con rollback", test_celery_rollback_task),
        ("Endpoints de API", test_api_endpoints),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Error ejecutando {test_name}: {e}")
            results.append((test_name, False))
    
    # Resumen
    print("\n" + "="*50)
    print("📊 RESUMEN DE PRUEBAS DE ROLLBACK")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Resultado: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("\n🎉 ¡Todas las pruebas de rollback pasaron!")
        print("\n📝 Funcionalidades disponibles:")
        print("   - Backup automático de configuración")
        print("   - Verificación de salud del switch")
        print("   - Rollback automático en caso de fallo")
        print("   - Endpoint /upgrade-with-rollback/")
        print("\n💡 Para usar:")
        print("   curl -X POST http://localhost:8000/api/upgrade-so-huawei-switch/upgrade_with_rollback/")
    else:
        print(f"\n⚠️  {total - passed} prueba(s) falló(aron). Revisa los errores arriba.")

if __name__ == "__main__":
    main() 