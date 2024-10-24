import pexpect
import os
from dotenv import load_dotenv
from datetime import datetime
import time
import re

# GLOBAL VARIABLES
TIME_SLEEP = 0.1


def to_server(user_tacacs, pass_tacacs, cid_list, ip_owner, commit):
    load_dotenv()
    TACASTS_USER = user_tacacs
    TACASTS_PASS = pass_tacacs
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

    except:
        return
    
    print(result)
    return 


def to_router(child, user_tacacs, pass_tacacs, cid, commit):
    wan_found = None
    ippe_found = None
    pesubinterface_found = None
    trafficpolicy_found = None

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
    child.expect(r"\<.*\>")
    
    child.send(f"display ip routing-table {wan_found}")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"\<.*\>")
    output_ippe = child.before.decode("utf-8")
    ippe_pattern = re.search(r' +(\d+\.\d+\.\d+\.\d+) +', output_ippe)
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
    child.expect("[Pp]assword:")
    child.send(pass_tacacs)
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"\<.*\>")

    child.send(f"display ip routing-table {wan_found}")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"\<.*\>")

    output_pesubinterface = child.before.decode("utf-8")
    pesubinterface_pattern = re.search(r'(\S*Eth\S*)', output_pesubinterface)
    if pesubinterface_pattern:
        pesubinterface_found = pesubinterface_pattern.group(1)
    else:
        child.send(f"quit")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\]\$")

        return f"SUBINTERFACE DEL PE {ippe_found} del CID {cid} no encontrado", 400
 
    child.send(f"display curr int {pesubinterface_found}")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"\<\S+\>")
    time.sleep(TIME_SLEEP)

    output_trafficpolicy = child.before.decode("utf-8")
    print(output_trafficpolicy)
    trafficpolicy_pattern = re.findall(r'traffic-policy (\S+)', output_trafficpolicy)
    if len(trafficpolicy_pattern) > 0:
        trafficpolicy_found = trafficpolicy_pattern
    else:
        child.send(f"quit")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect(r"\]\$")

        return f"traffic-policy NO ENCONTRADO EN SUBINTERFACE DEL PE {ippe_found} del CID {cid} no encontrado", 400
    

    child.send(f"quit")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"\]\$")

    return f"EXITO {cid} {wan_found}", 200