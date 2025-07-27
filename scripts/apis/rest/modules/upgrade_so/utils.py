import pexpect
import os
from dotenv import load_dotenv
import re
from datetime import datetime
import time
from .tasks import upgrade_multiple_switches_task

# GLOBAL VARIABLES
TIME_SLEEP = 0.1

def to_router(list_ip_gestion, link, so_upgrade, parche_upgrade, user_tacacs, pass_tacacs, download, ip_ftp, pass_ftp):
    """
    Versión optimizada que usa Celery para procesamiento paralelo
    """
    load_dotenv(override=True)
    CYBERARK_USER = os.getenv("CYBERARK_USER")
    CYBERARK_PASS = os.getenv("CYBERARK_PASS")
    CYBERARK_IP = os.getenv("CYBERARK_IP")
    CRT_IP = os.getenv("CRT_IP")
    CRT_USER = os.getenv("CRT_USER")
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    file_txt = f"media/upgrade_so/{now}.txt"
    url_txt = f"{link}/{file_txt}"
    result = []
    ip_fail = None

    try:
        # Preparar datos para Celery
        switches_data = []
        for ip in list_ip_gestion:
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
        
        # Ejecutar tarea de Celery
        task = upgrade_multiple_switches_task.delay(switches_data)
        
        # Esperar resultado (opcional, puede ser asíncrono)
        result = task.get(timeout=7200)  # 2 horas máximo
        
        return result
        
    except Exception as e:
        return {"msg": f"ERROR, LA API FALLÓ: {str(e)}"}


def to_switch(child, user_tacacs, pass_tacacs, ip, so_upgrade, parche_upgrade, download, ip_ftp, pass_ftp):
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

    child.send(f"telnet {ip}")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    item_input = child.expect([r"[Uu]sername:", r"\]\$"])
    if item_input == 1:
        return {"msg": rf"SWITCH IPv4OfStack {ip} sin gestión"}
    child.send(user_tacacs)
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect("[Pp]assword:")
    child.send(pass_tacacs)
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"\s<[\w\-.]+>")

    child.send(f"screen-length 0 temporary")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"\s<[\w\-.]+>")

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

    child.send(f"display version")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"\s<[\w\-.]+>")
    output_version = child.before.decode("utf-8")
    output_version_pattern = re.search(r'\sVersion (?P<version1>[\w\.]+) \((?P<version2>[\w ]+)\)', output_version)
    if output_version_pattern:
        version = {"number": output_version_pattern.group("version1"), "detail": output_version_pattern.group("version2")}

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

    child.send(f"display ip interface brief")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"\s<[\w\-.]+>")
    output_interfaces = child.before.decode("utf-8")
    output_interfaces_pattern = re.search(r"\bVlanif199\b", output_interfaces)
    if output_interfaces_pattern:
        vlanif199 = True

        child.send(f"display current-configuration interface Vlanif199")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\s<[\w\-.]+>")
        output_interfaceVlanif199 = child.before.decode("utf-8")
        output_interfaceVlanif199_pattern = re.findall(r'ip address (\d+\.\d+\.\d+\.\d+) ', output_interfaceVlanif199)
        routersFTP = routersFTPFromIPv4(output_interfaceVlanif199_pattern, FILE_SERVER)
        
        for ftp_item in routersFTP:
            child.send(f"ping {ftp_item}")
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"\s<[\w\-.]+>")
            output_ping = child.before.decode("utf-8")
            output_ping_pattern = re.findall(r'round-trip min\/avg\/max ', output_ping)
            if output_ping_pattern:
                interface_ip = ftp_item
                break
    
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
        if output_parcheInFTP_pattern:
            parcheSizeInFTPInMegas = round(int(output_parcheInFTP_pattern.group(1)) / (1024 * 1024), 2)

        child.send(r"quit")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\s<[\w\-.]+>")

    for stack in result_stack: 
        child.send("dir {stack}#flash:/".format(stack=stack["MemberID"]))
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
        else:
            stack["soInStack"] = False
        if output_parcheInStack_pattern:
            stack["parcheInStack"]  = True
            if stack["Role"] == "Master":
                parcheInMaster = True
        else:
            stack["parcheInStack"]  = False
        if output_sizeInStack_pattern:
            sizeFreeInStack = output_sizeInStack_pattern.group(1)
            stack["sizeFreeInStack"]  = round(int(re.sub(",", "", sizeFreeInStack)) / 1024, 2)
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

    result_stack = sorted(result_stack, key=master_isFirst)
    child.timeout = 7200
    for stack in result_stack:
        if stack["Role"] == "Master":
            # IR AL SERVIDOR FTP
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
                    child.send(rf"get {so_upgrade}")
                    time.sleep(TIME_SLEEP)
                    child.sendline("")
                    child.expect(r"\n\[ftp\]")
                    soInMaster = True
                    
                if not stack["parcheInStack"] and download == "Y" and parche_upgrade:
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
            # SOLO COPIAR DE UN STACK A OTRO
            memberID = stack["MemberID"]
            if stack["sufficientCapacityInStack"]:
                if not stack["soInStack"] and soInMaster and download == "Y" and so_upgrade:
                    child.send(f"copy {so_upgrade} {memberID}#flash:")
                    time.sleep(TIME_SLEEP)
                    child.sendline("")
                    child.expect(r"\[Y\/N\]:")
                    child.send(f"Y")
                    time.sleep(TIME_SLEEP)
                    child.sendline("")
                    child.expect(r"\s<[\w\-.]+>")

                if not stack["parcheInStack"] and parcheInMaster and download == "Y" and parche_upgrade:
                    child.send(f"copy {parche_upgrade} {memberID}#flash:")
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
    return result


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