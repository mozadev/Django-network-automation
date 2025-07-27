import pexpect
import os
from dotenv import load_dotenv
import re
from datetime import datetime
import time
from celery import shared_task
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# GLOBAL VARIABLES
TIME_SLEEP = 0.1

@shared_task(bind=True, time_limit=7200, soft_time_limit=6000)
def upgrade_switch_task(self, switch_data):
    """
    Tarea de Celery para upgrade de un switch individual
    """
    try:
        # Actualizar estado de la tarea
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 10,
                'total': 100,
                'status': 'Iniciando upgrade del switch'
            }
        )
        
        # Extraer datos del switch
        ip = switch_data['ip']
        user_tacacs = switch_data['user_tacacs']
        pass_tacacs = switch_data['pass_tacacs']
        so_upgrade = switch_data.get('so_upgrade')
        parche_upgrade = switch_data.get('parche_upgrade')
        download = switch_data['download']
        ip_ftp = switch_data['ip_ftp']
        pass_ftp = switch_data['pass_ftp']
        
        logger.info(f"Iniciando upgrade para switch {ip}")
        
        # Ejecutar upgrade del switch
        result = to_switch_optimized_improved(
            user_tacacs, pass_tacacs, ip, so_upgrade, 
            parche_upgrade, download, ip_ftp, pass_ftp
        )
        
        # Actualizar estado final
        self.update_state(
            state='SUCCESS',
            meta={
                'current': 100,
                'total': 100,
                'status': 'Upgrade completado exitosamente',
                'result': result
            }
        )
        
        return result
        
    except Exception as exc:
        logger.error(f"Error en upgrade del switch {ip}: {str(exc)}")
        self.update_state(
            state='FAILURE',
            meta={
                'current': 0,
                'total': 100,
                'status': f'Error: {str(exc)}'
            }
        )
        raise

@shared_task(bind=True, time_limit=7200, soft_time_limit=6000)
def upgrade_multiple_switches_task(self, switches_data):
    """
    Tarea de Celery para upgrade de múltiples switches (SECUENCIAL - NO PARALELO)
    ⚠️ ADVERTENCIA: Esta función procesa switches uno por uno, no en paralelo
    """
    try:
        # Actualizar estado inicial
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': len(switches_data),
                'status': 'Iniciando upgrade SECUENCIAL de switches'
            }
        )
        
        results = []
        total_switches = len(switches_data)
        
        for i, switch_data in enumerate(switches_data):
            # Actualizar progreso
            progress = int((i / total_switches) * 100)
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': progress,
                    'total': 100,
                    'status': f'Procesando switch {i+1} de {total_switches} (SECUENCIAL)'
                }
            )
            
            # Ejecutar upgrade del switch individual
            result = to_switch_optimized_improved(
                switch_data['user_tacacs'],
                switch_data['pass_tacacs'],
                switch_data['ip'],
                switch_data.get('so_upgrade'),
                switch_data.get('parche_upgrade'),
                switch_data['download'],
                switch_data['ip_ftp'],
                switch_data['pass_ftp']
            )
            
            results.append(result)
            
            # Pequeña pausa entre switches
            time.sleep(2)
        
        # Actualizar estado final
        self.update_state(
            state='SUCCESS',
            meta={
                'current': 100,
                'total': 100,
                'status': 'Upgrade SECUENCIAL de todos los switches completado',
                'results': results
            }
        )
        
        return results
        
    except Exception as exc:
        logger.error(f"Error en upgrade múltiple secuencial: {str(exc)}")
        self.update_state(
            state='FAILURE',
            meta={
                'current': 0,
                'total': 100,
                'status': f'Error: {str(exc)}'
            }
        )
        raise

@shared_task(bind=True, time_limit=7200, soft_time_limit=6000)
def upgrade_multiple_switches_parallel_task(self, switches_data):
    """
    Tarea de Celery para upgrade de múltiples switches EN PARALELO REAL
    ✅ Esta función procesa switches simultáneamente usando group()
    """
    try:
        # Actualizar estado inicial
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': len(switches_data),
                'status': 'Iniciando upgrade PARALELO de switches'
            }
        )
        
        # Crear grupo de tareas paralelas
        from celery import group
        
        # Crear tareas individuales para cada switch
        switch_tasks = []
        for switch_data in switches_data:
            task = upgrade_switch_task.delay(switch_data)
            switch_tasks.append(task)
        
        # Ejecutar todas las tareas en paralelo
        task_group = group(switch_tasks)
        results = task_group.get()  # Esperar que todas terminen
        
        # Actualizar estado final
        self.update_state(
            state='SUCCESS',
            meta={
                'current': 100,
                'total': 100,
                'status': 'Upgrade PARALELO de todos los switches completado',
                'results': results
            }
        )
        
        return results
        
    except Exception as exc:
        logger.error(f"Error en upgrade múltiple paralelo: {str(exc)}")
        self.update_state(
            state='FAILURE',
            meta={
                'current': 0,
                'total': 100,
                'status': f'Error: {str(exc)}'
            }
        )
        raise

@shared_task(bind=True, time_limit=7200, soft_time_limit=6000)
def upgrade_multiple_switches_chord_task(self, switches_data):
    """
    Tarea de Celery para upgrade de múltiples switches usando chord (paralelo con callback)
    ✅ Esta función procesa switches simultáneamente usando chord()
    """
    try:
        # Actualizar estado inicial
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': len(switches_data),
                'status': 'Iniciando upgrade paralelo con chord'
            }
        )
        
        # Crear tareas individuales para cada switch
        from celery import chord
        
        # Crear lista de tareas individuales
        switch_tasks = []
        for switch_data in switches_data:
            task = upgrade_switch_task.s(switch_data)  # .s() crea una firma de tarea
            switch_tasks.append(task)
        
        # Ejecutar con chord (paralelo + callback)
        chord_result = chord(switch_tasks)(collect_results.s())
        results = chord_result.get()  # Esperar que todas terminen
        
        # Actualizar estado final
        self.update_state(
            state='SUCCESS',
            meta={
                'current': 100,
                'total': 100,
                'status': 'Upgrade paralelo con chord completado',
                'results': results
            }
        )
        
        return results
        
    except Exception as exc:
        logger.error(f"Error en upgrade múltiple con chord: {str(exc)}")
        self.update_state(
            state='FAILURE',
            meta={
                'current': 0,
                'total': 100,
                'status': f'Error: {str(exc)}'
            }
        )
        raise

@shared_task
def collect_results(results):
    """
    Callback que se ejecuta cuando todas las tareas individuales terminan
    """
    logger.info(f"Todas las tareas de upgrade terminaron. Resultados: {len(results)} switches procesados")
    return results

def to_switch_optimized_improved(user_tacacs, pass_tacacs, ip, so_upgrade, parche_upgrade, download, ip_ftp, pass_ftp):
    """
    Versión mejorada que separa claramente IPs vs Stack
    """
    result = {}
    version = None
    vlanif199 = False
    FILE_SERVER = ip_ftp
    FTP_USER = os.getenv("FTP_USER") if pass_ftp == "N" else user_tacacs
    FTP_PASS = os.getenv("FTP_PASS") if pass_ftp == "N" else pass_tacacs
    interface_ip = None
    soSizeInFTPInMegas = None
    parcheSizeInFTPInMegas = None
    routersFTP = []
    soInMaster = False
    parcheInMaster = False

    try:
        logger.info(f"🔄 Iniciando upgrade para IP: {ip}")
        
        # Conexión DIRECTA al switch (sin router intermedio)
        child = pexpect.spawn(f"telnet {ip}", timeout=60)
        child.expect([r"[Uu]sername:", r"\]\$"])
        
        if child.after.decode().strip() == r"\]\$":
            logger.warning(f"❌ Switch {ip} sin gestión")
            return {"msg": rf"SWITCH IPv4OfStack {ip} sin gestión"}
        
        # Autenticación
        child.send(user_tacacs)
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect("[Pp]assword:")
        child.send(pass_tacacs)
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\s<[\w\-.]+>")

        # Configuración inicial
        child.send(f"screen-length 0 temporary")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\s<[\w\-.]+>")

        # Obtener información del stack (módulos físicos del MISMO switch)
        child.send(f"display stack")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\s<[\w\-.]+>")
        output_stack = child.before.decode("utf-8")
        output_stack_pattern = re.findall(r'\s(\d+) +([a-zA-Z]+) +(\w+-\w+-\w+) ', output_stack)
        result_stack = []
        
        if len(output_stack_pattern) > 0:
            for i in output_stack_pattern:
                result_stack.append({"MemberID": int(i[0]), "Role": i[1], "MAC": i[2]})
            logger.info(f"📦 Stack detectado en {ip}: {len(result_stack)} módulos")
        else:
            logger.info(f"📦 Switch {ip} sin stack (módulo único)")

        # Obtener versión del switch
        child.send(f"display version")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\s<[\w\-.]+>")
        output_version = child.before.decode("utf-8")
        output_version_pattern = re.search(r'\sVersion (?P<version1>[\w\.]+) \((?P<version2>[\w ]+)\)', output_version)
        
        if output_version_pattern:
            version = {
                "number": output_version_pattern.group("version1"), 
                "detail": output_version_pattern.group("version2")
            }
            logger.info(f"📋 Versión actual: {version['number']}")

        # Obtener configuración de startup
        child.send(f"display startup")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\s<[\w\-.]+>")
        output_startup = child.before.decode("utf-8")
        output_startup_stack_pattern = re.findall(r'\n(\w+[\w ]*):', output_startup)
        output_startup_software_pattern = re.findall(r' Startup system software: +(\S+)', output_startup)
        output_startup_patch_pattern = re.findall(r' Startup patch package: +(\S+)', output_startup)
        
        result_startup = []
        for item in zip(output_startup_stack_pattern, output_startup_software_pattern, output_startup_patch_pattern):
            result_startup.append({"stack": item[0], "software": item[1], "patch": item[2]})

        # Verificar interfaz Vlanif199 para conectividad FTP
        child.send(f"display ip interface brief")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\s<[\w\-.]+>")
        output_interfaces = child.before.decode("utf-8")
        output_interfaces_pattern = re.search(r"\bVlanif199\b", output_interfaces)
        
        if output_interfaces_pattern:
            vlanif199 = True
            logger.info(f"🌐 Vlanif199 encontrada en {ip}")

            child.send(f"display current-configuration interface Vlanif199")
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"\s<[\w\-.]+>")
            output_interfaceVlanif199 = child.before.decode("utf-8")
            output_interfaceVlanif199_pattern = re.findall(r'ip address (\d+\.\d+\.\d+\.\d+) ', output_interfaceVlanif199)
            routersFTP = routersFTPFromIPv4(output_interfaceVlanif199_pattern, FILE_SERVER)
            
            # Probar conectividad FTP
            for ftp_item in routersFTP:
                child.send(f"ping {ftp_item}")
                time.sleep(TIME_SLEEP)
                child.sendline("")
                child.expect(r"\s<[\w\-.]+>")
                output_ping = child.before.decode("utf-8")
                output_ping_pattern = re.findall(r'round-trip min\/avg\/max ', output_ping)
                if output_ping_pattern:
                    interface_ip = ftp_item
                    logger.info(f"✅ Conectividad FTP establecida: {interface_ip}")
                    break
        
        # Procesar archivos en FTP si hay conectividad
        if interface_ip:
            child.send(f"ftp {interface_ip}")
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"\)\):")
            child.send(FTP_USER)
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"[Pp]assword:")
            child.send(FTP_PASS)
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"\n\[ftp\]")

            child.send(r"dir")
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"\n\[ftp\]")
            output_dirInFTP = child.before.decode("utf-8")
            output_soInFTP_pattern = re.search(rf' (\d+) +\S+ +\S+ +\S+ +\b{so_upgrade}\b', output_dirInFTP)
            output_parcheInFTP_pattern = re.search(rf' (\d+) +\S+ +\S+ +\S+ +\b{parche_upgrade}\b', output_dirInFTP)
            
            if output_soInFTP_pattern:
                soSizeInFTPInMegas = round(int(output_soInFTP_pattern.group(1)) / (1024 * 1024), 2)
                logger.info(f"📁 SO en FTP: {so_upgrade} ({soSizeInFTPInMegas} MB)")
            if output_parcheInFTP_pattern:
                parcheSizeInFTPInMegas = round(int(output_parcheInFTP_pattern.group(1)) / (1024 * 1024), 2)
                logger.info(f"📁 Parche en FTP: {parche_upgrade} ({parcheSizeInFTPInMegas} MB)")

            child.send(r"quit")
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"\s<[\w\-.]+>")

        # Procesar cada módulo del stack (del MISMO switch)
        logger.info(f"🔍 Analizando módulos del stack en {ip}")
        for stack in result_stack: 
            member_id = stack["MemberID"]
            role = stack["Role"]
            logger.info(f"  📦 Módulo {member_id} ({role})")
            
            child.send("dir {stack}#flash:/".format(stack=member_id))
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"\s<[\w\-.]+>")

            output_dirInStack = child.before.decode("utf-8")
            output_soInStack_pattern = re.search(rf'\b{so_upgrade}\b', output_dirInStack)
            output_parcheInStack_pattern = re.search(rf'\b{parche_upgrade}\b', output_dirInStack)
            output_sizeInStack_pattern = re.search(r' KB total \((\S+) KB free\)', output_dirInStack)
            listSOInStack_pattern = re.findall(r' (\S+) +\S+ +\S+ +\S+ +\S+ +(\S+\.cc)\s', output_dirInStack)
            listParcheInStack_pattern = re.findall(r' (\S+) +\S+ +\S+ +\S+ +\S+ +(\S+\.PAT|\S+\.pat)\s', output_dirInStack)
            
            if output_soInStack_pattern:
                stack["soInStack"] = True
                if stack["Role"] == "Master":
                    soInMaster = True
                logger.info(f"    ✅ SO encontrado en módulo {member_id}")
            else:
                stack["soInStack"] = False
                logger.info(f"    ❌ SO NO encontrado en módulo {member_id}")
                
            if output_parcheInStack_pattern:
                stack["parcheInStack"] = True
                if stack["Role"] == "Master":
                    parcheInMaster = True
                logger.info(f"    ✅ Parche encontrado en módulo {member_id}")
            else:
                stack["parcheInStack"] = False
                logger.info(f"    ❌ Parche NO encontrado en módulo {member_id}")
                
            if output_sizeInStack_pattern:
                sizeFreeInStack = output_sizeInStack_pattern.group(1)
                stack["sizeFreeInStack"] = round(int(re.sub(",", "", sizeFreeInStack)) / 1024, 2)
                logger.info(f"    💾 Espacio libre: {stack['sizeFreeInStack']} MB")
            else:
                stack["sizeFreeInStack"] = None

            listSOInStack = []
            listParcheInStack = []
            stack["soIsCompletedInStack"] = False
            stack["parcheIsCompletedInStack"] = False

            for so_item in listSOInStack_pattern:
                soInMegas = round(int(re.sub(",", "", so_item[0])) / (1024 * 1024), 2)
                listSOInStack.append({"sizeSOInMB": soInMegas, "nameSO": so_item[1]})
                if so_item[1] == so_upgrade and soInMegas == soSizeInFTPInMegas:
                    stack["soIsCompletedInStack"] = True
                    
            for parche_item in listParcheInStack_pattern:
                parcheInMegas = round(int(re.sub(",", "", parche_item[0])) / (1024 * 1024), 2)
                listParcheInStack.append({"sizeParcheInMB": parcheInMegas, "nameParche": parche_item[1]})
                if parche_item[1] == parche_upgrade and parcheInMegas == parcheSizeInFTPInMegas:
                    stack["parcheIsCompletedInStack"] = True

            stack["listSOInStack"] = listSOInStack
            stack["listParcheInStack"] = listParcheInStack

            stack["sufficientCapacityInStack"] = calculateSpaceSuffient(soSizeInFTPInMegas, parcheSizeInFTPInMegas, stack["sizeFreeInStack"])

        # Procesar upgrade (solo Master descarga, Slaves copian del Master)
        result_stack = sorted(result_stack, key=master_isFirst)
        child.timeout = 7200
        
        logger.info(f"🚀 Iniciando upgrade en {ip}")
        for stack in result_stack:
            member_id = stack["MemberID"]
            role = stack["Role"]
            
            if stack["Role"] == "Master":
                # SOLO EL MASTER DESCARGA DEL FTP
                logger.info(f"  👑 Master {member_id}: Descargando del FTP")
                if stack["sufficientCapacityInStack"]:
                    child.send(f"ftp {interface_ip}")
                    time.sleep(TIME_SLEEP)
                    child.sendline("")
                    child.expect(r"\)\):")
                    child.send(FTP_USER)
                    time.sleep(TIME_SLEEP)
                    child.sendline("")
                    child.expect(r"[Pp]assword:")
                    child.send(FTP_PASS)
                    time.sleep(TIME_SLEEP)
                    child.sendline("")
                    child.expect(r"\n\[ftp\]")

                    if not stack["soInStack"] and download == "Y" and so_upgrade:
                        logger.info(f"    📥 Descargando SO: {so_upgrade}")
                        child.send(rf"get {so_upgrade}")
                        time.sleep(TIME_SLEEP)
                        child.sendline("")
                        child.expect(r"\n\[ftp\]")
                        soInMaster = True
                        
                    if not stack["parcheInStack"] and download == "Y" and parche_upgrade:
                        logger.info(f"    📥 Descargando parche: {parche_upgrade}")
                        child.send(rf"get {parche_upgrade}")
                        time.sleep(TIME_SLEEP)
                        child.sendline("")
                        child.expect(r"\n\[ftp\]")
                        parcheInMaster = True

                    child.send(r"quit")
                    time.sleep(TIME_SLEEP)
                    child.sendline("")
                    child.expect(r"\s<[\w\-.]+>")
            else:
                # LOS SLAVES COPIAN DEL MASTER (del mismo switch)
                logger.info(f"  📋 Slave {member_id}: Copiando del Master")
                if stack["sufficientCapacityInStack"]:
                    if not stack["soInStack"] and soInMaster and download == "Y" and so_upgrade:
                        logger.info(f"    📋 Copiando SO al módulo {member_id}")
                        child.send(f"copy {so_upgrade} {member_id}#flash:")
                        time.sleep(TIME_SLEEP)
                        child.sendline("")
                        child.expect(r"\[Y\/N\]:")
                        child.send(f"Y")
                        time.sleep(TIME_SLEEP)
                        child.sendline("")
                        child.expect(r"\s<[\w\-.]+>")

                    if not stack["parcheInStack"] and parcheInMaster and download == "Y" and parche_upgrade:
                        logger.info(f"    📋 Copiando parche al módulo {member_id}")
                        child.send(f"copy {parche_upgrade} {member_id}#flash:")
                        time.sleep(TIME_SLEEP)
                        child.sendline("")
                        child.expect(r"\[Y\/N\]:")
                        child.send(f"Y")
                        time.sleep(TIME_SLEEP)
                        child.sendline("")
                        child.expect(r"\s<[\w\-.]+>")
                        
        child.timeout = 60

        child.send(f"quit")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\]\$")

        # Construir resultado
        result["IPv4OfStack"] = ip
        result["IPv4OfFTPServer"] = ip_ftp
        result["passIsEqualToFTPServer"] = pass_ftp
        result["newSOSearchedInFTPServer"] = so_upgrade
        result["newParcheSearchedInFTPServer"] = parche_upgrade
        result["downloadFiles"] = download
        result["countStacks"] = len(result_stack)
        result["versionSwitchNow"] = version
        result["versionByStackNow"] = result_startup
        result["Vlanif199_isFound"] = vlanif199
        result["PingToFTP"] = f"ping {interface_ip}"
        result["soSizeInFTPInMB"] = soSizeInFTPInMegas
        result["parcheSizeInFTPInMB"] = parcheSizeInFTPInMegas
        result["soInMaster"] = soInMaster
        result["parcheInMaster"] = parcheInMaster
        result["stacks"] = result_stack
        
        logger.info(f"✅ Upgrade completado para {ip}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error en to_switch_optimized para {ip}: {str(e)}")
        return {"error": str(e), "ip": ip}

# Funciones auxiliares (importadas del utils.py original)
def routersFTPFromIPv4(list_ip, ftp_server):
    result = [f"-a {i} {ftp_server}" for i in list_ip]
    result.append(f"{ftp_server}")
    result.reverse()
    return result

def master_isFirst(elemento):
    return 0 if elemento["Role"] == "Master" else 1

def calculateSpaceSuffient(soSizeInFTPInMegas, parcheSizeInFTPInMegas, sizeFreeInStack):
    sufficientCapacity = False
    if not soSizeInFTPInMegas: soSizeInFTPInMegas = 0.0
    if not parcheSizeInFTPInMegas: parcheSizeInFTPInMegas = 0.0
    sufficientCapacity = sizeFreeInStack - (soSizeInFTPInMegas + parcheSizeInFTPInMegas)

    if sufficientCapacity > 0:
        return True
    else:
        return False

def detect_stack_membership(ip_list):
    """
    Detecta si las IPs pertenecen al mismo stack físico
    """
    stack_groups = []
    processed_ips = set()
    
    for ip in ip_list:
        if ip in processed_ips:
            continue
            
        try:
            # Conectar al switch
            child = pexpect.spawn(f"telnet {ip}", timeout=30)
            child.expect([r"[Uu]sername:", r"\]\$"])
            
            if child.after.decode().strip() == r"\]\$":
                continue
                
            # Autenticación básica (asumiendo credenciales por defecto)
            child.send("admin")
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect("[Pp]assword:")
            child.send("Admin123")
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"\s<[\w\-.]+>")
            
            # Obtener información del stack
            child.send("display stack")
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"\s<[\w\-.]+>")
            output_stack = child.before.decode("utf-8")
            
            # Buscar IPs de otros miembros del stack
            stack_members = []
            stack_members.append(ip)
            
            # Buscar IPs de otros switches en el stack
            child.send("display ip interface brief")
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"\s<[\w\-.]+>")
            output_interfaces = child.before.decode("utf-8")
            
            # Extraer IPs de interfaces
            ip_pattern = re.findall(r'(\d+\.\d+\.\d+\.\d+)', output_interfaces)
            for found_ip in ip_pattern:
                if found_ip in ip_list and found_ip != ip:
                    stack_members.append(found_ip)
                    processed_ips.add(found_ip)
            
            if len(stack_members) > 1:
                stack_groups.append({
                    'master_ip': ip,
                    'member_ips': stack_members,
                    'total_members': len(stack_members)
                })
                logger.info(f"🔍 Stack detectado: {ip} es master de {len(stack_members)} switches")
            else:
                # Switch individual
                stack_groups.append({
                    'master_ip': ip,
                    'member_ips': [ip],
                    'total_members': 1
                })
                logger.info(f"🔍 Switch individual detectado: {ip}")
            
            child.send("quit")
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.close()
            
        except Exception as e:
            logger.error(f"❌ Error detectando stack para {ip}: {str(e)}")
            # Asumir switch individual
            stack_groups.append({
                'master_ip': ip,
                'member_ips': [ip],
                'total_members': 1
            })
        
        processed_ips.add(ip)
    
    return stack_groups

def detect_network_topology(ip_list):
    """
    Detecta la topología de red: Stack vs Switches Conectados
    """
    topology_info = {
        'stacks': [],
        'connected_switches': [],
        'individual_switches': []
    }
    
    # Primero detectar stacks
    stack_groups = detect_stack_membership(ip_list)
    
    for stack in stack_groups:
        if stack['total_members'] > 1:
            topology_info['stacks'].append(stack)
        else:
            # Verificar si está conectado a otros switches
            switch_ip = stack['master_ip']
            connected_switches = detect_connected_switches(switch_ip, ip_list)
            
            if connected_switches:
                topology_info['connected_switches'].append({
                    'server_ip': switch_ip,
                    'client_ips': connected_switches,
                    'total_switches': len(connected_switches) + 1
                })
            else:
                topology_info['individual_switches'].append(switch_ip)
    
    return topology_info

def detect_connected_switches(switch_ip, all_ips):
    """
    Detecta switches conectados (no en stack) que pueden usar este como server
    """
    connected_switches = []
    
    try:
        # Conectar al switch
        child = pexpect.spawn(f"telnet {switch_ip}", timeout=30)
        child.expect([r"[Uu]sername:", r"\]\$"])
        
        if child.after.decode().strip() == r"\]\$":
            return connected_switches
            
        # Autenticación
        child.send("admin")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect("[Pp]assword:")
        child.send("Admin123")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\s<[\w\-.]+>")
        
        # Verificar si tiene firmware que puede compartir
        child.send("dir")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\s<[\w\-.]+>")
        output_dir = child.before.decode("utf-8")
        
        # Buscar archivos de firmware
        firmware_files = []
        if "Software" in output_dir or ".cc" in output_dir or ".pat" in output_dir:
            firmware_files = re.findall(r'(\S+\.(?:cc|pat|bin))', output_dir)
        
        if firmware_files:
            logger.info(f"🔍 Switch {switch_ip} tiene firmware: {firmware_files}")
            
            # Verificar conectividad con otros switches
            for other_ip in all_ips:
                if other_ip != switch_ip:
                    # Probar ping
                    child.send(f"ping {other_ip}")
                    time.sleep(TIME_SLEEP)
                    child.sendline("")
                    child.expect(r"\s<[\w\-.]+>")
                    output_ping = child.before.decode("utf-8")
                    
                    if "round-trip min/avg/max" in output_ping:
                        connected_switches.append(other_ip)
                        logger.info(f"✅ Switch {other_ip} conectado a {switch_ip}")
        
        child.send("quit")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.close()
        
    except Exception as e:
        logger.error(f"❌ Error detectando switches conectados para {switch_ip}: {str(e)}")
    
    return connected_switches

def upgrade_stack_optimized(stack_info, user_tacacs, pass_tacacs, so_upgrade, parche_upgrade, download, ip_ftp, pass_ftp):
    """
    Upgrade optimizado para un stack completo
    """
    master_ip = stack_info['master_ip']
    member_ips = stack_info['member_ips']
    
    logger.info(f"🚀 Iniciando upgrade optimizado para stack: {master_ip}")
    logger.info(f"📦 Miembros del stack: {member_ips}")
    
    try:
        # Conectar al MASTER del stack
        child = pexpect.spawn(f"telnet {master_ip}", timeout=60)
        child.expect([r"[Uu]sername:", r"\]\$"])
        
        if child.after.decode().strip() == r"\]\$":
            return {"error": f"Switch {master_ip} sin gestión"}
        
        # Autenticación
        child.send(user_tacacs)
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect("[Pp]assword:")
        child.send(pass_tacacs)
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\s<[\w\-.]+>")
        
        # Configuración inicial
        child.send("screen-length 0 temporary")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\s<[\w\-.]+>")
        
        # Verificar conectividad FTP
        child.send("display ip interface brief")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\s<[\w\-.]+>")
        output_interfaces = child.before.decode("utf-8")
        
        # Buscar Vlanif199 para FTP
        vlanif199_pattern = re.search(r"\bVlanif199\b", output_interfaces)
        interface_ip = None
        
        if vlanif199_pattern:
            child.send("display current-configuration interface Vlanif199")
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"\s<[\w\-.]+>")
            output_vlanif199 = child.before.decode("utf-8")
            ip_pattern = re.findall(r'ip address (\d+\.\d+\.\d+\.\d+) ', output_vlanif199)
            
            if ip_pattern:
                # Probar conectividad FTP
                for ip in ip_pattern:
                    child.send(f"ping {ip_ftp}")
                    time.sleep(TIME_SLEEP)
                    child.sendline("")
                    child.expect(r"\s<[\w\-.]+>")
                    output_ping = child.before.decode("utf-8")
                    if "round-trip min/avg/max" in output_ping:
                        interface_ip = ip_ftp
                        break
        
        # Descargar firmware solo en el MASTER si hay conectividad
        if interface_ip and download == "Y":
            logger.info(f"📥 Descargando firmware en MASTER {master_ip}")
            
            child.send(f"ftp {interface_ip}")
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"\)\):")
            child.send(user_tacacs)
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"[Pp]assword:")
            child.send(pass_tacacs)
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"\n\[ftp\]")
            
            if so_upgrade:
                child.send(f"get {so_upgrade}")
                time.sleep(TIME_SLEEP)
                child.sendline("")
                child.expect(r"\n\[ftp\]")
                logger.info(f"✅ SO descargado: {so_upgrade}")
            
            if parche_upgrade:
                child.send(f"get {parche_upgrade}")
                time.sleep(TIME_SLEEP)
                child.sendline("")
                child.expect(r"\n\[ftp\]")
                logger.info(f"✅ Parche descargado: {parche_upgrade}")
            
            child.send("quit")
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"\s<[\w\-.]+>")
        
        # Distribuir firmware a los SLAVES
        for slave_ip in member_ips[1:]:  # Excluir el master
            logger.info(f"📋 Distribuyendo firmware a SLAVE {slave_ip}")
            
            # Copiar archivos del master al slave
            if so_upgrade:
                child.send(f"copy {so_upgrade} {slave_ip}#flash:")
                time.sleep(TIME_SLEEP)
                child.sendline("")
                child.expect(r"\[Y\/N\]:")
                child.send("Y")
                time.sleep(TIME_SLEEP)
                child.sendline("")
                child.expect(r"\s<[\w\-.]+>")
                logger.info(f"✅ SO copiado a {slave_ip}")
            
            if parche_upgrade:
                child.send(f"copy {parche_upgrade} {slave_ip}#flash:")
                time.sleep(TIME_SLEEP)
                child.sendline("")
                child.expect(r"\[Y\/N\]:")
                child.send("Y")
                time.sleep(TIME_SLEEP)
                child.sendline("")
                child.expect(r"\s<[\w\-.]+>")
                logger.info(f"✅ Parche copiado a {slave_ip}")
        
        child.send("quit")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.close()
        
        # Resultado del stack
        result = {
            "stack_master": master_ip,
            "stack_members": member_ips,
            "total_members": len(member_ips),
            "so_upgrade": so_upgrade,
            "parche_upgrade": parche_upgrade,
            "status": "completed",
            "message": f"Stack upgrade completado: {len(member_ips)} switches"
        }
        
        logger.info(f"✅ Upgrade de stack completado: {master_ip}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error en upgrade de stack {master_ip}: {str(e)}")
        return {"error": str(e), "stack_master": master_ip} 

def get_current_config(switch_ip):
    """Obtener configuración actual del switch"""
    try:
        child = pexpect.spawn(f"telnet {switch_ip}", timeout=60)
        child.expect([r"[Uu]sername:", r"\]\$"])
        
        if child.after.decode().strip() == r"\]\$":
            return None  # Switch sin gestión
        
        # Asumir credenciales por defecto o usar variables de entorno
        child.send("admin")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect("[Pp]assword:")
        child.send("Admin123")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\s<[\w\-.]+>")

        # Obtener configuración actual
        child.send("display current-configuration")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\s<[\w\-.]+>")
        config = child.before.decode("utf-8")
        
        child.send("quit")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.close()
        
        return config
        
    except Exception as e:
        logger.error(f"Error obteniendo configuración de {switch_ip}: {str(e)}")
        return None

def verify_switch_health(switch_ip):
    """Verificar que el switch está operativo después del upgrade"""
    try:
        # Intentar conexión
        child = pexpect.spawn(f"telnet {switch_ip}", timeout=30)
        child.expect([r"[Uu]sername:", r"\]\$", pexpect.TIMEOUT])
        
        if child.expect == 2:  # TIMEOUT
            return False
        
        # Verificar que responde a comandos básicos
        child.send("display version")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\s<[\w\-.]+>")
        
        # Verificar interfaces
        child.send("display interface brief")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\s<[\w\-.]+>")
        output = child.before.decode("utf-8")
        
        # Verificar que al menos una interfaz está up
        if "up" in output and "down" not in output:
            return True
        
        child.send("quit")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.close()
        
        return False
        
    except Exception as e:
        logger.error(f"Error verificando salud del switch {switch_ip}: {str(e)}")
        return False

def restore_config(switch_ip, backup_config):
    """Restaurar configuración de backup"""
    try:
        if not backup_config:
            logger.warning(f"No hay configuración de backup para {switch_ip}")
            return False
        
        child = pexpect.spawn(f"telnet {switch_ip}", timeout=60)
        child.expect([r"[Uu]sername:", r"\]\$"])
        
        if child.after.decode().strip() == r"\]\$":
            return False
        
        child.send("admin")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect("[Pp]assword:")
        child.send("Admin123")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\s<[\w\-.]+>")

        # Entrar en modo sistema
        child.send("system-view")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\[Switch\]")

        # Aplicar configuración línea por línea
        config_lines = backup_config.split('\n')
        for line in config_lines:
            line = line.strip()
            if line and not line.startswith('#'):
                child.send(line)
                time.sleep(TIME_SLEEP)
                child.sendline("")
                child.expect(r"\[Switch\]")
        
        # Guardar configuración
        child.send("quit")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\s<[\w\-.]+>")
        
        child.send("save")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\[Y\/N\]:")
        child.send("Y")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\s<[\w\-.]+>")
        
        child.send("quit")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.close()
        
        logger.info(f"Configuración restaurada exitosamente en {switch_ip}")
        return True
        
    except Exception as e:
        logger.error(f"Error restaurando configuración en {switch_ip}: {str(e)}")
        return False

def apply_upgrade_with_rollback(switch_ip, firmware_file, user_tacacs, pass_tacacs):
    """Aplicar upgrade con rollback automático en caso de fallo"""
    backup_config = None
    
    try:
        logger.info(f"Iniciando upgrade con rollback para {switch_ip}")
        
        # 1. Backup de configuración actual
        logger.info(f"Creando backup de configuración para {switch_ip}")
        backup_config = get_current_config(switch_ip)
        
        if not backup_config:
            logger.warning(f"No se pudo obtener backup de configuración para {switch_ip}")
            # Continuar sin backup (riesgoso pero posible)
        
        # 2. Aplicar upgrade
        logger.info(f"Aplicando firmware {firmware_file} en {switch_ip}")
        
        # Usar la función existente de upgrade
        result = to_switch_optimized_improved(
            user_tacacs, pass_tacacs, switch_ip, 
            firmware_file, None, "Y", "192.168.1.100", "Y"
        )
        
        if "error" in result:
            raise Exception(f"Error en upgrade: {result['error']}")
        
        # 3. Verificar que el switch responde
        logger.info(f"Verificando salud del switch {switch_ip} después del upgrade")
        time.sleep(30)  # Esperar a que el switch se estabilice
        
        if not verify_switch_health(switch_ip):
            logger.error(f"Switch {switch_ip} no responde después del upgrade")
            
            # 4. Rollback automático
            if backup_config:
                logger.info(f"Ejecutando rollback automático para {switch_ip}")
                if restore_config(switch_ip, backup_config):
                    raise Exception("Upgrade falló, rollback ejecutado exitosamente")
                else:
                    raise Exception("Upgrade falló y rollback también falló")
            else:
                raise Exception("Upgrade falló y no hay backup para rollback")
        
        logger.info(f"Upgrade completado exitosamente para {switch_ip}")
        return {
            "status": "success",
            "switch_ip": switch_ip,
            "firmware": firmware_file,
            "backup_created": backup_config is not None
        }
        
    except Exception as e:
        logger.error(f"Error en upgrade con rollback para {switch_ip}: {str(e)}")
        
        # Rollback en caso de error
        if backup_config:
            logger.info(f"Intentando rollback de emergencia para {switch_ip}")
            try:
                restore_config(switch_ip, backup_config)
                logger.info(f"Rollback de emergencia completado para {switch_ip}")
            except Exception as rollback_error:
                logger.error(f"Rollback de emergencia falló para {switch_ip}: {str(rollback_error)}")
        
        return {
            "status": "failed",
            "switch_ip": switch_ip,
            "error": str(e),
            "backup_available": backup_config is not None
        }

@shared_task(bind=True, time_limit=7200, soft_time_limit=6000)
def upgrade_with_rollback_task(self, upgrade_data):
    """
    Tarea de Celery para upgrade con rollback automático
    """
    try:
        # Actualizar estado de la tarea
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 10,
                'total': 100,
                'status': 'Iniciando upgrade con rollback'
            }
        )
        
        # Extraer datos
        switch_ip = upgrade_data['switch_ip']
        firmware_file = upgrade_data['firmware_file']
        user_tacacs = upgrade_data['user_tacacs']
        pass_tacacs = upgrade_data['pass_tacacs']
        
        logger.info(f"Iniciando upgrade con rollback para switch {switch_ip}")
        
        # Aplicar upgrade con rollback
        result = apply_upgrade_with_rollback(
            switch_ip, firmware_file, user_tacacs, pass_tacacs
        )
        
        # Actualizar estado final
        if result['status'] == 'success':
            self.update_state(
                state='SUCCESS',
                meta={
                    'current': 100,
                    'total': 100,
                    'status': 'Upgrade con rollback completado exitosamente',
                    'result': result
                }
            )
        else:
            self.update_state(
                state='FAILURE',
                meta={
                    'current': 0,
                    'total': 100,
                    'status': f'Upgrade falló: {result["error"]}',
                    'result': result
                }
            )
        
        return result
        
    except Exception as exc:
        logger.error(f"Error en upgrade con rollback: {str(exc)}")
        self.update_state(
            state='FAILURE',
            meta={
                'current': 0,
                'total': 100,
                'status': f'Error: {str(exc)}'
            }
        )
        raise 

def upgrade_network_optimized(topology_info, user_tacacs, pass_tacacs, so_upgrade, parche_upgrade, download, ip_ftp, pass_ftp):
    """
    Upgrade optimizado para toda la red
    """
    results = []
    
    # 1. Procesar stacks
    for stack in topology_info['stacks']:
        result = upgrade_stack_optimized(stack, user_tacacs, pass_tacacs, so_upgrade, parche_upgrade, download, ip_ftp, pass_ftp)
        results.append(result)
    
    # 2. Procesar switches conectados (server-client)
    for connected_group in topology_info['connected_switches']:
        result = upgrade_server_client_group_sequential(connected_group, user_tacacs, pass_tacacs, so_upgrade, parche_upgrade, download, ip_ftp, pass_ftp)
        results.append(result)
    
    # 3. Procesar switches individuales
    for individual_ip in topology_info['individual_switches']:
        result = to_switch_optimized_improved(user_tacacs, pass_tacacs, individual_ip, so_upgrade, parche_upgrade, download, ip_ftp, pass_ftp)
        results.append(result)
    
    return results

def upgrade_server_client_group(connected_group, user_tacacs, pass_tacacs, so_upgrade, parche_upgrade, download, ip_ftp, pass_ftp):
    """
    Upgrade optimizado para grupo server-client
    """
    server_ip = connected_group['server_ip']
    client_ips = connected_group['client_ips']
    
    logger.info(f"🚀 Iniciando upgrade server-client: {server_ip} -> {client_ips}")
    
    try:
        # 1. Descargar firmware en el SERVER
        server_result = to_switch_optimized_improved(user_tacacs, pass_tacacs, server_ip, so_upgrade, parche_upgrade, download, ip_ftp, pass_ftp)
        
        if "error" in server_result:
            return server_result
        
        # 2. Distribuir a los CLIENTES
        client_results = []
        for client_ip in client_ips:
            client_result = copy_from_server_to_client(server_ip, client_ip, user_tacacs, pass_tacacs, so_upgrade, parche_upgrade)
            client_results.append(client_result)
        
        # Resultado del grupo
        result = {
            "server_ip": server_ip,
            "client_ips": client_ips,
            "server_result": server_result,
            "client_results": client_results,
            "total_switches": len(client_ips) + 1,
            "status": "completed",
            "message": f"Server-client upgrade completado: 1 server + {len(client_ips)} clientes"
        }
        
        logger.info(f"✅ Server-client upgrade completado: {server_ip}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error en server-client upgrade {server_ip}: {str(e)}")
        return {"error": str(e), "server_ip": server_ip}

def copy_from_server_to_client(server_ip, client_ip, user_tacacs, pass_tacacs, so_upgrade, parche_upgrade):
    """
    Copia firmware del server al cliente de forma secuencial
    """
    try:
        # Conectar al CLIENTE
        child = pexpect.spawn(f"telnet {client_ip}", timeout=60)
        child.expect([r"[Uu]sername:", r"\]\$"])
        
        if child.after.decode().strip() == r"\]\$":
            return {"error": f"Switch {client_ip} sin gestión"}
        
        # Autenticación
        child.send(user_tacacs)
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect("[Pp]assword:")
        child.send(pass_tacacs)
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\s<[\w\-.]+>")
        
        # Copiar archivos del server SECUENCIALMENTE
        if so_upgrade:
            logger.info(f"📋 Copiando SO de {server_ip} a {client_ip} (secuencial)")
            child.send(f"copy {so_upgrade} {server_ip}#flash:")
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"\[Y\/N\]:")
            child.send("Y")
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"\s<[\w\-.]+>")
            logger.info(f"✅ SO copiado de {server_ip} a {client_ip}")
            
            # DELAY para no saturar la red
            time.sleep(5)  # 5 segundos entre copias
        
        if parche_upgrade:
            logger.info(f"📋 Copiando parche de {server_ip} a {client_ip} (secuencial)")
            child.send(f"copy {parche_upgrade} {server_ip}#flash:")
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"\[Y\/N\]:")
            child.send("Y")
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"\s<[\w\-.]+>")
            logger.info(f"✅ Parche copiado de {server_ip} a {client_ip}")
            
            # DELAY para no saturar la red
            time.sleep(5)  # 5 segundos entre copias
        
        child.send("quit")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.close()
        
        return {
            "client_ip": client_ip,
            "server_ip": server_ip,
            "status": "completed",
            "message": f"Firmware copiado de {server_ip} (secuencial)"
        }
        
    except Exception as e:
        logger.error(f"❌ Error copiando de {server_ip} a {client_ip}: {str(e)}")
        return {"error": str(e), "client_ip": client_ip}

def upgrade_server_client_group_sequential(connected_group, user_tacacs, pass_tacacs, so_upgrade, parche_upgrade, download, ip_ftp, pass_ftp):
    """
    Upgrade optimizado para grupo server-client con copiado SECUENCIAL
    """
    server_ip = connected_group['server_ip']
    client_ips = connected_group['client_ips']
    
    logger.info(f"🚀 Iniciando upgrade server-client SECUENCIAL: {server_ip} -> {client_ips}")
    logger.info(f"⏱️ Copiado secuencial para evitar saturación de red")
    
    try:
        # 1. Descargar firmware en el SERVER
        server_result = to_switch_optimized_improved(user_tacacs, pass_tacacs, server_ip, so_upgrade, parche_upgrade, download, ip_ftp, pass_ftp)
        
        if "error" in server_result:
            return server_result
        
        # 2. Distribuir a los CLIENTES SECUENCIALMENTE
        client_results = []
        for i, client_ip in enumerate(client_ips):
            logger.info(f"📋 Procesando cliente {i+1}/{len(client_ips)}: {client_ip}")
            
            client_result = copy_from_server_to_client(server_ip, client_ip, user_tacacs, pass_tacacs, so_upgrade, parche_upgrade)
            client_results.append(client_result)
            
            # DELAY entre clientes para no saturar la red
            if i < len(client_ips) - 1:  # No delay después del último
                logger.info(f"⏳ Esperando 10 segundos antes del siguiente cliente...")
                time.sleep(10)  # 10 segundos entre clientes
        
        # Resultado del grupo
        result = {
            "server_ip": server_ip,
            "client_ips": client_ips,
            "server_result": server_result,
            "client_results": client_results,
            "total_switches": len(client_ips) + 1,
            "status": "completed",
            "message": f"Server-client upgrade completado SECUENCIAL: 1 server + {len(client_ips)} clientes",
            "method": "sequential",
            "total_time_estimated": f"{(len(client_ips) * 15) + 30} segundos"  # 15s por cliente + 30s server
        }
        
        logger.info(f"✅ Server-client upgrade completado SECUENCIAL: {server_ip}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error en server-client upgrade {server_ip}: {str(e)}")
        return {"error": str(e), "server_ip": server_ip} 

def upgrade_network_optimized_hybrid(topology_info, user_tacacs, pass_tacacs, so_upgrade, parche_upgrade, download, ip_ftp, pass_ftp):
    """
    Upgrade optimizado híbrido: Celery para stacks, secuencial para conectados
    """
    results = []
    
    # 1. Procesar stacks en PARALELO (Celery efectivo)
    if topology_info['stacks']:
        logger.info(f"🚀 Procesando {len(topology_info['stacks'])} stacks en PARALELO")
        stack_tasks = []
        for stack in topology_info['stacks']:
            # Crear tarea individual para cada stack
            task = upgrade_stack_optimized.delay(stack, user_tacacs, pass_tacacs, so_upgrade, parche_upgrade, download, ip_ftp, pass_ftp)
            stack_tasks.append(task)
        
        # Ejecutar stacks en paralelo usando Celery
        from celery import group
        task_group = group(stack_tasks)
        stack_results = task_group.get()
        results.extend(stack_results)
        logger.info(f"✅ {len(topology_info['stacks'])} stacks procesados en paralelo")
    
    # 2. Procesar switches conectados SECUENCIALMENTE (limitado por ancho de banda)
    if topology_info['connected_switches']:
        logger.info(f"⏱️ Procesando {len(topology_info['connected_switches'])} grupos conectados SECUENCIALMENTE")
        for connected_group in topology_info['connected_switches']:
            result = upgrade_server_client_group_sequential(connected_group, user_tacacs, pass_tacacs, so_upgrade, parche_upgrade, download, ip_ftp, pass_ftp)
            results.append(result)
            logger.info(f"✅ Grupo conectado procesado secuencialmente")
    
    # 3. Procesar switches individuales en PARALELO (Celery efectivo)
    if topology_info['individual_switches']:
        logger.info(f"🚀 Procesando {len(topology_info['individual_switches'])} switches individuales en PARALELO")
        individual_tasks = []
        for individual_ip in topology_info['individual_switches']:
            # Crear tarea individual para cada switch
            task = to_switch_optimized_improved.delay(user_tacacs, pass_tacacs, individual_ip, so_upgrade, parche_upgrade, download, ip_ftp, pass_ftp)
            individual_tasks.append(task)
        
        # Ejecutar switches individuales en paralelo usando Celery
        from celery import group
        task_group = group(individual_tasks)
        individual_results = task_group.get()
        results.extend(individual_results)
        logger.info(f"✅ {len(topology_info['individual_switches'])} switches individuales procesados en paralelo")
    
    return results

def analyze_optimization_potential(topology_info):
    """
    Analiza el potencial de optimización según la topología
    """
    analysis = {
        'stacks_count': len(topology_info['stacks']),
        'connected_groups_count': len(topology_info['connected_switches']),
        'individual_switches_count': len(topology_info['individual_switches']),
        'celery_effective': False,
        'bandwidth_limited': False,
        'recommendation': ''
    }
    
    # Calcular potencial de optimización
    total_switches = (
        sum(stack['total_members'] for stack in topology_info['stacks']) +
        sum(group['total_switches'] for group in topology_info['connected_switches']) +
        len(topology_info['individual_switches'])
    )
    
    # Si hay múltiples stacks o switches individuales → Celery efectivo
    if (len(topology_info['stacks']) > 1 or 
        len(topology_info['individual_switches']) > 1):
        analysis['celery_effective'] = True
        analysis['recommendation'] = 'Usar Celery para optimización real'
    
    # Si hay switches conectados → Limitado por ancho de banda
    if len(topology_info['connected_switches']) > 0:
        analysis['bandwidth_limited'] = True
        analysis['recommendation'] += ' + Secuencial para switches conectados'
    
    # Calcular tiempo estimado
    if analysis['celery_effective']:
        analysis['estimated_time'] = f"{total_switches * 2} minutos (paralelo)"
    else:
        analysis['estimated_time'] = f"{total_switches * 5} minutos (secuencial)"
    
    logger.info(f"📊 Análisis de optimización:")
    logger.info(f"   - Stacks: {analysis['stacks_count']}")
    logger.info(f"   - Grupos conectados: {analysis['connected_groups_count']}")
    logger.info(f"   - Switches individuales: {analysis['individual_switches_count']}")
    logger.info(f"   - Celery efectivo: {analysis['celery_effective']}")
    logger.info(f"   - Limitado por ancho de banda: {analysis['bandwidth_limited']}")
    logger.info(f"   - Recomendación: {analysis['recommendation']}")
    logger.info(f"   - Tiempo estimado: {analysis['estimated_time']}")
    
    return analysis 