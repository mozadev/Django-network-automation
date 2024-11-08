import pexpect
import os
from dotenv import load_dotenv
from datetime import datetime
import time
import re

# GLOBAL VARIABLES
TIME_SLEEP = 0.1


def to_server(user_tacacs, pass_tacacs, cid_list, ip_owner, commit):
    load_dotenv(override=True)
    CYBERARK_USER = os.getenv("CYBERARK_USER")
    CYBERARK_PASS = os.getenv("CYBERARK_PASS")
    CYBERARK_IP = os.getenv("CYBERARK_IP")
    CRT_IP = os.getenv("CRT_IP")
    CRT_USER = os.getenv("CRT_USER")
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    name_file = f"media/internet_upgrade/{now}.txt"
    url_file = f"{ip_owner}/{name_file}"
    result = []

    try:
        # Ingreso al Cyberark
        child = pexpect.spawn(f"ssh -o StrictHostKeyChecking=no {CYBERARK_USER}@{CYBERARK_IP}", timeout=30)
        child.logfile = open(name_file, "wb")
        child.expect("[Pp]assword:")
        child.sendline(CYBERARK_PASS)
        child.expect(f"user:")
        child.sendline(CRT_USER)
        child.expect(f"address:")
        child.sendline(CRT_IP)
        child.expect(r"\]\$")
        for cid in cid_list:
            item = {}
            item["msg"], item["status"] = to_router(child, user_tacacs, pass_tacacs, cid, commit)
            result.append(item)
            time.sleep(5)
        child.send("exit")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.close()

    except Exception as e:    
        return f"{e}"
    return result


def to_router(child, user_tacacs, pass_tacacs, cid, commit):
    wan_found = None
    ippe_found = None
    pesubinterface_found = None
    trafficpolicy_found = None
    pe_ipmascara_found = None
    mac_found = None
    lldp_found = None
    interface_cliente_found = None
    trafficpolicy_cliente_found = None
    interface_cpe_found = None
    pesubinterface_physical = None
    trafficpolicy_cpe_found = None
    pe_os = None
    cpe_os = None
    acceso_os = None
    pe_protocol = None
    cpe_protocol = None
    acceso_protocol = None

    # OBTENER LA WAN DEL CID
    child.send(f"hh {cid} | grep -v '^#' | awk \'{{print $1}}\'")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"\]\$")
    output_wan = child.before.decode("utf-8")
    wan_pattern = re.search(r'(\d+\.\d+\.\d+\.\d+)', output_wan)
    if wan_pattern:
        wan_found = wan_pattern.group(1)
    else:
        return f"WAN del CID {cid} no encontrado", 400
    # OBTENER EL PE DEL CID
    GET_PE = os.getenv("GET_PE")
    child.send(f"ssh -o StrictHostKeyChecking=no {user_tacacs}@{GET_PE}")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect("[Pp]assword:")
    child.send(pass_tacacs)
    time.sleep(TIME_SLEEP)
    child.sendline("")
    prompt_server = child.expect([r"\<\S+\>", r"\]\$"])
    if prompt_server == 1:
        return f"No se pudo ingresar al {GET_PE}", 400
    
    child.send(f"display ip routing-table {wan_found} | no-more")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"\<\S+\>")
    output_ippe = child.before.decode("utf-8")
    ippe_pattern = re.search(r' +(\d+\.\d+\.\d+\.\d+)  +', output_ippe)
    if ippe_pattern:
        ippe_found = ippe_pattern.group(1)
    else:
        child.send(f"quit")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\]\$")

        return f"PE del CID {cid} no encontrado", 400
    
    child.send(f"quit")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"\]\$")

    # IR AL PE AQUÍ NECESITA SABER SI ES HUAWEI
    child.send(f"ssh -o StrictHostKeyChecking=no {user_tacacs}@{ippe_found}")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    prompt_pe_ssh = child.expect([r"[Pp]assword:", r"\]\$"])
    if prompt_pe_ssh == 1:
        return f"No se pudo ingresar al PE {ippe_found} por ssh", 400
    
    child.send(pass_tacacs)
    time.sleep(TIME_SLEEP)
    child.sendline("")
    prompt_pe = child.expect([r"\<\S+\>", r"\]\$"])
    if prompt_pe == 1:
        return f"No se pudo ingresar al PE {ippe_found}", 400
    else:
        pe_os = "huawei"
        pe_protocol = "ssh"
    
    # OBTENER LA INTERFACE
    child.send(f"display ip routing-table {wan_found} | no-more")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"\<.*\>")

    output_pesubinterface = child.before.decode("utf-8")
    pesubinterface_pattern = re.search(r'(GigabitEthernet\S+|Virtual-Ethernet\S+)', output_pesubinterface)
    if pesubinterface_pattern:
        pesubinterface_found = pesubinterface_pattern.group(1)
        pesubinterface_physical = pesubinterface_found.split(".")[0]
    else:
        pesubinterfacetrunk_pattern = re.search(r'(Eth-Trunk\S+)', output_pesubinterface)
        if pesubinterfacetrunk_pattern:
            pesubinterface_found = pesubinterfacetrunk_pattern.group(1)
            pesubinterfacetrunk = pesubinterface_found.split(".")[0]
            child.send(f"display interface {pesubinterfacetrunk} | no-more ")
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"\<\S+\>")
            output_pesubinterfacetrunk = child.before.decode("utf-8")
            pesubinterfacetrunkup_pattern = re.search(r"(GigabitEthernet\S+) +UP", output_pesubinterfacetrunk)
            if pesubinterfacetrunkup_pattern:
                pesubinterface_physical = pesubinterfacetrunkup_pattern.group(1)
            else:
                child.send(f"quit")
                time.sleep(TIME_SLEEP)
                child.sendline("")
                child.expect(r"\]\$")

                return f"SUBINTERFACE TRUNK DEL PE {ippe_found} del CID {cid} no encontrado, ninguno está en UP", 400
        else:
            child.send(f"quit")
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"\]\$")

            return f"NO SE ENCUENTRA SUBINTERFACE DEL PE {ippe_found} del CID {cid} no encontrado", 400
        
    # OBTENER LA IP - MASCARA - TRAFFIC-POLICY
    child.send(f"display curr int {pesubinterface_found} | no-more")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"\<\S+\>")
    time.sleep(TIME_SLEEP)

    output_trafficpolicy = child.before.decode("utf-8")
    trafficpolicy_pattern = re.findall(r'traffic-policy (\S+) (\S+)', output_trafficpolicy)
    if len(trafficpolicy_pattern) > 0:
        trafficpolicy_found = trafficpolicy_pattern

    output_trafficpolicy = child.before.decode("utf-8")
    pe_ipmascara_pattern = re.search(r'ip address (\d+\.\d+\.\d+\.\d+) (\d+\.\d+\.\d+\.\d+)', output_trafficpolicy)
    if pe_ipmascara_pattern:
        pe_ipmascara_found = { "ip": pe_ipmascara_pattern.group(1), "mascara": pe_ipmascara_pattern.group(2)}
    else:
        child.send(f"quit")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\]\$")

        return f"IP y/o MÁSCARA NO ENCONTRADO EN SUBINTERFACE DEL PE {ippe_found} del CID {cid} no encontrado", 400
    
    # DIVIDIR ESCENARIOS DEPENDIENDO DE LA MASCARA
    pe_commands_list = None 
    pe_commands_is = is_mascara30(pe_ipmascara_found["mascara"])
    if pe_commands_is:
        pe_commands_list = [
            ""
        ]
    
    # OBTENER LA MAC DE LA WAN EN EL PE
    child.send(f"display arp all | i {wan_found}")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"\<\S+\>")
    time.sleep(TIME_SLEEP)

    output_mac = child.before.decode("utf-8")
    mac_pattern = re.search(r'(\d+\.\d+\.\d+\.\d+) +(\S+)', output_mac)
    if mac_pattern:
        mac_found = mac_pattern.group(2)
    else:
        child.send(f"quit")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\]\$")

        return f"MAC NO ENCONTRADO EN EL PE {ippe_found} del CID {cid} no encontrado", 400
    
    # OBTENER SYSNAME CON LLDP
    child.send(f"display lldp neighbor interface {pesubinterface_physical} | no-more")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"\<\S+\>")
    time.sleep(TIME_SLEEP)

    output_lldp = child.before.decode("utf-8")
    lldp_pattern = re.search(r'System name +:(\S+)', output_lldp)
    if lldp_pattern:
        lldp_found = lldp_pattern.group(1)
    else:
        child.send(f"quit")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\]\$")

        return f"SYSNAME DEL EQUIPO LLDP NO ENCONTRADO EN EL PE {ippe_found} del CID {cid} no encontrado", 400

    # INGRESANDO AL CPE 
    if not pe_commands_is:
        child.send(f"telnet {wan_found}")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        prompt_cpe = child.expect([r"\<\S+\>", r"[Uu]sername:"])
        if prompt_cpe == 1:
            child.send(user_tacacs)
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"[Pp]assword:")
            child.send(pass_tacacs)
            time.sleep(TIME_SLEEP)
            child.sendline("")

            prompt_cpe_in = child.expect([r"\s[\w\-.]+>", r"\s[\w\-.]+#", r"\<[\w\-.]+>"])
            if prompt_cpe_in in [0, 1]:
                if prompt_cpe_in == 0:
                    child.send("ena")
                    time.sleep(TIME_SLEEP)
                    child.sendline("")
                    child.expect(r"[Pp]assword:")
                    child.send(pass_tacacs)
                    time.sleep(TIME_SLEEP)
                    child.sendline("")
                    child.expect(r"\S+\#")
                
                cpe_os = "cisco"
                cpe_protocol = "telnet"
                child.send(f"terminal length 0")
                time.sleep(TIME_SLEEP)
                child.sendline("")
                child.expect(r"\S+\#")

                child.send(f"sh ip int brief")
                time.sleep(TIME_SLEEP)
                child.sendline("")
                child.expect(r"\S+\#")

                output_interface_cpe = child.before.decode("utf-8")
                interface_cpe_pattern = re.search(rf'\n(\S+) +{wan_found}', output_interface_cpe)
                if interface_cpe_pattern:
                    interface_cpe_found = interface_cpe_pattern.group(1)
                else:
                    child.send("exit")
                    time.sleep(TIME_SLEEP)
                    child.sendline("")
                    child.expect(r"\<\S+\>")
                    child.send(f"quit")
                    time.sleep(TIME_SLEEP)
                    child.sendline("")
                    child.expect(r"\]\$")

                    return f"CPE: INTERFACE DEL ACCESO CISCO {wan_found} NO ENCONTRADO del CID {cid} no encontrado", 400
            
                child.send(f"sh run int {interface_cpe_found}")
                time.sleep(TIME_SLEEP)
                child.sendline("")
                child.expect(r"\S+\#")

                output_trafficpolicy_cpe = child.before.decode("utf-8")
                trafficpolicy_cpe_pattern = re.search(rf'bandwidth (\d+)', output_trafficpolicy_cpe)
                if trafficpolicy_cpe_pattern:
                    trafficpolicy_cpe_found = trafficpolicy_cpe_pattern.group(1)

                child.send("exit")
                time.sleep(TIME_SLEEP)
                child.sendline("")
                child.expect(r"\<\S+\>")
            else: 
                cpe_os = "huawei"
                cpe_protocol = "telnet"
                child.send(f"screen-length 0 temporary")
                time.sleep(TIME_SLEEP)
                child.sendline("")
                child.expect(r"\<\S+\>")

                child.send(f"display ip interface brief")
                time.sleep(TIME_SLEEP)
                child.sendline("")
                child.expect(r"\<\S+\>")

                output_interface_cpe = child.before.decode("utf-8")
                interface_cpe_pattern = re.search(rf'\n(\S+) +{wan_found}', output_interface_cpe)
                if interface_cpe_pattern:
                    interface_cpe_found = interface_cpe_pattern.group(1)
                else:
                    child.send("quit")
                    time.sleep(TIME_SLEEP)
                    child.sendline("")
                    child.expect(r"\<\S+\>")
                    child.send(f"quit")
                    time.sleep(TIME_SLEEP)
                    child.sendline("")
                    child.expect(r"\]\$")

                    return f"CPE: INTERFACE DEL ACCESO HUAWEI {wan_found} NO ENCONTRADO del CID {cid} no encontrado", 400

                child.send(f"display current-configuration interface {interface_cpe_found}")
                time.sleep(TIME_SLEEP)
                child.sendline("")
                child.expect(r"\<\S+\>")

                output_trafficpolicy_cpe = child.before.decode("utf-8")
                trafficpolicy_cpe_pattern = re.findall(r'traffic-policy (\S+) (\S+)', output_trafficpolicy_cpe)
                if len(trafficpolicy_cpe_pattern):
                    trafficpolicy_cpe_found = trafficpolicy_cpe_pattern

                child.send("quit")
                time.sleep(TIME_SLEEP)
                child.sendline("")
                child.expect(r"\<\S+\>")
        else:
            child.send(f"quit")
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"\]\$")
            return f"CPE: NO SE PUDO INGRESAR AL CPE {wan_found} del CID {cid} no encontrado", 400
    
    
    child.send(f"quit")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"\]\$")

    # INGRESANDO AL LLDP - INTERFACE DEL CLIENTE - ACCESO
    child.send(f"ssh -o StrictHostKeyChecking=no {user_tacacs}@{lldp_found}")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    prompt_acceso = child.expect([r"[Pp]assword:", r"\]\$"])
    if prompt_acceso == 1:
        return f"No se pudo ingresar al ACCESO {lldp_found} del cid {cid}", 400
    
    child.send(pass_tacacs)
    time.sleep(TIME_SLEEP)
    child.sendline("")
    prompt_acceso = child.expect([r"\<\S+\>", r"\]\$"])
    if prompt_acceso == 1:
        return f"No se pudo ingresar al ACCESO {lldp_found} del cid {cid}", 400
    
    acceso_os = "huawei"
    acceso_protocol = "ssh"
    child.send(f"screen-length 0 temporary")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"\<\S+\>")

    child.send(f"display mac-address | i {mac_found}")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"\<\S+\>")
    output_interface_cliente = child.before.decode("utf-8")
    interface_cliente_pattern = re.search(rf'\n{mac_found} +(\S+) +(\S+)', output_interface_cliente)
    if interface_cliente_pattern:
        interface_cliente_found = interface_cliente_pattern.group(2)
    else:
        child.send(f"quit")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\]\$")

        return f"LLDP: INTERFACE DEL CLIENTE  NO ENCONTRADO del CID {cid} no encontrado", 400
    
    # VER LA INTERFACE DEL CLIENTE
    interface_cliente_found = interface_cliente_found.replace("GE", "Gi")
    child.send(f"display curr int {interface_cliente_found}")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"\<\S+\>")
    output_trafficpolicy_cliente = child.before.decode("utf-8")
    trafficpolicy_cliente_pattern = re.findall(r'traffic-policy (\S+) (\S+)', output_trafficpolicy_cliente)
    if len(trafficpolicy_cliente_pattern) > 0:
        trafficpolicy_cliente_found = trafficpolicy_cliente_pattern

    child.send(f"quit")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"\]\$")

    #

    result = {
        "cid": cid,
        "wan_ofInternet": wan_found,
        "pe_device": {
            "pe": ippe_found,
            "pe_subInterface": pesubinterface_found,
            "pe_interfacePhysical": pesubinterface_physical,
            "pe_trafficpolicyInSubInterface": trafficpolicy_found,
            "pe_ipmascaraInSubInterface": pe_ipmascara_found,
            "pe_macOfCPE": mac_found,
            "pe_os": pe_os,
            "pe_protocol": pe_protocol,
            "pe_analisis": {
                "pe_upgrade": pe_commands_is,
                "pe_commands": pe_commands_list,
            },
        },
        "cpe_device": {
            "cpe": wan_found,
            "cpe_interface": interface_cpe_found,
            "cpe_trafficpolicy": trafficpolicy_cpe_found,
            "cpe_os": cpe_os,
            "cpe_protocol": cpe_protocol,
            "cpe_analisis": {
                "cpe_upgrade": None,
                "cpe_commands": None,
            },
        },
        "acceso_device": {
            "acceso": lldp_found,
            "acceso_interface": interface_cliente_found,
            "acceso_trafficpolicy": trafficpolicy_cliente_found,
            "acceso_os": acceso_os,
            "acceso_protocol": acceso_protocol,
            "cpe_analisis": {
                "acceso_upgrade": None,
                "acceso_commands": None,
            }
        },
    }

    return result, 200


def is_mascara30(mascara):
    lastocteto = int(mascara.split(".")[-1])
    if lastocteto == 252:    
        return True
    else:
        return False
    

def cpe_huawei(child):
    return