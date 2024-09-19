import pexpect
import os
import time
from commands import commands_to_cisco, commands_to_teldat

def to_router(cid):
    TACASTS_USER = os.getenv("TACASTS_USER")
    TACASTS_PASS = os.getenv("TACASTS_PASS")
    CYBERARK_USER = os.getenv("CYBERARK_USER")
    CYBERARK_PASS = os.getenv("CYBERARK_PASS")
    CYBERARK_IP = os.getenv("CYBERARK_IP")
    CRT_IP = os.getenv("CRT_IP")
    CRT_USER = os.getenv("CRT_USER")
    TIME_SLEEP = 1.75


    try:
        # Ingreso al Cyberark
        child = pexpect.spawn(f"ssh -o StrictHostKeyChecking=no {CYBERARK_USER}@{CYBERARK_IP}", timeout=30)
        child.logfile = open(f"media/{cid}.log", "wb")
        child.expect("[Pp]assword:")
        child.sendline(CYBERARK_PASS)
        child.expect(f"user:")
        child.sendline(CRT_USER)
        child.expect(f"address:")
        child.sendline(CRT_IP)
        # Obteniendo el IP
        child.expect("\$")
        time.sleep(TIME_SLEEP)
        child.send(f"router=$(hh {cid} | tail -1 | awk \'{{print $1}}\')")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        time.sleep(TIME_SLEEP)
        child.expect("\$")
        time.sleep(TIME_SLEEP)
        # Ingresando al router Cisco
        child.send("telnet $router")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.expect("[Uu]sername:")
        child.sendline(TACASTS_USER)
        child.expect("[Pp]assword:")
        child.sendline(TACASTS_PASS)
        # Dentro del router
        tipo_router = child.expect(["\#", "\s\*", "\>", pexpect.EOF, pexpect.TIMEOUT])
        if tipo_router in [0, 2]:
            # Dentro del router Cisco
            if tipo_router == 2:
                # Aplicar primero enable
                time.sleep(TIME_SLEEP)
                child.send("enable")
                child.sendline("")
                child.expect("[Pp]assword:")
                time.sleep(TIME_SLEEP)
                child.send(TACASTS_PASS)
                time.sleep(TIME_SLEEP)
                child.sendline("")

            time.sleep(TIME_SLEEP)
            child.sendline("")
            for command in commands_to_cisco():
                time.sleep(TIME_SLEEP)
                child.expect(command["prompt"])
                time.sleep(TIME_SLEEP)
                child.send(command["command"])
                time.sleep(TIME_SLEEP)
                child.sendline("")
                
            child.send("exit")
            time.sleep(TIME_SLEEP)
            child.sendline("")
        elif tipo_router == 1:
            # Dentro del router Teldat
            time.sleep(TIME_SLEEP)
            child.sendline("")
            for command in commands_to_teldat():
                time.sleep(TIME_SLEEP)
                child.expect(command["prompt"])
                time.sleep(TIME_SLEEP)
                child.send(command["command"])
                time.sleep(TIME_SLEEP)
                child.sendline("")

            time.sleep(TIME_SLEEP)
            child.send("logout")
            time.sleep(TIME_SLEEP)
            child.sendline("")
            time.sleep(TIME_SLEEP)
            child.expect("\?")
            time.sleep(TIME_SLEEP)
            child.send("yes")
            time.sleep(TIME_SLEEP)
            child.sendline("")
        else:
            child.close()
            print("Error: Otro equipo")

        child.expect("\$")
        time.sleep(TIME_SLEEP)
        child.send("exit")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.close()
    except pexpect.TIMEOUT:
        print("ERROR")

