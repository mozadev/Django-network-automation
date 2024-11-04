import pexpect
import os
import time
from rest.modules.suspension.commands import commands_to_huawei
from dotenv import load_dotenv


def to_router(action, user_tacacs, pass_tacacs, pe, sub_interface, suspension, commit):
    load_dotenv(override=True)
    action = "suspension" if suspension else "reconnection"
    TACASTS_USER = user_tacacs
    TACASTS_PASS = pass_tacacs
    CYBERARK_USER = os.getenv("CYBERARK_USER")
    CYBERARK_PASS = os.getenv("CYBERARK_PASS")
    CYBERARK_IP = os.getenv("CYBERARK_IP")
    CRT_IP = os.getenv("CRT_IP")
    CRT_USER = os.getenv("CRT_USER")
    TIME_SLEEP = 0.1
    interface_log = sub_interface.replace("/", "_")
    name_file= f"media/{action}_{pe}_{interface_log}.txt"
    url_file = f"http://10.200.90.248:9000/{name_file}"

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

        for command in commands_to_huawei(sub_interface, suspension, commit):
            print(command["command"])
            continue
            time.sleep(TIME_SLEEP)
            child.expect(command["prompt"])
            time.sleep(TIME_SLEEP)
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
        return f"EXITOSO: ", 200, url_file
    except pexpect.TIMEOUT:
        return f"ERROR: el Servidor/Router no responden ó las tacas están mal", 400, url_file
