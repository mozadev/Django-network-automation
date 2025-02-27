import pandas as pd
import ipaddress
import pexpect
from dotenv import load_dotenv
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
import re
from django.core.mail import EmailMessage
import csv


TIME_SLEEP = 0.1
PROMP_HUAWEI = r"\n<[\w\-. \(\)]+>$"
PROMP_CISCO = r"\s[\w\-. \(\)]+#$"
PROMP_CISCO_SHOW = r"\s[\w\-. \(\)]+#$"
PROMP_CRT = r"~\]\$\s*$"

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
            run_step(child=self.child, command=self.crt_ip, expected_output=r"~\]\$\s*$", step_name="IP CRT", timeout=self.timeout, device="CRT")

            return self.child
        except CustomPexpectError as e:
            return e

    def exit(self):
        self.child.close()
        return None


class EnterToDevice(object):
    def __init__(self, child, username, password, ip, timeout=30):
        self.child = child
        self.username = username
        self.password = password
        self.ip = ip
        self.session = []
        self.path_file = None
        self.timeout = timeout

    def enter(self):
        try:
            run_step(child=self.child, 
                    command=f"hh {self.ip}",
                    expected_output=r"~\]\$\s*$", 
                    step_name="CPE - hh", 
                    timeout=self.timeout,
                    device="CPE"
                    )
            hh_output = self.child.before.decode("utf-8")
            hh_pattern = re.compile(rf"\n *(?P<loopback>{self.ip})\s+\w+\s+(?P<sede>\S+)\s+\w+\s+(?P<cid>\d+)\s+")
            hh_find = hh_pattern.search(hh_output)
            if hh_find:
                self.loopback = hh_find.group("loopback")
                self.sede = hh_find.group("sede")
                self.cid = int(hh_find.group("cid"))
            
            index_telnet = run_step(child=self.child, 
                    command=f"telnet {self.ip}", 
                    expected_output=[r"[Uu]sername:", r"~\]\$\s*$"], 
                    step_name="CPE - TELNET", 
                    timeout=self.timeout, 
                    device="CPE"
                    )
            
            if index_telnet == 1:
                index_ssh = run_step(child=self.child, 
                        command=f"ssh -o StrictHostKeyChecking=no {self.username}@{self.ip}",
                        expected_output=[r"[Pp]assword:", r"~\]\$\s*$"],
                        step_name="CPE - SSH", 
                        timeout=self.timeout, 
                        device="CPE"
                        )

                if index_ssh == 1:
                    return self.child
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
                            expected_output= [PROMP_CISCO_SHOW, PROMP_CISCO, PROMP_HUAWEI],
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
                        expected_output=r"\s[\w\-.]+#", 
                        step_name="CPE - ENA PASSWORD", 
                        timeout=self.timeout,
                        device="CPE"
                        )
            elif index_os == 1:
                self.os = "cisco"
            elif index_os == 2:
                self.os = "huawei"
            else:
                pass

        except CustomPexpectError as e:
            return e
        else:
            return self.child

    def get_values(self):
        if hasattr(self, "os"):
            if self.os == "huawei":
                run_step(child=self.child, 
                        command=f"screen-length 0 temporary",
                        expected_output=PROMP_HUAWEI, 
                        step_name="CPE - terminal length", 
                        timeout=self.timeout,
                        device="CPE"
                        )

                run_step(child=self.child, 
                        command=f"display version",
                        expected_output=PROMP_HUAWEI, 
                        step_name="CPE - VERSION", 
                        timeout=self.timeout, 
                        device="CPE"
                        )
                version_output = self.child.before.decode("utf-8")
                version_pattern = re.compile(r"\n(?P<version>.*?)(?=\s+uptime)")
                version_pattern_find = version_pattern.search(version_output)
                if version_pattern_find:
                    self.version = version_pattern_find.group("version")

                run_step(child=self.child, 
                        command=f"display current-configuration",
                        expected_output=PROMP_HUAWEI, 
                        step_name="CPE - HOSTNAME", 
                        timeout=self.timeout, 
                        device="CPE"
                        )
                sysname_output = self.child.before.decode("utf-8")
                sysname_pattern = re.compile(r"\n ?sysname (?P<sysname>\S+)")
                sysname_pattern_find = sysname_pattern.search(sysname_output)
                if sysname_pattern_find:
                    self.hostname = sysname_pattern_find.group("sysname")

            elif self.os == "cisco":
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
                else:
                    version_pattern = re.compile(r"\n(?P<version>.*) \(revision \d+\.\d+\) with \d+K\/\d+K bytes of memory\.")
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

        return self.child
    

    def get_time_of_reboot(self):
        if hasattr(self, "os") and hasattr(self, "version") and hasattr(self, "hostname"):
            if self.os == "huawei":

                run_step(child=self.child, 
                        command=f"display version",
                        expected_output=PROMP_HUAWEI, 
                        step_name="CPE - VERSION", 
                        timeout=self.timeout, 
                        device="CPE"
                        )
                
                uptime_output = self.child.before.decode("utf-8")

                year_pattern = re.compile(rf"{self.version} .* (?P<year>\d+) year")
                week_pattern = re.compile(rf"{self.version} .* (?P<week>\d+) week")
                days_pattern = re.compile(rf"{self.version} .* (?P<day>\d+) day")
                hour_pattern = re.compile(rf"{self.version} .* (?P<hour>\d+) hour")
                mins_pattern = re.compile(rf"{self.version} .* (?P<min>\d+) minute")

                year_find = year_pattern.search(uptime_output)
                week_find = week_pattern.search(uptime_output)
                days_find = days_pattern.search(uptime_output)
                hour_find = hour_pattern.search(uptime_output)
                mins_find = mins_pattern.search(uptime_output)

                if year_find:
                    self.year = int(year_find.group("year"))
                if week_find:
                    self.week = int(week_find.group("week"))
                if days_find:
                    self.days = int(days_find.group("day"))
                if hour_find:
                    self.hour = int(hour_find.group("hour"))
                if mins_find:
                    self.mins = int(mins_find.group("min"))

            elif self.os == "cisco":

                run_step(child=self.child, 
                        command="show version | include uptime",
                        expected_output=PROMP_CISCO, 
                        step_name="CPE - version", 
                        timeout=self.timeout,
                        device="CPE"
                        )

                uptime_output = self.child.before.decode("utf-8")

                year_pattern = re.compile(rf"{self.hostname} .* (?P<year>\d+) year")
                week_pattern = re.compile(rf"{self.hostname} .* (?P<week>\d+) week")
                days_pattern = re.compile(rf"{self.hostname} .* (?P<day>\d+) day")
                hour_pattern = re.compile(rf"{self.hostname} .* (?P<hour>\d+) hour")
                mins_pattern = re.compile(rf"{self.hostname} .* (?P<min>\d+) minute")

                year_find = year_pattern.search(uptime_output)
                week_find = week_pattern.search(uptime_output)
                days_find = days_pattern.search(uptime_output)
                hour_find = hour_pattern.search(uptime_output)
                mins_find = mins_pattern.search(uptime_output)

                if year_find:
                    self.year = int(year_find.group("year"))
                if week_find:
                    self.week = int(week_find.group("week"))
                if days_find:
                    self.days = int(days_find.group("day"))
                if hour_find:
                    self.hour = int(hour_find.group("hour"))
                if mins_find:
                    self.mins = int(mins_find.group("min"))

        return self.child


    def exit(self):
        try:
            if hasattr(self, "os"):
                if self.os == "huawei":
                    run_step(child=self.child,
                            command="quit",
                            expected_output=PROMP_CRT,
                            step_name=f"EXIT {self.ip}",
                            timeout=self.timeout,
                            device="DEVICE"
                            )
                elif self.os == "cisco":
                    run_step(child=self.child,
                            command="exit",
                            expected_output=PROMP_CRT,
                            step_name=f"EXIT {self.ip}",
                            timeout=self.timeout,
                            device="DEVICE"
                            )

        except CustomPexpectError as e:
            return e
        else:
            return self.child


def get_date(now, args):
    year = args["year"]
    week = args["week"]
    days = args["days"]
    hour = args["hour"]
    mins = args["mins"]

    if not year: year = 0
    if not week: week = 0
    if not days: days = 0
    if not hour: hour = 0
    if not mins: mins = 0

    delta = relativedelta(years=year, days=days, minutes=mins, hours=hour, weeks=week)
    return now - delta


def create_csv(path, data):
    file = path + "/data.csv"
    with open(file, "w", newline="") as csvfile:
        fieldnames = [
            "code", "detail", "IPv4", "loopback", "sede", "cid", "os", "version", "hostname", "year", "week", "days",
            "hour", "mins", "date_of_read", "date_of_uptime",
            ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()

        for i in data:
            writer.writerow({
                "code": i["code"],
                "detail": i["detail"],
                "IPv4": i["IPv4"],
                "loopback": i["device"]["loopback"],
                "sede": i["device"]["sede"],
                "cid": i["device"]["cid"],
                "os": i["device"]["os"],
                "version": i["device"]["version"],
                "hostname": i["device"]["hostname"],
                "year": i["device"]["year"],
                "week": i["device"]["week"],
                "days": i["device"]["days"],
                "hour": i["device"]["hour"],
                "mins": i["device"]["mins"],
                "date_of_read": i["device"]["datetime"],
                "date_of_uptime": i["device"]["uptime"],
            })

    return file

def session_in_device(user_tacacs, pass_tacacs, list_of_ip, email, base_url):
    try:
        result = []
        sessionCRT = EnterToCRT("media/get_time_of_reboot", timeout=30)
        terminal_crt = sessionCRT.enter()
        if isinstance(terminal_crt, CustomPexpectError): raise terminal_crt
        for device in list_of_ip:
            item = {}
            try:
                now = datetime.now()
                terminal_device = EnterToDevice(terminal_crt, user_tacacs, pass_tacacs, device["ip"])
                terminal_device_status = terminal_device.enter()
                if isinstance(terminal_device_status, NotEnterToDevice): raise terminal_device_status
                terminal_device.get_values()
                terminal_device.get_time_of_reboot()

                data = {
                    "loopback": terminal_device.loopback if hasattr(terminal_device, "loopback") else None,
                    "sede": terminal_device.sede if hasattr(terminal_device, "sede") else None,
                    "cid": terminal_device.cid if hasattr(terminal_device, "cid") else None,
                    "os": terminal_device.os if hasattr(terminal_device, "os") else None,
                    "version": terminal_device.version if hasattr(terminal_device, "version") else None,
                    "hostname": terminal_device.hostname if hasattr(terminal_device, "hostname") else None,
                    "year": terminal_device.year if hasattr(terminal_device, "year") else None,
                    "week": terminal_device.week if hasattr(terminal_device, "week") else None,
                    "days": terminal_device.days if hasattr(terminal_device, "days") else None,
                    "hour": terminal_device.hour if hasattr(terminal_device, "hour") else None,
                    "mins": terminal_device.mins if hasattr(terminal_device, "mins") else None,
                    "datetime": now.strftime("%d/%m/%Y %H:%M:%S"),
                }
                
                delta = get_date(now, data)
                data["uptime"] = delta.strftime("%d/%m/%Y %H:%M:%S")

                terminal_device.exit()

            except NotEnterToDevice as e:
                item["code"] = e.code
                item["detail"] = str(e)
                item["IPv4"] = device["ip"]
                item["device"] = data
            else:
                item["code"] = 200
                item["detail"] = "EXITOSO"
                item["IPv4"] = device["ip"]
                item["device"] = data
            finally:
                result.append(item)

        sessionCRT.exit()

        file = create_csv(sessionCRT.ruta, result)

        if email:
            mail = SendMailHitss(file, email)
            mail.send_email()

        return {"file": f"{base_url}/{file}"}
    except CustomPexpectError as e:
        return e



class SendMailHitss(object):
    def __init__(self, file, to):
        self.file = file
        self.to = to

    def send_email(self):
        load_dotenv(override=True)

        email = EmailMessage(
            subject="API-AUTOSEP: get uptime of devices",
            body="Estimado\nAdjunto los resultados solicitados al API-AUTOSEP.",
            from_email=os.getenv("EMAIL_AUTOSEP_USER"),
            to=[self.to],
        )

        email.content_subtype = "plain"

        with open(self.file, 'rb') as f:
            email.attach("data.csv", f.read(), "text/csv")

        email.send()
        return
