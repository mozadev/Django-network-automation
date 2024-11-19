import pexpect
import os
import time
from rest.modules.update_vrf.commands import commands_to_huawei
import re
import pandas as pd
from dotenv import load_dotenv

# GLOBAL VARIABLES
TIME_SLEEP = 0.1

def to_router(action, user_tacacs, pass_tacacs, pe, sub_interface, vrf_new, vrf_old, cliente, password, commit):
    load_dotenv(override=True)
    TACASTS_USER = user_tacacs
    TACASTS_PASS = pass_tacacs
    CYBERARK_USER = os.getenv("CYBERARK_USER")
    CYBERARK_PASS = os.getenv("CYBERARK_PASS")
    CYBERARK_IP = os.getenv("CYBERARK_IP")
    CRT_IP = os.getenv("CRT_IP")
    CRT_USER = os.getenv("CRT_USER")
    interface_log = sub_interface.replace("/", "_")
    name_file = f"media/{action}_{pe}_{interface_log}.txt"
    url_file = f"http://10.200.90.248:9000/{name_file}"

    try:
        # Ingreso al Cyberark
        child = pexpect.spawn(f"ssh -o StrictHostKeyChecking=no {CYBERARK_USER}@{CYBERARK_IP}", timeout=60)
        child.logfile = open(name_file, "wb")
        child.expect("[Pp]assword:")
        child.sendline(CYBERARK_PASS)
        child.expect(f"user:")
        child.sendline(CRT_USER)
        child.expect(f"address:")
        child.sendline(CRT_IP)
        # INGRESANDO AL HUAWEI
        child.expect("\$")
        time.sleep(TIME_SLEEP)
        child.send(f"ssh -o StrictHostKeyChecking=no {TACASTS_USER}@{pe}")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        time.sleep(TIME_SLEEP)
        child.expect("[Pp]assword:")
        time.sleep(TIME_SLEEP)
        child.send(TACASTS_PASS)
        time.sleep(TIME_SLEEP)
        child.sendline("")
        time.sleep(TIME_SLEEP)
        # Dentro del router
        child.expect("\>")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        time.sleep(TIME_SLEEP)

        # PARAMETROS ENCONTRADOS SI O SI: IP - VRF
        ip_found, vrf_found, cid_found, group_found, asnumber_found, ip_mra_found, mascara_mra_found = search_parameters(child, sub_interface, vrf_new, vrf_old, cliente)
        if ip_found:
            # IP para VRF: aumentar una unidad en el último octeto
            ip_interface = ip_found
            ip_vrf = red_wan_ip(ip_found, 1)
            if vrf_found == vrf_old:
                if cid_found:
                    pass
                else:
                    cid_found = ""

                if asnumber_found:
                    if ip_mra_found and mascara_mra_found:
                        msg_mra = None
                    else:
                        ip_vrf_found = red_wan_ip(ip_found, 1)
                        msg_mra = f"INCOMPLETO: No se encontró la route static PREFERENCE 1 para VRF {vrf_old} e WAN {ip_vrf_found}"
                        #child.close()
                        #
                        #eturn f"ERROR: No se encontró la ip y máscara del MRA en el enrutamiento static para la VRF ACTUAL {vrf_old} y ip {ip_vrf_found}", 400, url_file
                else:
                    child.close()
                    return f"ERROR: AS-NUMBER NO ENCONTRADO EN EL GRUPO {group_found} DE LA VPN-INSTANCE {vrf_new} YA ENCONTRADA", 400, url_file
            else:
                child.close()
                return f"ERROR: VRF ingresada anterior {vrf_old} no encontrada o no coincide con la VRF en la interface {sub_interface} del equipo {pe}", 400, url_file
        else:
            child.close()
            return f"ERROR: IPv4 en la interface {sub_interface} del equipo {pe} no encontrada", 400, url_file


        child.send(f" ")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        
        for command in commands_to_huawei(sub_interface, vrf_new, vrf_old, ip_interface, ip_vrf, cid_found, cliente, asnumber_found, password, group_found, commit, ip_mra_found, mascara_mra_found):
            prompt = child.expect([command["prompt"], "which will affect BGP peer relationship establishment\. Are you sure you want to continue\? \[Y\/N\]:"])
            if prompt == 0:
                child.send(command["command"])
            else:
                child.send(commit)
                time.sleep(TIME_SLEEP)
                child.sendline("")
                child.expect(command["prompt"])
                child.send(command["command"])
                

                
            
            time.sleep(TIME_SLEEP)
            child.sendline("")
                
        child.send("quit")
        time.sleep(TIME_SLEEP)
        child.sendline("")

        child.expect("\$")
        time.sleep(TIME_SLEEP)
        child.send("exit")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.close()

        if msg_mra:
            return f"PARCIAL EXITOSO (INCOMPLETO ROUTE STATIC): NUEVA VRF {vrf_new} CREADA Y ASIGNADA EN {pe} {sub_interface} - {msg_mra}", 200, url_file
        else:
            return f"EXITOSO: NUEVA VRF {vrf_new} CREADA Y ASIGNADA EN {pe} {sub_interface}", 200, url_file
    except pexpect.TIMEOUT as e:
        return f"ERROR: FALLÓ PARA {pe} {sub_interface}: NO SE CREÓ LA VRF {vrf_new}, el router no responde: {e}", 500, url_file



def search_parameters(child, sub_interface, vrf_new, vrf_old, cliente):
    vrf_new_str = convert_num_to_str(vrf_new, 5)
    vrf_old_str = convert_num_to_str(vrf_old, 5)
    ip_found = None
    vrf_found = None
    cid_found = None
    group_found = 0
    asnumber_old_found = None
    sysname_found = None
    ip_mra_found = None
    mascara_mra_found = None
    asnumber_found = None
    
    child.expect(r"\<.*\>")

    # HOSTNAME
    child.send(f"display current-configuration | include sysname")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"\<.*\>")
    output_sysname = child.before.decode("utf-8")
    sysname_pattern = re.search(r'sysname (\S+)', output_sysname)
    if sysname_pattern:
        sysname_found = sysname_pattern.group(1)

    # VER LA INTERFACE 
    child.send(f"dis curr int {sub_interface}")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(rf"\<{sysname_found}\>")
    output_interface = child.before.decode("utf-8")
    ip_pattern = re.search(r'ip address (\d+\.\d+\.\d+\.\d+)', output_interface)
    vrf_pattern = re.search(r'ip binding vpn-instance (\d+)', output_interface)
    cid_pattern = re.search(r'CID (\d+)', output_interface)
    if ip_pattern:
        ip_found = ip_pattern.group(1)
    if vrf_pattern:
        vrf_found = int(vrf_pattern.group(1))
    if cid_pattern:
        cid_found = int(cid_pattern.group(1))

    # ACTUAL VPN-INSTANCE EN LA BGP 12252: RECICLAR SUS VALORES
    child.send(f"dis curr conf bgp | begin {vrf_old_str} | no-more")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(rf'\<{sysname_found}\>')
    output_bgp_old = child.before.decode("utf-8")
    output_bgp_old_list = re.split("\r\n", output_bgp_old)

    try: 
        output_bgp_old_result = output_bgp_old_list[:(output_bgp_old_list.index(" #") + 1)]
    except ValueError:
        output_bgp_old_result = []


    ip_vrf_old = red_wan_ip(ip_found, 1)

    for item in output_bgp_old_result:
        asnumber_old_pattern = re.search(rf'peer {ip_vrf_old} as-number (\d+)', item)
        if asnumber_old_pattern:
            asnumber_old_found = int(asnumber_old_pattern.group(1))

    # NUEVA VPN-INSTANCE EN LA BGP 12252: VER SI YA ESTÁ CREADA
    child.send(f"dis curr conf bgp | begin {vrf_new_str} | no-more")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(rf"\<{sysname_found}\>")
    output_bgp_new = child.before.decode("utf-8")
    output_bgp_new_list = re.split("\r\n", output_bgp_new)
    try: 
        output_bgp_new_result = output_bgp_new_list[:(output_bgp_new_list.index(" #") + 1)]
    except ValueError:
        output_bgp_new_result = []

    for item in output_bgp_new_result:
        group_pattern = re.search(rf'group {cliente} external', item)
        if group_pattern:
            for item_internal in output_bgp_new_result:
                asnumber_pattern = re.search(rf'peer {cliente} as-number (\d+)', item_internal)
                if asnumber_pattern:
                    asnumber_found = int(asnumber_pattern.group(1))
                    break
            if asnumber_found == asnumber_old_found: 
                group_found = 1
            else: 
                group_found = 2
            break

    # VER LAS ROUTE-STATIC
    child.send(f"dis curr configuration route-static | i {ip_vrf_old} | no-more")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(rf"\<{sysname_found}\>")
    output_routestatic = child.before.decode("utf-8")
    output_routestatic_list = re.split("\r\n", output_routestatic)
    for item in output_routestatic_list:
        routerstatic_pattern = re.search(rf"ip route-static vpn-instance {vrf_old_str} (\d+\.\d+\.\d+\.\d+) (\d+\.\d+\.\d+\.\d+) {ip_vrf_old} preference 1", item)
        if routerstatic_pattern:
            ip_mra_found = routerstatic_pattern.group(1)
            mascara_mra_found = routerstatic_pattern.group(2)
            break
    return ip_found, vrf_found, cid_found, group_found, asnumber_old_found, ip_mra_found, mascara_mra_found


def red_wan_ip(ip, i):
    ip_temp = ip.split(".")
    ip_temp = [int(x) for x in ip_temp]
    ip_temp[-1] = ip_temp[-1] + i
    ip_temp = [str(x) for x in ip_temp]
    new_ip = ".".join(ip_temp)
    return new_ip


def clean_excel_changevrf(data):
    try:
        df = pd.read_excel(data, dtype={
            "router_pe": str, 
            "subinterface_pe": str, 
            "vrf_old": int, 
            "vrf_new": int,
            "cliente": str,
            "pass_cipher": str,
            })

        df_columns = df[["router_pe", "subinterface_pe", "vrf_old", "vrf_new", "cliente", "pass_cipher"]].copy()
        return df_columns.to_dict(orient='records'), 200
    except ValueError as e:
        return f"ERROR de Tipo, por favor ingresar tipos validos en {e}", 404


def convert_num_to_str(number, digit):
    num = str(number)
    len_num = len(num)
    if len_num < digit:
        new_txt = str(number + 10**(digit))[1:]
    else:
        new_txt = num
    return new_txt