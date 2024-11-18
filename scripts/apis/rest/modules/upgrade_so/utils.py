import pexpect
import os
from dotenv import load_dotenv
import re
from datetime import datetime
import time

# GLOBAL VARIABLES
TIME_SLEEP = 0.1

def to_router(list_ip_gestion, link, so_upgrade, parche_upgrade):
    load_dotenv(override=True)
    CYBERARK_USER = os.getenv("CYBERARK_USER")
    CYBERARK_PASS = os.getenv("CYBERARK_PASS")
    CYBERARK_IP = os.getenv("CYBERARK_IP")
    CRT_IP = os.getenv("CRT_IP")
    CRT_USER = os.getenv("CRT_USER")
    user_tacacs = os.getenv("MINPUB_USER")
    pass_tacacs = os.getenv("MINPUB_PASS")
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    file_txt = f"media/upgrade_so/{now}.txt"
    url_txt = f"{link}/{file_txt}"
    result = []

    try:
        # Ingreso al Cyberark
        child = pexpect.spawn(f"ssh -o StrictHostKeyChecking=no {CYBERARK_USER}@{CYBERARK_IP}", timeout=60)
        child.logfile = open(file_txt, "wb")
        child.expect("[Pp]assword:")
        child.sendline(CYBERARK_PASS)
        child.expect(f"user:")
        child.sendline(CRT_USER)
        child.expect(f"address:")
        child.sendline(CRT_IP)
        child.expect(r"\]\$")
        for ip in list_ip_gestion:
            item = {}
            item["ip"] = ip
            result.append(to_switch(child, user_tacacs, pass_tacacs, ip, so_upgrade, parche_upgrade))
            time.sleep(5)
        child.send("exit")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.close()

        return result
    except pexpect.ExceptionPexpect:
        return {"msg": "ERROR"}


def to_switch(child, user_tacacs, pass_tacacs, ip, so_upgrade, parche_upgrade):
    result = {}
    version = None
    vlanif199 = False
    FILE_SERVER = os.getenv("FILE_SERVER")
    FTP_USER = os.getenv("FTP_USER")
    FTP_PASS = os.getenv("FTP_PASS")
    interface_ip = None
    soInSwitch = False
    parcheInSwitch = False
    sizeFree = None
    listSOInSwitch = []
    listParcheInSwitch = []
    soSizeInFTPInMegas = None
    parcheSizeInFTPInMegas = None
    sufficientCapacity = None

    child.send(f"telnet {ip}")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect("[Uu]sername:")
    child.send(user_tacacs)
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect("[Pp]assword:")
    child.send(pass_tacacs)
    time.sleep(TIME_SLEEP)
    child.sendline("")

    prompt_server = child.expect([r"\s<[\w\-.]+>", r"\]\$"])
    if prompt_server == 1:
        return result

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
        output_interfaceVlanif199_pattern.reverse()
        
        for ip_item in output_interfaceVlanif199_pattern:
            child.send(f"ping -a {ip_item} {FILE_SERVER}")
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"\s<[\w\-.]+>")
            output_ping = child.before.decode("utf-8")
            output_ping_pattern = re.findall(r'round-trip min\/avg\/max ', output_ping)
            if output_ping_pattern:
                interface_ip = ip_item
                break

        child.send(f"dir")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\s<[\w\-.]+>")
        output_dirInSwitch = child.before.decode("utf-8")
        output_soInSwitch_pattern = re.search(rf'\b{so_upgrade}\b', output_dirInSwitch)
        output_parcheInSwitch_pattern = re.search(rf'\b{parche_upgrade}\b', output_dirInSwitch)
        output_sizeInSwitch_pattern = re.search(r' KB total \((\S+) KB free\)', output_dirInSwitch)
        listSOInSwitch_pattern = re.findall(r' (\S+) +\S+ +\S+ +\S+ +\S+ +(\S+\.cc)\s', output_dirInSwitch)
        listParcheInSwitch_pattern = re.findall(r' (\S+) +\S+ +\S+ +\S+ +\S+ +(\S+\.PAT)\s', output_dirInSwitch)
        
        if output_soInSwitch_pattern:
            soInSwitch = True
        if output_parcheInSwitch_pattern:
            parcheInSwitch = True
        if output_sizeInSwitch_pattern:
            sizeFree = output_sizeInSwitch_pattern.group(1)
            sizeFree = round(int(re.sub(",", "", sizeFree)) / 1024, 2)
        for so_item in listSOInSwitch_pattern:
            listSOInSwitch.append({"sizeSOInMB": round(int(re.sub(",", "", so_item[0])) / (1024 * 1024), 2), "nameSO": so_item[1]})
        for parche_item in listParcheInSwitch_pattern:
            listParcheInSwitch.append({"sizeParcheInMB": round(int(re.sub(",", "", parche_item[0])) / (1024 * 1024), 2), "nameParche": parche_item[1]})

    if interface_ip:
        child.send(f"ftp -a {ip_item} {FILE_SERVER}")
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

        # User(172.19.216.127:(none)):
        #child.expect(r"\s<[\w\-.]+>")
        #output_ping = child.before.decode("utf-8")
        #output_ping_pattern = re.findall(r'round-trip min\/avg\/max ', output_ping)

    child.send(f"quit")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"\]\$")

    if isinstance(soSizeInFTPInMegas, float) and isinstance(parcheSizeInFTPInMegas, float) and isinstance(sizeFree, float):
        if (sizeFree - (soSizeInFTPInMegas + parcheSizeInFTPInMegas)) > 0:
            sufficientCapacity = True
        else:
            sufficientCapacity = False

    result["IPv4OfStack"] = ip 
    result["stacks"] = result_stack
    result["countStacks"] = len(result_stack)
    result["versionSwitch"] = version
    result["versionByStack"] = result_startup
    result["Vlanif199_isFound"] = vlanif199
    result["ipForPingAndFTP"] = interface_ip
    result["soInSwitch"] = soInSwitch
    result["parcheInSwitch"] = parcheInSwitch
    result["sizeFreeInMB"] = sizeFree
    result["listSOInSwitch"] = listSOInSwitch
    result["listParcheInSwitch"] = listParcheInSwitch
    result["soSizeInFTPInMB"] = soSizeInFTPInMegas
    result["parcheSizeInFTPInMB"] = parcheSizeInFTPInMegas
    result["sufficientCapacity"] = sufficientCapacity
    return result