import pexpect
import os
from dotenv import load_dotenv
import re
from datetime import datetime
import time

# GLOBAL VARIABLES
TIME_SLEEP = 0.1

def to_router(list_ip_gestion, link):
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
            to_switch(child, user_tacacs, pass_tacacs, ip)
            time.sleep(5)
        child.send("exit")
        time.sleep(TIME_SLEEP)
        child.sendline("")
        child.close()

        return
    except pexpect.ExceptionPexpect:
        return 400, {"msg": "ERROR", "file": url_txt}


def to_switch(child, user_tacacs, pass_tacacs, ip):

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

    prompt_server = child.expect([r"\<\S+\>", r"\]\$"])
    if prompt_server == 1:
        return []

    child.send(f"display interface brief | no-more")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"\<\S+\>")
    interface_output = child.before.decode("utf-8")
    interface_pattern = re.findall(r' *(\S+) +\*?\b(up|down)\b +\*?\b(up|down)\b', interface_output)

    child.send(f"quit")
    time.sleep(TIME_SLEEP)
    child.sendline("")
    child.expect(r"\]\$")    
    return interface_pattern