#!/usr/bin/env python3
"""
Script de prueba para verificar la configuración de Celery
"""

import os
import sys
import django
from django.conf import settings

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webservice.settings')
django.setup()

def test_celery_configuration():
    """Prueba la configuración de Celery"""
    print("🔍 Verificando configuración de Celery...")
    
    try:
        from webservice.celery import app
        print("✅ Celery app configurado correctamente")
        
        # Verificar configuración
        print(f"📋 Broker URL: {app.conf.broker_url}")
        print(f"📋 Result Backend: {app.conf.result_backend}")
        print(f"📋 Timezone: {app.conf.timezone}")
        
        return True
    except Exception as e:
        print(f"❌ Error en configuración de Celery: {e}")
        return False

def test_redis_connection():
    """Prueba la conexión a Redis"""
    print("\n🔍 Verificando conexión a Redis...")
    
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Conexión a Redis exitosa")
        return True
    except Exception as e:
        print(f"❌ Error conectando a Redis: {e}")
        print("💡 Asegúrate de que Redis esté ejecutándose:")
        print("   sudo systemctl start redis")
        return False

def test_task_import():
    """Prueba la importación de tareas"""
    print("\n🔍 Verificando importación de tareas...")
    
    try:
        from rest.modules.upgrade_so.tasks import upgrade_switch_task, upgrade_multiple_switches_task
        print("✅ Tareas importadas correctamente")
        return True
    except Exception as e:
        print(f"❌ Error importando tareas: {e}")
        return False

def test_django_settings():
    """Prueba la configuración de Django"""
    print("\n🔍 Verificando configuración de Django...")
    
    try:
        # Verificar configuración de Celery en settings
        celery_broker = getattr(settings, 'CELERY_BROKER_URL', None)
        celery_result = getattr(settings, 'CELERY_RESULT_BACKEND', None)
        
        if celery_broker and celery_result:
            print("✅ Configuración de Celery en Django settings correcta")
            return True
        else:
            print("❌ Configuración de Celery faltante en Django settings")
            return False
    except Exception as e:
        print(f"❌ Error verificando Django settings: {e}")
        return False

def test_worker_startup():
    """Simula el inicio de un worker"""
    print("\n🔍 Verificando capacidad de inicio de worker...")
    
    try:
        from webservice.celery import app
        
        # Verificar que las tareas estén registradas
        registered_tasks = app.tasks.keys()
        upgrade_tasks = [task for task in registered_tasks if 'upgrade' in task]
        
        if upgrade_tasks:
            print(f"✅ Tareas de upgrade registradas: {upgrade_tasks}")
            return True
        else:
            print("❌ No se encontraron tareas de upgrade registradas")
            return False
    except Exception as e:
        print(f"❌ Error verificando worker: {e}")
        return False

def main():
    """Función principal de pruebas"""
    print("🚀 Iniciando pruebas de configuración de Celery\n")
    
    tests = [
        ("Configuración de Celery", test_celery_configuration),
        ("Conexión a Redis", test_redis_connection),
        ("Importación de tareas", test_task_import),
        ("Configuración de Django", test_django_settings),
        ("Capacidad de worker", test_worker_startup),
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
    print("📊 RESUMEN DE PRUEBAS")
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
        print("\n🎉 ¡Todas las pruebas pasaron! El sistema está listo para usar.")
        print("\n📝 Para iniciar el worker:")
        print("   cd scripts/apis")
        print("   celery -A webservice worker --loglevel=info --concurrency=4 --queues=upgrade_so")
    else:
        print(f"\n⚠️  {total - passed} prueba(s) falló(aron). Revisa los errores arriba.")
        print("\n💡 Comandos útiles:")
        print("   sudo systemctl start redis")
        print("   pip install -r requirements.txt")
        print("   python manage.py migrate")

if __name__ == "__main__":
    main() 