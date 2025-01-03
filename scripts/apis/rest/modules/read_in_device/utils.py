import pandas as pd
import ipaddress
import pexpect
from dotenv import load_dotenv
import os
from datetime import datetime
import time

TIME_SLEEP = 0.1

def list_of_ip(excel):
    data = pd.read_excel(excel, usecols=["ip"])
    data['is_valid'] = data["ip"].apply(is_valid_ipv4)
    if not data["is_valid"].all() :
        raise IPv4NotValidas("Se encontraron IPv4 no válidas", 500)
    
    result = data.to_dict(orient="records")
    return result


def is_valid_ipv4(ip):
    try:
        return isinstance(ipaddress.ip_address(ip), ipaddress.IPv4Address)
    except (ValueError, TypeError):
        return False


class IPv4NotValidas(Exception):
    def __init__(self, msg, code):
        super().__init__(msg)
        self.code = code


class NotEnterToDevice(Exception):
    def __init__(self, msg, code):
        super().__init__(msg)
        self.code = code


class EnterToCRT(object):
    def __init__(self, ruta,timeout=30):
        load_dotenv(override=True)
        self.username = os.getenv("CYBERARK_USER")
        self.password = os.getenv("CYBERARK_PASS")
        self.ip = os.getenv("CYBERARK_IP")
        self.crt_ip = os.getenv("CRT_IP")
        self.crt_user = os.getenv("CRT_USER")
        self.name_file = ruta + "/" + f'{datetime.now().strftime("%Y%m%d%H%M%S")}.txt'
        self.timeout = timeout
    
    def enter(self, ):
        self.child = pexpect.spawn(f"ssh -o StrictHostKeyChecking=no {self.username}@{self.ip}", timeout=self.timeout)
        self.child.logfile = open(self.name_file, "wb")
        self.child.expect("[Pp]assword:")
        self.child.sendline(self.password)
        self.child.expect(f"user:")
        self.child.sendline(self.crt_user)
        self.child.expect(f"address:")
        self.child.sendline(self.crt_ip)
        self.child.expect(r"\]\$")
        return self.child
    
    def exit(self, ):
        self.child.close()
        return None
    

class EnterToDevice(object):
    def __init__(self, child, username, password, ip):
        self.child = child
        self.username = username
        self.password = password
        self.ip = ip
    
    def enter(self,):
        self.child.send(f"telnet {self.ip}")
        time.sleep(TIME_SLEEP)
        self.child.sendline("")
        input_username = self.child.expect([r"[Uu]sername:", r"\]\$"])
        if input_username == 1:
            raise NotEnterToDevice(f"DISPOSITIVO {self.ip} SIN GESTIÓN", 500)
        
        self.child.send(self.username)
        time.sleep(TIME_SLEEP)
        self.child.sendline("")
        input_password = self.child.expect([r"[Pp]assword:", r"[Uu]sername:"])
        if input_password == 1:
            raise NotEnterToDevice(f"CREDENCIALES EN EL DEVICE {self.ip} FALLIDAS", 500)
        
        self.child.send(self.password)
        self.child.sendline("")
        time.sleep(TIME_SLEEP)
        self.child.expect(r"\s<[\w\-.]+>")
        self.child.send(f"screen-length 0 temporary")
        time.sleep(TIME_SLEEP)
        self.child.sendline("")
        self.child.expect(r"\s<[\w\-.]+>")
        return self.child
    
    def send_command(self, command):
        self.child.send(command)
        time.sleep(TIME_SLEEP)
        self.child.sendline("")
        self.child.expect(r"\s<[\w\-.]+>")
        return self.child

    def send_enter(self, ):
        self.child.send(" ")
        time.sleep(TIME_SLEEP)
        self.child.sendline("")
        self.child.expect(r"\s<[\w\-.]+>")
        return self.child


def session_in_device(user_tacacs, pass_tacacs, list_of_ip, commands):
    sessionCRT = EnterToCRT("media/read_in_device", )
    terminal_crt = sessionCRT.enter()
    for device in list_of_ip:
        terminal_device = EnterToDevice(terminal_crt, user_tacacs, pass_tacacs, device["ip"])
        terminal_device.enter()
        for command in commands:
            terminal_device.send_command(command)
            terminal_device.send_enter()
    sessionCRT.exit()
    return
