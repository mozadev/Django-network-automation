import pandas as pd
import ipaddress
import pexpect
from dotenv import load_dotenv
import os
from datetime import datetime
import time
import zipfile
import re

TIME_SLEEP = 0.1

def list_of_ip(excel):
    data = pd.read_excel(excel, usecols=["ip"])
    data['is_valid'] = data["ip"].str.strip().apply(is_valid_ipv4)
    if not data["is_valid"].all() :
        ejemplo = data[data["is_valid"] == False].iloc[0, 0]
        raise IPv4NotValidas(f"Se encontraron IPv4 no válidas, por ejemplo : {ejemplo}", 500)
    
    result = data.to_dict(orient="records")
    return result


def is_valid_ipv4(ip):
    try:
        return isinstance(ipaddress.ip_address(ip), ipaddress.IPv4Address)
    except (ValueError, TypeError):
        return False


def run_step(child, command, expected_output, step_name, timeout, device):
    try:
        child.send(command)
        child.sendline("")
        time.sleep(TIME_SLEEP)
        child.expect(expected_output, timeout=timeout)
    except pexpect.TIMEOUT:
        raise CustomPexpectError(step_name, "Se agotó el tiempo de espera", 500, device)
    except pexpect.EOF:
        raise CustomPexpectError(step_name, "El proceso terminó de manera inesperada", 500, device)
    except Exception as e:
        raise CustomPexpectError(step_name, f"Error Inesperado: {str(e)}", 500, device)
    

class CustomPexpectError(Exception):
    def __init__(self, step, message, code, device):
        super().__init__(f"ERROR en el paso '{step}' del device {device}: {message}")
        self.step = step
        self.code = code
        self.device = device


class IPv4NotValidas(Exception):
    def __init__(self, msg, code):
        super().__init__(msg)
        self.code = code


class NotEnterToDevice(Exception):
    def __init__(self, msg, code):
        super().__init__(msg)
        self.code = code


class EnterToCRT(object):
    def __init__(self, ruta,timeout=5):
        load_dotenv(override=True)
        self.username = os.getenv("CYBERARK_USER")
        self.password = os.getenv("CYBERARK_PASS")
        self.ip = os.getenv("CYBERARK_IP")
        self.crt_ip = os.getenv("CRT_IP")
        self.crt_user = os.getenv("CRT_USER")
        self.ruta = ruta + "/" + f'{datetime.now().strftime("%Y%m%d%H%M%S")}'
        os.makedirs(self.ruta, exist_ok=True)
        self.name_file = self.ruta + "/session.log" 
        self.timeout = timeout
        self.ls_txt = []
    
    def enter(self, ):
        try:
            self.child = pexpect.spawn(f"ssh -o StrictHostKeyChecking=no {self.username}@{self.ip}", timeout=self.timeout)
            self.child.logfile = open(self.name_file, "wb")
            self.child.expect("[Pp]assword:")

            run_step(child=self.child, command=self.password, expected_output=f"user:", step_name="Password", timeout=self.timeout, device="CRT")
            run_step(child=self.child, command=self.crt_user, expected_output=f"address:", step_name="Address CRT", timeout=self.timeout, device="CRT")
            run_step(child=self.child, command=self.crt_ip, expected_output=r"\]\$", step_name="IP CRT", timeout=self.timeout, device="CRT")

            return self.child
        except CustomPexpectError as e:
            return e
    
    def exit(self, ):
        self.child.close()
        return None
    

    def listar_txt(self,):
        self.ls_txt = [i for i in os.listdir(self.ruta) if re.search("\.txt$", i)]

    def comprimir_session(self, zipfile_name):
        self.zipfile_name = self.ruta + "/" + zipfile_name
        with zipfile.ZipFile(self.zipfile_name, "w") as zipf:
            for fichero in self.ls_txt:
                path_file = self.ruta + "/" + fichero
                zipf.write(path_file, os.path.basename(path_file))

    

class EnterToDevice(object):
    def __init__(self, child, username, password, ip):
        self.child = child
        self.username = username
        self.password = password
        self.ip = ip
        self.session = []
        self.path_file = None
    
    def enter(self,):
        try:
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
            time.sleep(TIME_SLEEP * 2)
            self.child.sendline("")
            self.child.expect(r"\s<[\w\-.]+>")
        except NotEnterToDevice as e:
            return e
        except pexpect.TIMEOUT as e:
            return NotEnterToDevice(f"TIEMPO EXCEDIO DE ESPERA DEL DEVICE {self.ip}", 500)
        except pexpect.EOF as e:
            return NotEnterToDevice(f"NO HAY MÁS COMANDOS PARA EJECUTAR {self.ip}", 500)
        except Exception as e:
            return e
        else:
            return self.child
    
    def send_command(self, command):
        prompt_output = self.child.after.decode("utf-8")
        self.child.send(command)
        time.sleep(TIME_SLEEP)
        self.child.sendline("")
        self.child.expect(r"\s<[\w\-.]+>")
        comando_output = self.child.before.decode("utf-8")
        self.session.append(prompt_output + comando_output)
        return self.child

    def send_enter(self, ):
        prompt_output = self.child.after.decode("utf-8")
        self.child.send(" ")
        time.sleep(TIME_SLEEP)
        self.child.sendline("")
        self.child.expect(r"\s<[\w\-.]+>")
        comando_output = self.child.before.decode("utf-8")
        self.session.append(prompt_output + comando_output)
        return self.child
    
    def get_session(self,):
        self.session = "".join(self.session)
        self.session = self.session.split("\r\n")
        return self.session
    
    def save_session(self, file):
        self.path_file = file
        with open(self.path_file, "w") as file:
            for line in self.session:
                file.write(f"{line}\n")


def session_in_device(user_tacacs, pass_tacacs, list_of_ip, commands):
    try:
        result = []
        sessionCRT = EnterToCRT("media/read_in_device", timeout=30)
        terminal_crt = sessionCRT.enter()
        if isinstance(terminal_crt, CustomPexpectError): raise terminal_crt
        for device in list_of_ip:
            item = {}
            try:
                terminal_device = EnterToDevice(terminal_crt, user_tacacs, pass_tacacs, device["ip"])
                terminal_device_status = terminal_device.enter()
                if isinstance(terminal_device_status, NotEnterToDevice): raise terminal_device_status
                for command in commands:
                    terminal_device.send_command(command)
                    terminal_device.send_enter()
                terminal_device.get_session()
                terminal_device.save_session(sessionCRT.ruta + "/" + f'{device["ip"]}.txt')

            except NotEnterToDevice as e:
                item["code"] = e.code
                item["detail"] = str(e)
                item["IPv4"] = device["ip"]
            else:
                item["code"] = 200
                item["detail"] = "EXITOSO"
                item["IPv4"] = device["ip"]
            finally:
                result.append(item)
        sessionCRT.listar_txt()
        sessionCRT.comprimir_session("session.zip")
        sessionCRT.exit()
        return result
    except CustomPexpectError as e:
        return e

