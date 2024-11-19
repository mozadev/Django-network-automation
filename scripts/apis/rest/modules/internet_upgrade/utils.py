import pexpect
import os
from dotenv import load_dotenv
from datetime import datetime
import time
import re

# GLOBAL VARIABLES
TIME_SLEEP = 0.1


def to_server(user_tacacs, pass_tacacs, cid_list, ip_owner, commit, newbw):
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
            item["msg"], item["status"] = to_router(child, user_tacacs, pass_tacacs, cid, commit, newbw)
            result.append(item)
            time.sleep(5)
        child.send("exit")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.close()

    except Exception as e:    
        return f"{e}"
    return result


def to_router(child, user_tacacs, pass_tacacs, cid, commit, newbw):
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
    child.send(f"hh {cid} | grep -E \'\\b{cid}\\b\' | grep -E -o \'([0-9]{{1,3}}\.){{3}}[0-9]{{1,3}}\'")
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
    prompt_polo = child.expect([r"[Pp]assword:", r"\]\$"])
    if prompt_polo == 1:
        return f"Problemas al intertar ingresar al {GET_PE}", 400
    child.send(pass_tacacs)
    time.sleep(TIME_SLEEP)
    child.sendline("")
    prompt_server = child.expect([r"\n<\S+>", r"\]\$"])
    if prompt_server == 1:
        return f"No se pudo ingresar al {GET_PE} por CREDENCIALES", 400
    
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
    prompt_pe = child.expect([r"\<\S+\>", r"\]\$", r"\n\S+#"])
    if prompt_pe == 1:
        return f"No se pudo ingresar al PE {ippe_found}", 400
    elif prompt_pe == 2:
        pe_os = "zte"
        pe_protocol = "ssh"
        child.send(f"quit")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\]\$")
        return f"EL {ippe_found} no es Huawei, CID: {cid}", 400
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
    pe_ismascara30 = is_mascara30(pe_ipmascara_found["mascara"])
    if pe_ismascara30:
        newTrafficpolicyInPE  = search_newbw_inPE(child, trafficpolicy_found, newbw, pesubinterface_found, commit)

    
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
    if not pe_ismascara30:
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

    newTrafficpolicyInACCESO = search_newbw_inACCESO(child, trafficpolicy_cliente_found, newbw, interface_cliente_found, commit)

    child.send(f"quit")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"\]\$")

    #

    result = {
        "cid": cid,
        "commit": commit,
        "newBWinMegas": newbw,
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
            "pe_trafficpoliceAnalisys": {
                "pe_upgradeByMascara30": pe_ismascara30,
                "pe_trafficpolicyDetail": newTrafficpolicyInPE if pe_ismascara30 else None,
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
            "acceso_trafficpoliceAnalisys": newTrafficpolicyInACCESO
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


def search_newbw_inPE(child = None, trafficpolicy = None, newbw = None, subinterface=None, commit = "N"):
    result = {}

    if trafficpolicy:
        old_trafficpolicy_inMbps = trafficpolicy[0][0]
        old_trafficpolicy_outMbps = trafficpolicy[1][0]

        trafficpolicy_pattern_input =  re.search("(?P<pre>[a-zA-Z_]*)(?P<bw>\d+)(?P<post>[a-zA-Z_]*)", old_trafficpolicy_inMbps)
        trafficpolicy_pattern_output =  re.search("(?P<pre>[a-zA-Z_]*)(?P<bw>\d+)(?P<post>[a-zA-Z_]*)", old_trafficpolicy_outMbps)

        oldbw_input = int(trafficpolicy_pattern_input.group("bw"))
        oldbw_output = int(trafficpolicy_pattern_output.group("bw"))

        new_trafficpolicy_inMbps = trafficpolicy_pattern_input.group("pre") + f"{newbw}" + trafficpolicy_pattern_input.group("post")
        new_trafficpolicy_outMbps = trafficpolicy_pattern_output.group("pre") + f"{newbw}" + trafficpolicy_pattern_output.group("post")

        # OLD

        # IN OLD
        child.send(f"display curr configuration trafficpolicy {old_trafficpolicy_inMbps} | no-more")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"<[\w\-.]+>")

        output_trafficpolicy_in_old = child.before.decode("utf-8")
        output_classifier_behavior_in_old_pattern = re.search(r'classifier (\S+) behavior ([\w\-.]+) ', output_trafficpolicy_in_old)
        classifier_in_old = output_classifier_behavior_in_old_pattern.group(1)
        behavior_in_old = output_classifier_behavior_in_old_pattern.group(2)

        # OUT OLD
        child.send(f"display curr configuration trafficpolicy {old_trafficpolicy_outMbps} | no-more")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"<[\w\-.]+>")

        output_trafficpolicy_out_old = child.before.decode("utf-8")
        output_classifier_behavior_out_old_pattern = re.search(r'classifier (\S+) behavior ([\w\-.]+) ', output_trafficpolicy_out_old)
        classifier_out_old = output_classifier_behavior_out_old_pattern.group(1)
        behavior_out_old = output_classifier_behavior_out_old_pattern.group(2)

        # NEW

        behavior_in = None
        behavior_out = None
        traffic_in = None
        traffic_out = None

        # IN NEW
        child.send(f"display curr configuration trafficpolicy {new_trafficpolicy_inMbps} | no-more")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"<[\w\-.]+>")

        output_behavior_in = child.before.decode("utf-8")
        output_behavior_pattern_in = re.search(r'classifier \S+ behavior ([\w\-.]+) ', output_behavior_in)
        if output_behavior_pattern_in:
            behavior_in = output_behavior_pattern_in.group(1)

            child.send(f"display curr configuration behavior {behavior_in} | no-more")
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"<[\w\-.]+>")

            output_traffic_in = child.before.decode("utf-8")
            output_traffic_pattern_in = re.search(r"car cir (\d+) ", output_traffic_in)
            if output_traffic_pattern_in:
                traffic_in = int(output_traffic_pattern_in.group(1))
        
        # OUT NEW
        child.send(f"display curr configuration trafficpolicy {new_trafficpolicy_outMbps} | no-more")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"<[\w\-.]+>")

        output_behavior_out = child.before.decode("utf-8")
        output_behavior_pattern_out = re.search(r'classifier \S+ behavior ([\w\-.]+) ', output_behavior_out)
        if output_behavior_pattern_out:
            behavior_out = output_behavior_pattern_out.group(1)

            child.send(f"display curr configuration behavior {behavior_out} | no-more")
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"<[\w\-.]+>")

            output_traffic_out = child.before.decode("utf-8")
            output_traffic_pattern_out = re.search(r"car cir (\d+) ", output_traffic_out)
            if output_traffic_pattern_out:
                traffic_out = int(output_traffic_pattern_out.group(1))


        result["old_BWInMegas"] = oldbw_input
        result["old_BWOutMegas"] = oldbw_output
        result["old_trafficpolicy_inMbps"] = old_trafficpolicy_inMbps
        result["old_classifier_in"] = classifier_in_old
        result["old_behavior_in"] = behavior_in_old
        result["old_trafficpolicy_outMbps"] = old_trafficpolicy_outMbps
        result["old_classifier_out"] = classifier_out_old
        result["old_behavior_out"] = behavior_out_old

        result["new_trafficpolicy_inMbps"] = new_trafficpolicy_inMbps
        result["new_trafficpolicy_outMbps"] = new_trafficpolicy_outMbps
        if traffic_in == newbw * 1024:
            result["new_trafficpolicy_in_iscreated"] = True
        else:
            result["new_trafficpolicy_in_iscreated"] = False

        if traffic_out == newbw * 1024:
            result["new_trafficpolicy_out_iscreated"] = True
        else:
            result["new_trafficpolicy_out_iscreated"] = False

        result["new_trafficpolicy_commands"] = trafficpolicy_configurationInPE(
            new_trafficpolicy_inMbps, 
            new_trafficpolicy_outMbps, 
            newbw, 
            classifier_in_old, 
            classifier_out_old, 
            subinterface,
            result["new_trafficpolicy_in_iscreated"],
            result["new_trafficpolicy_out_iscreated"],
        )

        # result["session_inPE"] = configuration_inHuawei(child, result["new_trafficpolicy_commands"], commit)

        return result
    else:
        return None
    

def configuration_inHuawei(child, commands, commit):
    result = []
    prompt = child.after.decode("utf-8")
    child.send(f"system-view")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"\[\S+\]")
    comando = child.before.decode("utf-8")
    result.append(prompt + comando)

    for command in commands:
        prompt = child.after.decode("utf-8")
        child.send(command)
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\[\S+\]")
        comando = child.before.decode("utf-8")
        result.append(prompt + comando)

    prompt = child.after.decode("utf-8")
    child.send("quit")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    index = child.expect([r"\[Y\(yes\)\/N\(no\)\/C\(cancel\)\]:", r"<[\w\-.]+>"])
    comando = child.before.decode("utf-8")
    result.append(prompt + comando)
    prompt = child.after.decode("utf-8")
    if index == 0:
        child.send(commit)
    else:
        child.send(" ")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"<[\w\-.]+>")
    comando = child.before.decode("utf-8")
    result.append(prompt + comando)
    prompt = child.after.decode("utf-8")
    child.send(" ")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"<[\w\-.]+>")
    comando = child.before.decode("utf-8")
    result.append(prompt + comando)
    
    result = "".join(result)
    result = result.split("\r\n")
    return result
    

def trafficpolicy_configurationInPE(trafficpolicy_in, trafficpolicy_out, bw, classifier_in, classifier_out, subinterface, in_iscreated, out_iscreated):
    
    result = []

    if not in_iscreated:
        result.extend(
            [
                f"traffic behavior {trafficpolicy_in}",
                f" car cir {bw * 1024}",
                f" quit",

                f"traffic policy {trafficpolicy_in}",
                f" undo share-mode",
                f" statistics enable",
                f" classifier {classifier_in} behavior {trafficpolicy_in} precedence 1",
                f" quit",
            ]
        )

    if not out_iscreated:
        result.extend(
            [
                f"traffic behavior {trafficpolicy_out}",
                f" car cir {bw * 1024}",
                f" quit",
                
                f"traffic policy {trafficpolicy_out}",
                f" undo share-mode",
                f" statistics enable",
                f" classifier {classifier_out} behavior {trafficpolicy_out} precedence 1",
                f" quit",
            ]
        )

    result.extend(
        [
            f"interface {subinterface}",
            f" undo traffic-policy inbound",
            f" undo traffic-policy outbound",
            f" traffic-policy {trafficpolicy_in} inbound",
            f" traffic-policy {trafficpolicy_out} outbound",
            f" quit",
        ]
    )

    return result


def search_newbw_inACCESO(child=None, trafficpolicy = None, newbw = None, subinterface=None, commit="N"):
    result = {}
    byInterfaceIn = False
    byInterfaceOut = False
    trafficpolicy_in_new = None
    trafficpolicy_out_new = None
    newbw_inKbps = newbw * 1024
    newbw_outKbps = newbw * 1024
    cbs_pbs = int((newbw_inKbps / 8) * 1.5 * 1000)

    if trafficpolicy:
        old_trafficpolicy_inMbps = trafficpolicy[0][0]
        old_trafficpolicy_outMbps = trafficpolicy[1][0]

        # OLD
        # IN OLD
        child.send(f"display curr configuration trafficpolicy {old_trafficpolicy_inMbps}")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"<[\w\-.]+>")
        output_trafficpolicy_in_old = child.before.decode("utf-8")
        output_classifier_behavior_in_old_pattern = re.search(r'classifier (\w+) behavior (\w+)', output_trafficpolicy_in_old)
        classifier_in_old = output_classifier_behavior_in_old_pattern.group(1)
        behavior_in_old = output_classifier_behavior_in_old_pattern.group(2)

        # OUT OLD
        child.send(f"display curr configuration trafficpolicy {old_trafficpolicy_outMbps}")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"<[\w\-.]+>")
        output_trafficpolicy_out_old = child.before.decode("utf-8")
        output_classifier_behavior_out_old_pattern = re.search(r'classifier (\w+) behavior (\w+)', output_trafficpolicy_out_old)
        classifier_out_old = output_classifier_behavior_out_old_pattern.group(1)
        behavior_out_old = output_classifier_behavior_out_old_pattern.group(2)

        # NEW
        behavior_in_newNow = None
        behavior_out_newNow = None
        carcir_in_newNow = False
        carcir_out_newNow = False
        new_trafficpolicy_in_iscreated = False
        new_trafficpolicy_out_iscreated = False

        # Si la nomenclatura es por interface o Kbps
        if re.search("(\d+\/\d+\/\d+)", old_trafficpolicy_inMbps):
            byInterfaceIn = True
            trafficpolicy_in_new = old_trafficpolicy_inMbps
        else:
            trafficpolicy_in_new = re.sub("\d+", f"{newbw_inKbps}", old_trafficpolicy_inMbps)

        if re.search("(\d+\/\d+\/\d+)", old_trafficpolicy_outMbps):
            byInterfaceOut = True
            trafficpolicy_out_new = old_trafficpolicy_outMbps
        else:
            trafficpolicy_out_new = re.sub("\d+", f"{newbw_outKbps}", old_trafficpolicy_outMbps)
        
        behavior_in_new = re.sub("\d+", f"{newbw_inKbps}", behavior_in_old)
        behavior_out_new = re.sub("\d+", f"{newbw_outKbps}", behavior_out_old)

        # IN NEW
        child.send(f"display curr configuration trafficpolicy {trafficpolicy_in_new}")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"<[\w\-.]+>")
        output_behavior_in = child.before.decode("utf-8")
        output_trafficpolicy_in_pattern = re.search(rf'traffic policy {trafficpolicy_in_new}', output_behavior_in)
        if output_trafficpolicy_in_pattern:
            new_trafficpolicy_in_iscreated = True

        output_behavior_pattern_in = re.search(r'classifier \S+ behavior ([\w\-.]+)', output_behavior_in)
        if output_behavior_pattern_in:
            behavior_in_newNow = output_behavior_pattern_in.group(1)
            
            child.send(f"display curr configuration behavior {behavior_in_newNow}")
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"<[\w\-.]+>")
            output_carcir_in = child.before.decode("utf-8")
            output_carcir_pattern_in = re.search(rf"car cir {newbw_inKbps} pir {newbw_inKbps} cbs {cbs_pbs} pbs {cbs_pbs} ", output_carcir_in)
            if output_carcir_pattern_in:
                carcir_in_newNow = True
                

        # OUT NEW
        child.send(f"display curr configuration trafficpolicy {trafficpolicy_out_new}")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"<[\w\-.]+>")
        output_behavior_out = child.before.decode("utf-8")
        output_trafficpolicy_out_pattern = re.search(rf'traffic policy {trafficpolicy_out_new}', output_behavior_out)
        if output_trafficpolicy_out_pattern:
            new_trafficpolicy_out_iscreated = True
        output_behavior_pattern_out = re.search(r'classifier \S+ behavior ([\w\-.]+)', output_behavior_out)
        if output_behavior_pattern_out:
            behavior_out_newNow = output_behavior_pattern_out.group(1)

            child.send(f"display curr configuration behavior {behavior_out_newNow}")
            time.sleep(TIME_SLEEP)
            child.sendline("")
            child.expect(r"<[\w\-.]+>")
            output_carcir_out = child.before.decode("utf-8")
            output_carcir_pattern_out = re.search(rf"car cir {newbw_outKbps} pir {newbw_outKbps} cbs {cbs_pbs} pbs {cbs_pbs} ", output_carcir_out)
            if output_carcir_pattern_out:
                carcir_out_newNow = True
                
        # 
        child.send(f"display current-configuration | inc traffic policy")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"<[\w\-.]+>")
        output_trafficpolicyAll = child.before.decode("utf-8")
        output_trafficpolicyAll_pattern = re.findall(f"traffic policy (\S+) match-order config", output_trafficpolicyAll)
        trafficpolicyAll = len(output_trafficpolicyAll_pattern)
        addNewPolicyTraffic = True if trafficpolicyAll <= 254 else False

        values_for_commands = {
            "subinterface": subinterface,
            "old_classifier_in" : classifier_in_old,
            "old_classifier_out" : classifier_out_old,
            "new_trafficpolicy_in": trafficpolicy_in_new,
            "new_behavior_in" : behavior_in_new,
            "new_trafficpolicy_out": trafficpolicy_out_new,
            "new_behavior_out": behavior_out_new,
            "new_trafficpolicy_in_iscreated": new_trafficpolicy_in_iscreated,
            "new_trafficpolicy_out_iscreated": new_trafficpolicy_out_iscreated,
            "new_behavior_in_newNow": behavior_in_newNow,
            "new_behavior_out_newNow": behavior_out_newNow,
            "new_bwKbps": newbw_inKbps,
            "cbs_pbs": cbs_pbs,
            "old_trafficpoliceByInterface_in": byInterfaceIn,
            "old_trafficpoliceByInterface_out": byInterfaceOut,
            "carcir_in_newNow": carcir_in_newNow,
            "carcir_out_newNow": carcir_out_newNow,
            "addNewPolicyTraffic": addNewPolicyTraffic
        }

        result["old_trafficpolicy_in"] = old_trafficpolicy_inMbps
        result["old_trafficpoliceByInterface_in"] = byInterfaceIn
        result["old_classifier_in"] = classifier_in_old
        result["old_behavior_in"] = behavior_in_old
        result["old_trafficpolicy_out"] = old_trafficpolicy_outMbps
        result["old_trafficpoliceByInterface_out"] = byInterfaceOut
        result["old_classifier_out"] = classifier_out_old
        result["old_behavior_out"] = behavior_out_old
        result["new_trafficpolicy_in"] = trafficpolicy_in_new
        result["new_behavior_in"] = behavior_in_new
        result["new_trafficpolicy_out"] = trafficpolicy_out_new
        result["new_behavior_out"] = behavior_out_new
        result["new_trafficpolicy_in_iscreated"] = new_trafficpolicy_in_iscreated
        result["new_trafficpolicy_out_iscreated"] = new_trafficpolicy_out_iscreated
        result["new_behavior_in_newNow"] = behavior_in_newNow
        result["new_behavior_out_newNow"] = behavior_out_newNow
        result["carcir_in_newNow"] = carcir_in_newNow
        result["carcir_out_newNow"] = carcir_out_newNow
        result["numberOfPolicytraffic"] = trafficpolicyAll
        result["addNewPolicyTraffic"] = addNewPolicyTraffic
        result["new_trafficpolicy_commands"] = trafficpolicy_configurationInACCESO(**values_for_commands)
        # result["session_inACCESO"] = configuration_inHuawei(child, [], commit)
        return result
    else:
        return None
    


def trafficpolicy_configurationInACCESO(**kwargs):
    result = []

    if not kwargs["addNewPolicyTraffic"]:
        return result

    if not kwargs["carcir_in_newNow"]:
        result.extend(
            [
                "traffic behavior {behavior}".format(behavior=kwargs["new_behavior_in"]),
                " remark dscp default",
                " car cir {bw} pir {bw} cbs {cbs_pbs} pbs {cbs_pbs} green pass yellow pass red discard".format(bw=kwargs["new_bwKbps"], cbs_pbs=kwargs["cbs_pbs"]),
                " statistic enable",
                " quit",
            ]
        )

    if not kwargs["carcir_out_newNow"]:
        result.extend(
            [
                "traffic behavior {behavior}".format(behavior=kwargs["new_behavior_out"]),
                " remark dscp default",
                " car cir {bw} pir {bw} cbs {cbs_pbs} pbs {cbs_pbs} green pass yellow pass red discard".format(bw=kwargs["new_bwKbps"], cbs_pbs=kwargs["cbs_pbs"]),
                " statistic enable",
                " quit",
            ]
        )

    if not kwargs["new_trafficpolicy_in_iscreated"] or not kwargs["carcir_in_newNow"]:
        result.extend(
            [
                "traffic policy {trafficpolice}".format(trafficpolice=kwargs["new_trafficpolicy_in"]),
                " classifier {classifier} behavior {behavior}".format(classifier=kwargs["old_classifier_in"], behavior=kwargs["new_behavior_in"]),
                " quit",
            ]
        )

    if not kwargs["new_trafficpolicy_out_iscreated"] or not kwargs["carcir_out_newNow"]:
        result.extend(
            [
                "traffic policy {trafficpolice}".format(trafficpolice=kwargs["new_trafficpolicy_out"]),
                " classifier {classifier} behavior {behavior}".format(classifier=kwargs["old_classifier_out"], behavior=kwargs["new_behavior_out"]),
                " quit",
            ]
        )

    result.extend(
        [
            "interface {subinterface}".format(subinterface=kwargs["subinterface"]),
            " undo traffic-policy inbound",
            " undo traffic-policy outbound",
            " traffic-policy {trafficpolicy_in} inbound".format(trafficpolicy_in=kwargs["new_trafficpolicy_in"]),
            " traffic-policy {trafficpolicy_out} outbound".format(trafficpolicy_out=kwargs["new_trafficpolicy_out"]),
            " quit",
        ]
    ) 

    return result