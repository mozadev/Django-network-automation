import pandas as pd
import pexpect
from datetime import datetime
import time
import os
from dotenv import load_dotenv
import re
from django.core.mail import EmailMessage
import zipfile
from jinja2 import Environment, FileSystemLoader
import csv


TIME_SLEEP = 0.2
PROMP_HUAWEI = r"\n<[\w\-. \(\)]+>$"
PROMP_CISCO = r"\s[\w\-. \(\)]+#$"
PROMP_CISCO_SHOW = r"\s[\w\-. \(\)]+>$"
PROMP_CRT = r"~\]\$\s*$"


def list_of_cid(excel):
    data = pd.read_excel(excel, usecols=["cid"])
    data["is_number"] = data["cid"].apply(is_number)
    if not data["is_number"].all():
        ejemplo = data[data["is_number"] == False].iloc[0, 0]
        raise Exception(f"Se encontraron CIDs no válidos en: {ejemplo}")
    result = data.to_dict(orient="records")
    return result

def is_number(x):
    try:
        float(x)
        return True
    except ValueError:
        return False


class CustomPexpectError(Exception):
    def __init__(self, step, message, code, device):
        super().__init__(f"ERROR en el paso '{step}' del device {device}: {message}")
        self.step = step
        self.code = code
        self.device = device


class NotEnterToDevice(Exception):
    def __init__(self, msg, code):
        super().__init__(msg)
        self.code = code



def run_step(child, command, expected_output, step_name, timeout, device):
    try:
        index = None
        child.send(command)
        child.sendline("")
        time.sleep(TIME_SLEEP)
        if isinstance(expected_output, str):
            child.expect(expected_output, timeout=timeout)
        elif isinstance(expected_output, list):
            index = child.expect(expected_output, timeout=timeout)
        else:
            raise TypeError("Solo se aceptan 'str' y 'list'")

    except pexpect.TIMEOUT:
        raise CustomPexpectError(step_name, "Se agotó el tiempo de espera", 500, device)
    except pexpect.EOF:
        raise CustomPexpectError(step_name, "El proceso terminó de manera inesperada", 500, device)
    except Exception as e:
        raise CustomPexpectError(step_name, f"Error Inesperado: {str(e)}", 500, device)
    else:
        return index
    


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
            run_step(child=self.child, command=self.crt_ip, expected_output=PROMP_CRT, step_name="IP CRT", timeout=self.timeout, device="CRT")

            return self.child
        except CustomPexpectError as e:
            return e

    def exit(self):
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
    def __init__(self, child, username, password, cid, timeout=30):
        self.child = child
        self.username = username
        self.password = password
        self.cid = cid
        self.session = []
        self.path_file = None
        self.timeout = timeout
        self.loopback = None

    def enter(self):
        try:
            run_step(child=self.child, 
                    command=f"hh {self.cid} | sed -E 's/^#//g' | grep -E \'\\b{self.cid}\\b\'",
                    expected_output=PROMP_CRT, 
                    step_name="CPE - hh", 
                    timeout=self.timeout,
                    device="CPE"
                    )
            hh_output = self.child.before.decode("utf-8")
            hh_pattern = re.compile(rf"\n *(?P<loopback>\d+\.\d+\.\d+\.\d+)\s+\w+\s+(?P<sede>\S+)\s+\w+\s+")
            hh_find = hh_pattern.search(hh_output)
            if hh_find:
                self.loopback = hh_find.group("loopback")
                self.sede = hh_find.group("sede")
            
            index_telnet = run_step(child=self.child, 
                    command=f"telnet {self.loopback}", 
                    expected_output=[r"[Uu]sername:", PROMP_CRT], 
                    step_name="CPE - TELNET", 
                    timeout=self.timeout, 
                    device="CPE"
                    )
            
            if index_telnet == 1:
                index_ssh = run_step(child=self.child, 
                        command=f"ssh -o StrictHostKeyChecking=no {self.username}@{self.loopback}",
                        expected_output=[r"[Pp]assword:", PROMP_CRT],
                        step_name="CPE - SSH", 
                        timeout=self.timeout, 
                        device="CPE"
                        )

                if index_ssh == 1:
                    return NotEnterToDevice(f"No se ingresó al equipo {self.loopback}", 500)
            else:
                run_step(child=self.child, 
                        command=self.username,
                        expected_output=r"[Pp]assword:", 
                        step_name="CPE - USERNAME", 
                        timeout=self.timeout,
                        device="CPE"
                        )

            index_os = run_step(child=self.child,                              
                            command=self.password,
                            expected_output= [PROMP_CISCO_SHOW, PROMP_CISCO, PROMP_HUAWEI, r"[Uu]sername:", r"[Pp]assword:"],
                            step_name="CPE - PASSWORD", 
                            timeout=self.timeout,
                            device="CPE"
                            )

            if index_os == 0:
                self.os = "cisco"
                run_step(child=self.child, 
                        command="ena",
                        expected_output=r"[Pp]assword:", 
                        step_name="CPE - ENA", 
                        timeout=self.timeout,
                        device="CPE"
                        )
                run_step(child=self.child, 
                        command=self.password,
                        expected_output=PROMP_CISCO, 
                        step_name="CPE - ENA PASSWORD", 
                        timeout=self.timeout,
                        device="CPE"
                        )
            elif index_os == 1:
                self.os = "cisco"
            elif index_os == 2:
                self.os = "huawei"
            elif index_os in [3, 4]:
                self.child.sendcontrol("c")
                time.sleep(TIME_SLEEP)
                self.child.expect(PROMP_CRT, timeout=self.timeout)
                return NotEnterToDevice(f"Credenciales fallidas para el equipo {self.loopback}", 500)

        except CustomPexpectError as e:
            return e
        else:
            return self.child
        

    def get_values(self):
        if hasattr(self, "os") and self.os == "cisco":
            try:
                run_step(child=self.child, 
                        command="terminal length 0",
                        expected_output=PROMP_CISCO, 
                        step_name="CPE - terminal length", 
                        timeout=self.timeout,
                        device="CPE"
                        )
                run_step(child=self.child, 
                        command="show version",
                        expected_output=PROMP_CISCO, 
                        step_name="CPE - version", 
                        timeout=self.timeout,
                        device="CPE"
                        )
                version_output = self.child.before.decode("utf-8")
                version_pattern = re.compile(r"\n(?P<version>.*)(?=\s+processor with)")
                version_find = version_pattern.search(version_output)
                if version_find:
                    self.version = version_find.group("version")

                run_step(child=self.child, 
                        command=f"show run | include hostname",
                        expected_output=PROMP_CISCO, 
                        step_name="CPE - hostname", 
                        timeout=self.timeout,
                        device="CPE"
                        )
                hostname_output = self.child.before.decode("utf-8")
                hostname_pattern = re.compile(r"\nhostname\s+(?P<hostname>\S+)")
                hostname_find = hostname_pattern.search(hostname_output)
                if hostname_find:
                    self.hostname = hostname_find.group("hostname")

            except CustomPexpectError as e:
                return e
            else:
                return self.child
        else:
            return

        
    def exit(self):
        try:
            if hasattr(self, "os"):
                if self.os == "huawei":
                    run_step(child=self.child,
                            command="quit",
                            expected_output=PROMP_CRT,
                            step_name=f"EXIT {self.loopback}",
                            timeout=self.timeout,
                            device="DEVICE"
                            )
                elif self.os == "cisco":
                    run_step(child=self.child,
                            command="exit",
                            expected_output=PROMP_CRT,
                            step_name=f"EXIT {self.loopback}",
                            timeout=self.timeout,
                            device="DEVICE"
                            )

        except CustomPexpectError as e:
            return e
        else:
            return self.child
        
    def configuration(self, commit, commands):
        self.commands = commands
        if hasattr(self, "os"):
            self.view_configuration = []

            if self.os == "cisco":
                prompt_output = self.child.after.decode("utf-8")
                run_step(child=self.child, 
                        command="configure terminal",
                        expected_output=PROMP_CISCO, 
                        step_name="CPE - configure terminal", 
                        timeout=self.timeout, 
                        device="CPE"
                        )
                configuration_output = self.child.before.decode("utf-8")
                self.view_configuration.extend((prompt_output + configuration_output).splitlines())
                
                if commit == "Y":
                    for command in self.commands:
                        prompt_output = self.child.after.decode("utf-8")
                        run_step(child=self.child, 
                                command=command,
                                expected_output=PROMP_CISCO, 
                                step_name="CPE - configuration", 
                                timeout=self.timeout, 
                                device="CPE"
                                )
                        configuration_output = self.child.before.decode("utf-8")
                        self.view_configuration.extend((prompt_output + configuration_output).splitlines())
                    
                    prompt_output = self.child.after.decode("utf-8")
                    run_step(child=self.child, 
                            command="exit",
                            expected_output=PROMP_CISCO, 
                            step_name="CPE - configuration", 
                            timeout=self.timeout, 
                            device="CPE"
                            )
                    configuration_output = self.child.before.decode("utf-8")
                    self.view_configuration.extend((prompt_output + configuration_output).splitlines())

                    prompt_output = self.child.after.decode("utf-8")
                    run_step(child=self.child, 
                            command="wr",
                            expected_output=PROMP_CISCO, 
                            step_name="CPE - configuration", 
                            timeout=self.timeout, 
                            device="CPE"
                            )
                    configuration_output = self.child.before.decode("utf-8")
                    self.view_configuration.extend((prompt_output + configuration_output).splitlines())

                    prompt_output = self.child.after.decode("utf-8")
                    run_step(child=self.child, 
                            command=" ",
                            expected_output=PROMP_CISCO, 
                            step_name="CPE - configuration", 
                            timeout=self.timeout, 
                            device="CPE"
                            )
                    configuration_output = self.child.before.decode("utf-8")
                    self.view_configuration.extend((prompt_output + configuration_output).splitlines())

                else:
                    prompt_output = self.child.after.decode("utf-8")
                    run_step(child=self.child, 
                            command="exit",
                            expected_output=PROMP_CISCO, 
                            step_name="CPE - configuration", 
                            timeout=self.timeout, 
                            device="CPE"
                            )
                    configuration_output = self.child.before.decode("utf-8")
                    self.view_configuration.extend((prompt_output + configuration_output).splitlines())

                    prompt_output = self.child.after.decode("utf-8")
                    run_step(child=self.child, 
                            command=" ",
                            expected_output=PROMP_CISCO, 
                            step_name="CPE - configuration", 
                            timeout=self.timeout, 
                            device="CPE"
                            )
                    configuration_output = self.child.before.decode("utf-8")
                    self.view_configuration.extend((prompt_output + configuration_output).splitlines())
    
    def save_session(self, file):
        self.path_file = file
        with open(self.path_file, "w") as file:
            for line in self.view_configuration:
                file.write(f"{line}\n")


class SendMailHitss(object):
    def __init__(self, file, to):
        self.file = file
        self.to = to

    def send_email(self, body):
        load_dotenv(override=True)

        email = EmailMessage(
            subject="API-AUTOSEP: configuration in device",
            body=body,
            from_email=os.getenv("EMAIL_AUTOSEP_USER"),
            to=[self.to],
        )

        email.content_subtype = "html"

        with open(self.file, 'rb') as f:
            email.attach('session.zip', f.read(), 'application/zip')

        email.send()
        return
    

class CreateHTML(object):
    def __init__(self, template, data):
        self.template = template
        self.data = data

    def create(self):
        env = Environment(loader=FileSystemLoader("."))
        template = env.get_template(self.template)

        self.context = {
            "data": self.data,
        }
        self.result =  template.render(self.context)
        return self.result
    

def save_in_csv(file, item):
    existe = os.path.isfile(file)
    with open(file, "a", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["code", "detail", "cid", "file"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=";")
        if not existe:
            writer.writeheader()
        writer.writerow(item)


def session_in_device(user_tacacs, pass_tacacs, list_of_cid, commands, commit, email, base_url):
    try:
        result = []
        sessionCRT = EnterToCRT("media/config_in_device", timeout=30)
        terminal_crt = sessionCRT.enter()
        if isinstance(terminal_crt, CustomPexpectError): raise terminal_crt
        for device in list_of_cid:
            item = {}
            try:
                terminal_device = EnterToDevice(terminal_crt, user_tacacs, pass_tacacs, device["cid"])
                terminal_device_status = terminal_device.enter()
                if isinstance(terminal_device_status, NotEnterToDevice): raise terminal_device_status
                terminal_device.get_values()
                terminal_device.configuration(commit=commit, commands=commands)
                terminal_device.save_session(sessionCRT.ruta + "/" + f'{device["cid"]}.txt')
                terminal_device.exit()

            except NotEnterToDevice as e:
                item["code"] = e.code
                item["detail"] = str(e)
                item["cid"] = device["cid"]
                item["file"] = None
            else:
                item["code"] = 200
                item["detail"] = "EXITOSO"
                item["cid"] = device["cid"]
                item["file"] = base_url + "/" + sessionCRT.ruta + "/" + f'{device["cid"]}.txt'
            finally:
                save_in_csv(file=sessionCRT.ruta + "/resumen.csv", item=item)
                result.append(item)

        sessionCRT.listar_txt()
        sessionCRT.comprimir_session("session.zip")
        sessionCRT.exit()

        create_html = CreateHTML("templates/config_in_device.j2", result)
        html = create_html.create()
        mail = SendMailHitss(sessionCRT.zipfile_name, email)
        mail.send_email(html)

        return result
    except CustomPexpectError as e:
        return e

