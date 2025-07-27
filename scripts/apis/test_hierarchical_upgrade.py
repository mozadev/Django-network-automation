#!/usr/bin/env python3
"""
Script de prueba para el upgrade jerárquico de switches Huawei
Demuestra cómo funciona la selección automática del switch principal
y la distribución optimizada del firmware.
"""

import requests
import json
import time
from datetime import datetime

# Configuración de la API
API_BASE_URL = "http://localhost:8000"
ENDPOINT = f"{API_BASE_URL}/upgrade-so-huawei-switch/upgrade_hierarchical/"

def test_hierarchical_upgrade():
    """
    Prueba el upgrade jerárquico con múltiples switches
    """
    print("🧪 PRUEBA DE UPGRADE JERÁRQUICO")
    print("=" * 50)
    
    # Datos de prueba
    test_data = {
        "user_tacacs": "admin",
        "pass_tacacs": "Admin123",
        "ip_ftp": "192.168.1.100",  # Servidor FTP externo
        "pass_ftp": "Y",
        "ip_switch": """192.168.1.10
192.168.1.11
192.168.1.12
192.168.1.13""",  # 4 switches de prueba
        "so_upgrade": "V200R019C00SPC500.cc",  # Archivo SO
        "parche_upgrade": "V200R019C00SPH012.pat",  # Archivo parche
        "download": "Y"
    }
    
    print(f"📋 Datos de prueba:")
    print(f"   - Switches: {test_data['ip_switch'].count('192.168')} switches")
    print(f"   - SO: {test_data['so_upgrade']}")
    print(f"   - Parche: {test_data['parche_upgrade']}")
    print(f"   - Servidor FTP: {test_data['ip_ftp']}")
    print()
    
    try:
        # 1. INICIAR UPGRADE JERÁRQUICO
        print("🚀 Iniciando upgrade jerárquico...")
        response = requests.post(ENDPOINT, data=test_data)
        
        if response.status_code == 202:
            result = response.json()
            task_id = result['task_id']
            print(f"✅ Upgrade iniciado exitosamente")
            print(f"   - Task ID: {task_id}")
            print(f"   - Método: {result['method']}")
            print(f"   - Tiempo estimado: {result['estimated_time']}")
            print()
            
            # Mostrar características del upgrade jerárquico
            print("🔧 Características del upgrade jerárquico:")
            for feature in result['features']:
                print(f"   ✓ {feature}")
            print()
            
            # Mostrar requisitos de recursos
            print("💾 Requisitos de recursos:")
            for req, value in result['resource_requirements'].items():
                print(f"   - {req}: {value}")
            print()
            
            # 2. MONITOREAR PROGRESO
            print("📊 Monitoreando progreso...")
            monitor_task_progress(task_id)
            
        else:
            print(f"❌ Error iniciando upgrade: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión: Verifica que el servidor Django esté ejecutándose")
    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")


def monitor_task_progress(task_id):
    """
    Monitorea el progreso de la tarea de upgrade
    """
    status_endpoint = f"{API_BASE_URL}/upgrade-so-huawei-switch/status/?task_id={task_id}"
    
    print("⏳ Esperando resultados...")
    print("   (Esto puede tomar varios minutos)")
    print()
    
    start_time = time.time()
    last_status = None
    
    while True:
        try:
            response = requests.get(status_endpoint)
            
            if response.status_code == 200:
                result = response.json()
                current_status = result['status']
                
                # Mostrar progreso solo si cambió
                if current_status != last_status:
                    print(f"🔄 Estado: {current_status.upper()}")
                    
                    if current_status == 'in_progress':
                        progress = result.get('progress', 0)
                        total = result.get('total', 100)
                        status_msg = result.get('status_message', 'Procesando...')
                        print(f"   📈 Progreso: {progress}/{total}")
                        print(f"   📝 Estado: {status_msg}")
                        
                    elif current_status == 'completed':
                        print("✅ Upgrade completado exitosamente!")
                        print()
                        print("📊 RESULTADOS FINALES:")
                        print("=" * 30)
                        
                        final_result = result['result']
                        if 'primary_switch' in final_result:
                            print(f"🎯 Switch principal: {final_result['primary_switch']}")
                            print(f"🖥️  Switches cliente: {len(final_result['client_switches'])}")
                            
                            if 'resource_check' in final_result:
                                resource = final_result['resource_check']
                                print(f"💾 Recursos verificados: {resource['message']}")
                            
                            print(f"📋 Mensaje: {final_result['message']}")
                            print(f"⏱️  Tiempo total: {time.time() - start_time:.1f} segundos")
                        
                        break
                        
                    elif current_status == 'failed':
                        print("❌ Upgrade falló!")
                        print(f"   Error: {result.get('error', 'Error desconocido')}")
                        break
                    
                    last_status = current_status
                
                time.sleep(5)  # Esperar 5 segundos antes de la siguiente consulta
                
            else:
                print(f"❌ Error consultando estado: {response.status_code}")
                break
                
        except requests.exceptions.ConnectionError:
            print("❌ Error de conexión durante monitoreo")
            break
        except Exception as e:
            print(f"❌ Error monitoreando progreso: {str(e)}")
            break


def simulate_network_topology():
    """
    Simula la topología de red para demostrar la selección del switch principal
    """
    print("🌐 SIMULACIÓN DE TOPOLOGÍA DE RED")
    print("=" * 40)
    
    # Simular switches con diferentes características
    switches = [
        {
            "ip": "192.168.1.10",
            "score": 120,
            "up_interfaces": 8,
            "free_space_mb": 250,
            "memory_usage": 65,
            "cpu_usage": 45
        },
        {
            "ip": "192.168.1.11", 
            "score": 95,
            "up_interfaces": 6,
            "free_space_mb": 180,
            "memory_usage": 75,
            "cpu_usage": 60
        },
        {
            "ip": "192.168.1.12",
            "score": 85,
            "up_interfaces": 5,
            "free_space_mb": 150,
            "memory_usage": 80,
            "cpu_usage": 70
        },
        {
            "ip": "192.168.1.13",
            "score": 70,
            "up_interfaces": 4,
            "free_space_mb": 120,
            "memory_usage": 85,
            "cpu_usage": 75
        }
    ]
    
    print("📊 Evaluación de switches:")
    print("-" * 40)
    
    for switch in switches:
        print(f"🔍 Switch {switch['ip']}:")
        print(f"   - Score: {switch['score']}")
        print(f"   - Interfaces UP: {switch['up_interfaces']}")
        print(f"   - Espacio libre: {switch['free_space_mb']}MB")
        print(f"   - Uso RAM: {switch['memory_usage']}%")
        print(f"   - Uso CPU: {switch['cpu_usage']}%")
        print()
    
    # Encontrar el mejor switch
    best_switch = max(switches, key=lambda x: x['score'])
    print(f"🏆 MEJOR SWITCH SELECCIONADO: {best_switch['ip']}")
    print(f"   - Score: {best_switch['score']}")
    print(f"   - Razón: Mejor conectividad y recursos disponibles")
    print()
    
    # Mostrar estrategia de distribución
    client_switches = [s for s in switches if s['ip'] != best_switch['ip']]
    print("📦 ESTRATEGIA DE DISTRIBUCIÓN:")
    print(f"   1. Descargar firmware en {best_switch['ip']} (servidor FTP local)")
    print(f"   2. Distribuir a {len(client_switches)} switches cliente:")
    
    for i, client in enumerate(client_switches, 1):
        print(f"      {i}. {client['ip']} (Score: {client['score']})")
    
    print()
    print("⚡ VENTAJAS DEL MÉTODO JERÁRQUICO:")
    print("   ✓ Reduce carga en servidor FTP externo")
    print("   ✓ Mejor velocidad de transferencia local")
    print("   ✓ Menor saturación de red")
    print("   ✓ Selección automática del mejor servidor")
    print("   ✓ Verificación de recursos antes del upgrade")


if __name__ == "__main__":
    print("🎯 DEMO: UPGRADE JERÁRQUICO DE SWITCHES HUAWEI")
    print("=" * 60)
    print()
    
    # Simular topología
    simulate_network_topology()
    print()
    
    # Preguntar si ejecutar la prueba real
    response = input("¿Ejecutar prueba real de upgrade? (y/N): ")
    
    if response.lower() in ['y', 'yes', 'sí', 'si']:
        print()
        test_hierarchical_upgrade()
    else:
        print("✅ Demo completado. Para ejecutar la prueba real:")
        print("   1. Asegúrate de que el servidor Django esté ejecutándose")
        print("   2. Modifica las IPs en el script para switches reales")
        print("   3. Ejecuta: python test_hierarchical_upgrade.py") 