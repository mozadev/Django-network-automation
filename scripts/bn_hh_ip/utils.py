import pexpect
import os
import time

def to_router(cid):
    TACASTS_USER = os.getenv("TACASTS_USER")
    TACASTS_PASS = os.getenv("TACASTS_PASS")
    CYBERARK_USER = os.getenv("CYBERARK_USER")
    CYBERARK_PASS = os.getenv("CYBERARK_PASS")
    CYBERARK_IP = os.getenv("CYBERARK_IP")
    CRT_IP = os.getenv("CRT_IP")
    CRT_USER = os.getenv("CRT_USER")
    TIME_SLEEP = 1.5


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
        child.send(f"hh {cid} | tail -1 | awk \'{{print $1}}\'")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        time.sleep(TIME_SLEEP)
        # Saliendo
        child.expect("\$")
        time.sleep(TIME_SLEEP)
        child.send("exit")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.close()
    except pexpect.TIMEOUT:
        print("ERROR")

