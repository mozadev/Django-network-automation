import pexpect
import os
import time
from commands import commands_to_huawei

def to_router(pe, sub_interface):
    TACASTS_USER = os.getenv("TACASTS_USER")
    TACASTS_PASS = os.getenv("TACASTS_PASS")
    CYBERARK_USER = os.getenv("CYBERARK_USER")
    CYBERARK_PASS = os.getenv("CYBERARK_PASS")
    CYBERARK_IP = os.getenv("CYBERARK_IP")
    CRT_IP = os.getenv("CRT_IP")
    CRT_USER = os.getenv("CRT_USER")
    TIME_SLEEP = 0.1
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

        for command in commands_to_huawei(sub_interface):
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
    except pexpect.TIMEOUT:
        print("ERROR")
