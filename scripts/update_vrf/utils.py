import pexpect
import os
import time
from commands import commands_to_huawei, commands_to_huawei_read
import re

# GLOBAL VARIABLES
TIME_SLEEP = 0.1

def to_router(pe, sub_interface, vrf_new, vrf_old, cliente, asnumber, password):
    TACASTS_USER = os.getenv("TACASTS_USER")
    TACASTS_PASS = os.getenv("TACASTS_PASS")
    CYBERARK_USER = os.getenv("CYBERARK_USER")
    CYBERARK_PASS = os.getenv("CYBERARK_PASS")
    CYBERARK_IP = os.getenv("CYBERARK_IP")
    CRT_IP = os.getenv("CRT_IP")
    CRT_USER = os.getenv("CRT_USER")
    interface_log = sub_interface.replace("/", "_")


    try:
        # Ingreso al Cyberark
        child = pexpect.spawn(f"ssh -o StrictHostKeyChecking=no {CYBERARK_USER}@{CYBERARK_IP}", timeout=30)
        child.logfile = open(f"media/{pe}_{interface_log}.log", "wb")
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
        ip_found, vrf_found, cid_found, group_found, asnumber_found = search_parameters(child, sub_interface, vrf_new, cliente)
        if ip_found:
            # IP para VRF: aumentar una unidad en el último octeto
            ip_interface = ip_found
            ip_vrf = red_wan_ip(ip_found, 1)
            if vrf_found == vrf_old:
                if cid_found:
                    if group_found:
                        new_grupo = False
                        if asnumber_found == asnumber:
                            pass
                        else:
                            child.close()
                            return f"\033[101mERROR\033[0m AS-NUMBER {asnumber} INGRESADO NO COINCIDE CON EL AS_NUMBER {asnumber_found} DEL GRUPO {group_found} DE LA VPN-INSTANCE {vrf_new} YA ENCONTRADA"
                    else:
                        new_grupo = True
                else:
                    cid_found = ""
            else:
                child.close()
                return f"\033[101mERROR\033[0m VRF ingresada anterior {vrf_old} no encontrada o no coincide con la VRF en la interface {sub_interface} del equipo {pe}"
        else:
            child.close()
            return f"\033[101mERROR\033[0m IPv4 en la interface {sub_interface} del equipo {pe} no encontrada"



        for command in commands_to_huawei(sub_interface, vrf_new, vrf_old, ip_interface, ip_vrf, cid_found, cliente, asnumber, password, new_grupo):
            print(command["command"])
            continue
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
        return f"\033[102mEXITOSO\033[0m NUEVA VRF {vrf_new} CREADA Y ASIGNADA EN {pe} {sub_interface}"
    except pexpect.TIMEOUT as e:
        return f"\033[101mERROR\033[0m FALLÓ PARA {pe} {sub_interface}: NO SE CREÓ LA VRF {vrf_new}, el router no responde: {e}"



def search_parameters(child, sub_interface, vrf_new, cliente):
    ip_found = None
    vrf_found = None
    cid_found = None
    group_found = None 
    asnumber_found = None

    for command in commands_to_huawei_read(sub_interface, vrf_new):
        output = child.before
        output_str = output.decode('utf-8')
        ip_pattern = re.search(r'ip address (\d+\.\d+\.\d+\.\d+)', output_str)
        vrf_pattern = re.search(r'ip binding vpn-instance (\d+)', output_str)
        cid_pattern = re.search(r'CID (\d+)', output_str)
        group_pattern = re.search(rf'group RPVFM_{cliente} external', output_str)
        asnumber_pattern = re.search(rf'peer RPVFM_{cliente} as-number (\d+)', output_str)

        if ip_pattern:
            ip_found = ip_pattern.group(1)
        if vrf_pattern:
            vrf_found = int(vrf_pattern.group(1))
        if cid_pattern:
            cid_found = int(cid_pattern.group(1))
        if group_pattern:
            group_found = f"RPVFM_{cliente}"
        if asnumber_pattern:
            asnumber_found = asnumber_pattern.group(1)

        tipo_prompt = child.expect([command["prompt"], "---- More ----"])
        if tipo_prompt == 0:
            child.send(command["command"])
        elif tipo_prompt == 1:
            child.send(" ")
            time.sleep(TIME_SLEEP)
            child.send("q")
            child.expect(command["prompt"])
            child.sendline("")

        time.sleep(TIME_SLEEP)
        child.sendline("")

    return ip_found, vrf_found, cid_found, group_found, asnumber_found


def red_wan_ip(ip, i):
    ip_temp = ip.split(".")
    ip_temp = [int(x) for x in ip_temp]
    ip_temp[-1] = ip_temp[-1] + i
    ip_temp = [str(x) for x in ip_temp]
    new_ip = ".".join(ip_temp)
    return new_ip