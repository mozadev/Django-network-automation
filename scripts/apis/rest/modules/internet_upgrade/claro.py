import pexpect
import os
from datetime import datetime
import time
import re
import pandas as pd
from dotenv import load_dotenv
import ipaddress

TIME_SLEEP = 0.2
PROMP_HUAWEI = r"\n<[\w\-. \(\)]+>$"
PROMP_CISCO = r"\s[\w\-. \(\)]+#$"
PROMP_CISCO_SHOW = r"\s[\w\-. \(\)]+#$"
PROMP_CRT = r"~\]\$\s*$"

def get_cid_newbw(file):
    data = pd.read_excel(file, usecols=["cid", "newbw", "action"])
    return data.to_dict(orient="records")

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

def is_mascara30(mascara):
    lastocteto = int(mascara.split(".")[-1])
    if lastocteto == 252:    
        return True
    else:
        return False

def is_wanprivade(wan):
    try:
        return ipaddress.ip_address(wan).exploded.startswith("10.31.")
    except ValueError:
        return False


class CustomPexpectError(Exception):
    def __init__(self, step, message, code, device):
        super().__init__(f"ERROR en el paso '{step}' del device {device}: {message}")
        self.step = step
        self.code = code
        self.device = device


class EnterToServer(object):
    def __init__(self, ip_sever, username, password, ruta, now, by_user=None, by_ip=None, timeout=5):
        self.username = username
        self.password = password
        self.ip_server = ip_sever
        self.by_ip = by_ip
        self.by_user = by_user
        self.ruta = ruta + "/" + now
        os.makedirs(self.ruta, exist_ok=True)
        self.session_log = self.ruta + "/session.log" 
        self.timeout = timeout
        self.hostname = None
        self.user = None
    
    def enter(self):
        try:

            self.child = pexpect.spawn(f"ssh -o StrictHostKeyChecking=no {self.username}@{self.ip_server}", timeout=self.timeout)
            self.child.logfile = open(self.session_log, "wb")
            self.child.expect("[Pp]assword:")

            run_step(child=self.child, command=self.password, expected_output=f"user:", step_name="Password", timeout=self.timeout, device="CRT")
            run_step(child=self.child, command=self.by_user, expected_output=f"address:", step_name="Address CRT", timeout=self.timeout, device="CRT")
            run_step(child=self.child, command=self.by_ip, expected_output=r"~\]\$\s*$", step_name="IP CRT", timeout=self.timeout, device="CRT")

            return self.child

        except CustomPexpectError as e:
            return e
        except pexpect.TIMEOUT:
            return CustomPexpectError("NO RESPONDE EL SERVIDOR, VERIFICAR LA CONECTIVIDAD Y/O CREDENCIALES", "Se agotó el tiempo de espera", 500, "SERVER")
    
    def get_values(self):
        run_step(child=self.child, command=r'echo $HOSTNAME | grep -E -o "^[[:alnum:]]+"', expected_output=r"~\]\$\s*$", step_name="SERVER HOSTNAME", timeout=self.timeout, device="SERVER")
        hostname_output = self.child.before.decode("utf-8")
        hostname_pattern = re.compile(r"\n(?P<hostname>\S+)")
        hostname_pattern_find = hostname_pattern.search(hostname_output)
        if hostname_pattern_find:
            self.hostname = hostname_pattern_find.group("hostname")

        run_step(child=self.child, command=r'echo $USER', expected_output=r"~\]\$\s*$", step_name="SERVER USER", timeout=self.timeout, device="SERVER")
        user_output = self.child.before.decode("utf-8")
        user_pattern = re.compile(r"\n(?P<user>\S+)")
        user_pattern_find = user_pattern.search(user_output)
        if user_pattern_find:
            self.user = user_pattern_find.group("user")

    def exit(self):
        try:
            run_step(
                child=self.child, 
                command="exit", 
                expected_output=r"~\]\$\s*$", 
                step_name="CRT - EXIT", 
                timeout=self.timeout, 
                device="CRT"
                )
            self.child.close()
        except CustomPexpectError as e:
            return e

        

class AgentPolo(object):
    def __init__(self, child, username, password, hostname, cid, timeout=30):
        self.child = child
        self.username = username
        self.password = password
        self.hostname = hostname
        self.cid = cid
        self.wan = None
        self.timeout = timeout
        self.pe = None
        self.is_wanprivade = None

    def get_wan(self):
        try:
            run_step(child=self.child, 
                    command=f"hh {self.cid} | grep -E \'\\b{self.cid}\\b\' | grep -E -o \'([0-9]{{1,3}}\.){{3}}[0-9]{{1,3}}\'", 
                    expected_output=r"~\]\$\s*$", 
                    step_name="hh", 
                    timeout=self.timeout, 
                    device="POLO"
                    )

            wan_output = self.child.before.decode("utf-8")
            wan_pattern = re.compile(r'(?P<wan>\d+\.\d+\.\d+\.\d+)')
            wan_pattern_find = wan_pattern.search(wan_output)

            if wan_pattern_find:
                self.wan = wan_pattern_find.group("wan")
                self.is_wanprivade = is_wanprivade(self.wan)
            return self.child
        except CustomPexpectError as e:
            return e

    def get_PE(self):
        try:
            if self.wan and hasattr(self, "is_wanprivade"):
                run_step(child=self.child,
                        command=f"ssh -o StrictHostKeyChecking=no {self.username}@{self.hostname}", 
                        expected_output=r"[Pp]assword:", 
                        step_name="POLO - SSH", 
                        timeout=self.timeout, 
                        device="POLO"
                        )
                run_step(child=self.child, 
                        command=self.password, 
                        expected_output=r"\n<[\w\-.]+>", 
                        step_name="POLO - PASS", 
                        timeout=self.timeout, 
                        device="POLO"
                        )
                run_step(child=self.child, 
                        command=f"screen-length 0 temporary",
                        expected_output=r"\n<[\w\-.]+>", 
                        step_name="POLO - NO MORE", 
                        timeout=self.timeout, 
                        device="POLO"
                        )
                
                if self.is_wanprivade:
                    run_step(child=self.child, 
                            command=f"display bgp routing-table {self.wan}",
                            expected_output=r"\n<[\w\-.]+>", 
                            step_name="POLO - ROUTING-TABLE", 
                            timeout=self.timeout, 
                            device="POLO"
                            )
                    pe_output = self.child.before.decode("utf-8")
                    pe_pattern = re.compile(r", best,.*\n Originator: (?P<pe>\d+\.\d+\.\d+\.\d+)")
                    pe_pattern_find = pe_pattern.search(pe_output)
                    if pe_pattern_find:
                        self.pe = pe_pattern_find.group("pe")
                else:
                    run_step(child=self.child, 
                            command=f"display ip routing-table {self.wan}",
                            expected_output=r"\n<[\w\-.]+>", 
                            step_name="POLO - ROUTING-TABLE", 
                            timeout=self.timeout, 
                            device="POLO"
                            )
                    pe_output = self.child.before.decode("utf-8")
                    pe_pattern = re.compile(r' +(?P<pe>\d+\.\d+\.\d+\.\d+)  +')
                    pe_pattern_find = pe_pattern.search(pe_output)
                    if pe_pattern_find:
                        self.pe = pe_pattern_find.group("pe")

                run_step(child=self.child, 
                        command="quit", 
                        expected_output=r"~\]\$\s*$", 
                        step_name="POLO - EXIT", 
                        timeout=self.timeout, 
                        device="POLO"
                        )
                return self.child
        except CustomPexpectError as e:
            return e
        

class AgentPE(object):
    def __init__(self, child, username, password, ip, action, is_wanprivade, timeout=30):
        self.child = child
        self.username = username
        self.password = password
        self.ip = ip
        self.timeout = timeout
        self.os = None
        self.version = None
        self.hostname = None
        self.in_trunk = []
        self.link = []
        self.interface = None
        self.subinterface = None
        self.interface_ip = None
        self.interface_mask = None
        self.is_mask30 = False
        self.trafficpolice_in = None
        self.trafficpolice_out = None
        self.trafficpolice_new_in = None
        self.trafficpolice_new_out = None
        self.mac = None
        self.lldp = None
        self.lldp_vendor = None
        self.bw = None
        self.bw_upgrade = None
        self.newbw = None
        self.capacidad = 0
        self.input_peak = 0
        self.output_peak = 0
        self.input_peak_porcentaje = 0
        self.output_peak_porcentaje = 0
        self.umbral = 0
        self.lt_umbral = None
        self.lt_umbral_value = None
        self.classifier_in = None
        self.classifier_out = None
        self.behavior_in = None
        self.behavior_out = None
        self.behavior_new_in = None
        self.behavior_new_out = None
        self.carcir_new_in = None
        self.carcir_new_out = None
        self.is_behavior_new_in = False
        self.is_behavior_new_out = False
        self.commands = []
        self.message = []
        self.send_email_carcir_in = False
        self.send_email_carcir_out = False
        self.action = action
        self.is_wanprivade = is_wanprivade

    def enter(self):
        try:
            if self.ip:
                if self.is_wanprivade:
                    run_step(child=self.child, 
                            command=f"hh {self.ip} | sed -E 's/^#//g' | grep -E \'\\b{self.ip}\\b\'", 
                            expected_output=PROMP_CRT,
                            step_name="PE - HH",
                            timeout=self.timeout,
                            device="PE"
                            )
                    device_output = self.child.before.decode("utf-8")
                    device_pattern = re.compile(rf"\n *{self.ip}\s+\S+\s+(?P<device>\S+)")
                    device_pattern_find = device_pattern.search(device_output)
                    if device_pattern_find:
                        self.device = device_pattern_find.group("device")
                    else:
                        self.device = None
                else:
                    self.device = self.ip

                run_step(child=self.child, 
                        command=f"ssh -o StrictHostKeyChecking=no {self.username}@{self.device}", 
                        expected_output=r"[Pp]assword:", 
                        step_name="PE - SSH", 
                        timeout=self.timeout, 
                        device="PE"
                        )
                tipo_pe = run_step(child=self.child, 
                        command=self.password,
                        expected_output=[PROMP_HUAWEI, PROMP_CISCO],
                        step_name="PE - PASSWORD", 
                        timeout=self.timeout,
                        device="PE"
                        )
                if tipo_pe == 0:
                    self.os = "huawei"
                else:
                    self.os = "zte"
                    run_step(child=self.child, 
                            command="exit",
                            expected_output=PROMP_CRT,
                            step_name="PE - EXIT - ZTE", 
                            timeout=self.timeout,
                            device="PE"
                            )
                    raise CustomPexpectError("INGRESO AL PE", "El PE es ZTE, aún no está implementado", 500, "PE")
                    
                run_step(child=self.child, 
                        command=f"screen-length 0 temporary",
                        expected_output=r"\n<[\w\-.]+>", 
                        step_name="PE - NO MORE", 
                        timeout=self.timeout, 
                        device="PE"
                        )
                run_step(child=self.child, 
                        command=f"display version | include uptime",
                        expected_output=r"\n<[\w\-.]+>", 
                        step_name="PE - VERSION", 
                        timeout=self.timeout, 
                        device="PE"
                        )
                version_output = self.child.before.decode("utf-8")
                version_pattern = re.compile(r"\n(?P<version>.*?)(?=\s+uptime)")
                version_pattern_find = version_pattern.search(version_output)
                if version_pattern_find:
                    self.version = version_pattern_find.group("version")

                run_step(child=self.child, 
                        command=f"display current-configuration  | include sysname",
                        expected_output=r"\n<[\w\-.]+>", 
                        step_name="PE - HOSTNAME", 
                        timeout=self.timeout, 
                        device="PE"
                        )
                sysname_output = self.child.before.decode("utf-8")
                sysname_pattern = re.compile(r"\nsysname (?P<sysname>\S+)")
                sysname_pattern_find = sysname_pattern.search(sysname_output)
                if sysname_pattern_find:
                    self.hostname = sysname_pattern_find.group("sysname")

        except CustomPexpectError as e:
            return e
        else:
            return self.child
        
    def get_values(self, wan):
        if self.os == "huawei" and wan:
            try:
                run_step(child=self.child, 
                        command=f"display ip routing-table {wan}",
                        expected_output=r"\n<[\w\-.]+>", 
                        step_name="PE - IP ROUTING TABLE", 
                        timeout=self.timeout, 
                        device="PE"
                        )
                routingtable_output = self.child.before.decode("utf-8")
                routingtable_pattern = re.compile(r'\d+\.\d+\.\d+\.\d+\/\d+.*\d+\.\d+\.\d+\.\d+ +(?P<subinterface>\S+)')
                routingtable_pattern_find = routingtable_pattern.search(routingtable_output)
                if routingtable_pattern_find:
                    self.subinterface = routingtable_pattern_find.group("subinterface")
                    self.interface = self.subinterface.split(".")[0]

                prompt_output = self.child.after.decode("utf-8")
                run_step(child=self.child, 
                        command=f"display curr int {self.subinterface}",
                        expected_output=r"\n<[\w\-.]+>", 
                        step_name="PE - CONFIG SUB INTERFACE", 
                        timeout=self.timeout, 
                        device="PE"
                        )
                ip_mask_output = self.child.before.decode("utf-8")
                self.view_subinterface = (prompt_output + ip_mask_output).splitlines()

                ip_mask_pattern = re.compile(r'ip address (?P<ip>\d+\.\d+\.\d+\.\d+) (?P<mask>\d+\.\d+\.\d+\.\d+)')
                ip_mask_find = ip_mask_pattern.search(ip_mask_output)
                if ip_mask_find:
                    self.interface_ip = ip_mask_find.group("ip")
                    self.interface_mask = ip_mask_find.group("mask")

                trafficpolice_in_pattern = re.compile(r'traffic-policy (?P<trafficpolice_in>\S+) inbound')
                trafficpolice_in_find = trafficpolice_in_pattern.search(ip_mask_output)
                if trafficpolice_in_find:
                    self.trafficpolice_in = trafficpolice_in_find.group("trafficpolice_in")

                trafficpolice_out_pattern = re.compile(r'traffic-policy (?P<trafficpolice_out>\S+) outbound')
                trafficpolice_out_find = trafficpolice_out_pattern.search(ip_mask_output)
                if trafficpolice_out_find:
                    self.trafficpolice_out = trafficpolice_out_find.group("trafficpolice_out")

                run_step(child=self.child, 
                        command=f"display interface {self.interface}",
                        expected_output=r"\n<[\w\-.]+>", 
                        step_name="PE - INTERFACE", 
                        timeout=self.timeout, 
                        device="PE"
                        )

                interface_output = self.child.before.decode("utf-8")
                interface_pattern = re.compile(r"(?P<interface>GigabitEthernet\S+) +UP")
                interface_pattern_find = interface_pattern.findall(interface_output)

                physical_pattern = re.compile(r"\nPort BW: (?P<capacidad>\d+)(?P<unit>[a-zA-Z]+),")
                physical_pattern_find = physical_pattern.search(interface_output)

                in_peak_pattern = re.compile(r"\sInput peak rate (?P<input>\d+) ")
                in_peak_pattern_find = in_peak_pattern.search(interface_output)

                out_peak_pattern = re.compile(r"\sOutput peak rate (?P<output>\d+) ")
                out_peak_pattern_find = out_peak_pattern.search(interface_output)

                if physical_pattern_find and in_peak_pattern_find and out_peak_pattern_find:
                    capacidad = int(physical_pattern_find.group("capacidad")) * 10 ** 3
                    input_peak_rate = int(in_peak_pattern_find.group("input")) / 10 ** 6
                    output_peak_rate = int(out_peak_pattern_find.group("output")) / 10 ** 6
                    self.link.append({"interface": self.interface,
                                      "capacidad_inMegas": capacidad,
                                      "capacidad_unitFound": physical_pattern_find.group("unit"),
                                      "input_peak_rate": input_peak_rate,
                                      "output_peak_rate": output_peak_rate,
                                      "input_porcentaje": round((input_peak_rate / capacidad) * 100, 2),
                                      "output_porcentaje": round((output_peak_rate / capacidad) * 100, 2),
                                      })

                if len(interface_pattern_find) > 0:
                    for i in interface_pattern_find:
                        self.in_trunk.append(i)

                    for i in self.in_trunk:
                        interface_trunk = i
                        run_step(child=self.child, 
                                command=f"display interface {interface_trunk}",
                                expected_output=r"\n<[\w\-.]+>", 
                                step_name="PE - IN INTERFACE", 
                                timeout=self.timeout, 
                                device="PE"
                                )
                        physical_link_output = self.child.before.decode("utf-8")
                        physical_link_find = physical_pattern.search(physical_link_output)
                        physical_link_in_find = in_peak_pattern.search(physical_link_output)
                        physical_link_out_find = out_peak_pattern.search(physical_link_output)

                        if physical_link_find and physical_link_in_find and physical_link_out_find:
                            capacidad = int(physical_link_find.group("capacidad")) * 10 ** 3
                            input_peak_rate = int(physical_link_in_find.group("input")) / 10 ** 6
                            output_peak_rate = int(physical_link_out_find.group("output")) / 10 ** 6
                            self.link.append({"interface": interface_trunk,
                                              "capacidad_inMegas": capacidad,
                                              "capacidad_unit": physical_link_find.group("unit"),
                                              "input_peak_rate": input_peak_rate,
                                              "output_peak_rate": output_peak_rate,
                                              "input_porcentaje": round((input_peak_rate / capacidad) * 100, 2),
                                              "output_porcentaje": round((output_peak_rate / capacidad) * 100, 2),
                                              })

                run_step(child=self.child, 
                        command=f"display arp all | i {wan}",
                        expected_output=r"\n<[\w\-.]+>", 
                        step_name="PE - ARP", 
                        timeout=self.timeout, 
                        device="PE"
                        )
                mac_output = self.child.before.decode("utf-8")
                mac_pattern = re.compile(r'(\d+\.\d+\.\d+\.\d+) +(?P<mac>\S+)')
                mac_find = mac_pattern.search(mac_output)
                if mac_find:
                    self.mac = mac_find.group("mac")
                else:
                    self.message.append("No se encontró la MAC")

                run_step(child=self.child, 
                        command=f"display lldp neighbor interface {self.interface}",
                        expected_output=r"\n<[\w\-.]+>", 
                        step_name="PE - LLDP", 
                        timeout=self.timeout, 
                        device="PE"
                        )
                lldp_output = self.child.before.decode("utf-8")
                lldp_pattern = re.compile(r'System name +:(?P<lldp>\S+)')
                lldp_find = lldp_pattern.search(lldp_output)
                if lldp_find:
                    self.lldp = lldp_find.group("lldp")
                    if not self.lldp.lower().startswith("cmetro"):
                        self.message.append(f"El acceso no es cmetro, es {self.lldp}")
                else:
                    self.message.append(f"No se encontró lldp para la primera sub-interface {self.interface}")

                lldp_vendor_pattern = re.compile(r'System description +:(?P<vendor>.*)')
                lldp_vendor_find = lldp_vendor_pattern.search(lldp_output)
                if lldp_vendor_find:
                    self.lldp_vendor = lldp_vendor_find.group("vendor")

                if not self.lldp and len(self.in_trunk) > 0:
                    first_interface_trunk = self.in_trunk[0]
                    run_step(child=self.child, 
                            command=f"display lldp neighbor interface {first_interface_trunk}",
                            expected_output=r"\n<[\w\-.]+>", 
                            step_name="PE - LLDP TRUNK", 
                            timeout=self.timeout, 
                            device="PE"
                            )
                    lldp_output = self.child.before.decode("utf-8")
                    lldp_find = lldp_pattern.search(lldp_output)
                    if lldp_find:
                        self.lldp = lldp_find.group("lldp")
                        if not self.lldp.lower().startswith("cmetro"):
                            self.message.append(f"El acceso no es cmetro, es {self.lldp}")
                    else:
                        self.message.append(f"No se encontró lldp para la primera sub-interface {first_interface_trunk}")

                    lldp_vendor_pattern = re.compile(r'System description +:(?P<vendor>.*)')
                    lldp_vendor_find = lldp_vendor_pattern.search(lldp_output)
                    if lldp_vendor_find:
                        self.lldp_vendor = lldp_vendor_find.group("vendor")


            except CustomPexpectError as e:
                return e
            else:
                return self.child
    
    def analizar(self, upgrade, umbral=60):
        self.bw_upgrade = upgrade
        self.umbral = umbral
        
        if self.os == "huawei" and len(self.link) > 0:
            for i in self.link:
                self.capacidad += i["capacidad_inMegas"]
                self.input_peak += i["input_peak_rate"]
                self.output_peak += i["output_peak_rate"]

            self.input_peak_porcentaje = round((self.input_peak / self.capacidad) * 100, 2)
            self.output_peak_porcentaje = round((self.output_peak / self.capacidad) * 100, 2)
        
        if self.os == "huawei" and self.interface_mask:
            self.is_mask30 = is_mascara30(self.interface_mask)
            if self.trafficpolice_in and self.trafficpolice_out:
                bw_pattern = re.compile(r"(?P<pre>[a-zA-Z_]*)(?P<bw>\d+)(?P<post>[a-zA-Z_]*)")
                bw_in_found = bw_pattern.search(self.trafficpolice_in)
                bw_out_found = bw_pattern.search(self.trafficpolice_out)
                if bw_in_found and bw_out_found and bw_in_found.group("bw") == bw_out_found.group("bw"):
                    self.bw = int(bw_in_found.group("bw"))
                    if self.is_mask30:
                        self.newbw = self.bw_upgrade
                    else:
                        if self.action == "upgrade":
                            self.newbw = self.bw + self.bw_upgrade
                        else:
                            self.newbw = self.bw
                    self.trafficpolice_new_in = bw_in_found.group("pre") + f"{self.newbw}" + bw_in_found.group("post")
                    self.trafficpolice_new_out = bw_out_found.group("pre") + f"{self.newbw}" + bw_out_found.group("post")
        
        if self.os == "huawei" and  isinstance(self.newbw, int) and self.newbw > 0 and self.capacidad > 0:
            self.lt_umbral_value = round(((self.newbw + max(self.input_peak, self.output_peak)) / self.capacidad) * 100, 2)

            if self.lt_umbral_value > self.umbral:
                self.lt_umbral = False
                self.message.append(f"No hay comandos de configuración porque el NewBW {self.newbw} Megas ({self.lt_umbral_value}%) supera el umbral de {self.umbral}%")
            else:
                self.lt_umbral = True

        if self.os == "huawei" and self.lt_umbral:
            prompt_output = self.child.after.decode("utf-8")
            run_step(child=self.child,
                    command=f"display curr configuration trafficpolicy {self.trafficpolice_in}",
                    expected_output=r"\n<[\w\-.]+>", 
                    step_name="PE - TRAFFICPOLICY IN", 
                    timeout=self.timeout, 
                    device="PE"
                    )
            trafficpolicy_in_output = self.child.before.decode("utf-8")
            self.view_trafficpolice_in = (prompt_output + trafficpolicy_in_output).splitlines()

            trafficpolicy_in_pattern = re.compile(r'classifier (?P<classifier>\S+) behavior (?P<behavior>[\w\-.]+) ')
            trafficpolicy_in_find = trafficpolicy_in_pattern.search(trafficpolicy_in_output)
            if trafficpolicy_in_find:
                self.classifier_in = trafficpolicy_in_find.group("classifier")
                self.behavior_in = trafficpolicy_in_find.group("behavior")

            prompt_output = self.child.after.decode("utf")
            run_step(child=self.child,
                    command=f"display curr configuration trafficpolicy {self.trafficpolice_out}",
                    expected_output=r"\n<[\w\-.]+>", 
                    step_name="PE - TRAFFICPOLICY OUT", 
                    timeout=self.timeout, 
                    device="PE"
                    )
            trafficpolicy_out_output = self.child.before.decode("utf-8")
            self.view_trafficpolice_out = (prompt_output + trafficpolicy_out_output).splitlines()

            trafficpolicy_out_pattern = re.compile(r'classifier (?P<classifier>\S+) behavior (?P<behavior>[\w\-.]+) ')
            trafficpolicy_out_find = trafficpolicy_out_pattern.search(trafficpolicy_out_output)
            if trafficpolicy_out_find:
                self.classifier_out = trafficpolicy_out_find.group("classifier")
                self.behavior_out = trafficpolicy_out_find.group("behavior")

            if self.behavior_in == self.trafficpolice_in:
                prompt_output = self.child.after.decode("utf-8")
                run_step(child=self.child,
                        command=f"display curr configuration trafficpolicy {self.trafficpolice_new_in}",
                        expected_output=r"\n<[\w\-.]+>", 
                        step_name="PE - TRAFFICPOLICY NEW IN", 
                        timeout=self.timeout, 
                        device="PE"
                        )
                trafficpolicy_new_in_output = self.child.before.decode("utf-8")
                self.view_trafficpolice_new_in = (prompt_output + trafficpolicy_new_in_output).splitlines()

                trafficpolicy_new_in_pattern = re.compile(r'classifier (?P<classifier>\S+) behavior (?P<behavior>[\w\-.]+) ')
                trafficpolicy_new_in_find = trafficpolicy_new_in_pattern.search(trafficpolicy_new_in_output)
                if trafficpolicy_new_in_find:
                    self.behavior_new_in = trafficpolicy_new_in_find.group("behavior")

                prompt_output = self.child.after.decode("utf-8")
                run_step(child=self.child,
                        command=f"display curr configuration behavior {self.trafficpolice_new_in}",
                        expected_output=r"\n<[\w\-.]+>", 
                        step_name="PE - BEHAVIOR NEW IN", 
                        timeout=self.timeout, 
                        device="PE"
                        )
                behavior_new_in_output = self.child.before.decode("utf-8")
                self.view_behavior_new_in = (prompt_output + behavior_new_in_output).splitlines()

                behavior_new_in_pattern = re.compile(r"car cir (?P<carcir>\d+) ")
                behavior_new_in_find = behavior_new_in_pattern.search(behavior_new_in_output)
                if behavior_new_in_find:
                    self.carcir_new_in = int(behavior_new_in_find.group("carcir"))
                
            if self.behavior_out == self.trafficpolice_out:
                prompt_output = self.child.after.decode("utf-8")
                run_step(child=self.child,
                        command=f"display curr configuration trafficpolicy {self.trafficpolice_new_out}",
                        expected_output=r"\n<[\w\-.]+>", 
                        step_name="PE - TRAFFICPOLICY NEW OUT", 
                        timeout=self.timeout, 
                        device="PE"
                        )
                trafficpolicy_new_out_output = self.child.before.decode("utf-8")
                self.view_trafficpolice_new_out = (prompt_output + trafficpolicy_new_out_output).splitlines()

                trafficpolicy_new_out_pattern = re.compile(r'classifier (?P<classifier>\S+) behavior (?P<behavior>[\w\-.]+) ')
                trafficpolicy_new_out_find = trafficpolicy_new_out_pattern.search(trafficpolicy_new_out_output)
                if trafficpolicy_new_out_find:
                    self.behavior_new_out = trafficpolicy_new_out_find.group("behavior")

                prompt_output = self.child.after.decode("utf-8")
                run_step(child=self.child,
                        command=f"display curr configuration behavior {self.trafficpolice_new_out}",
                        expected_output=r"\n<[\w\-.]+>", 
                        step_name="PE - BEHAVIOR NEW IN", 
                        timeout=self.timeout, 
                        device="PE"
                        )
                behavior_new_out_output = self.child.before.decode("utf-8")
                self.view_behavior_new_out = (prompt_output + behavior_new_out_output).splitlines()

                behavior_new_out_pattern = re.compile(r"car cir (?P<carcir>\d+) ")
                behavior_new_out_find = behavior_new_out_pattern.search(behavior_new_out_output)
                if behavior_new_out_find:
                    self.carcir_new_out = int(behavior_new_out_find.group("carcir"))

        if self.os == "huawei" and (self.behavior_new_in == self.trafficpolice_new_in) and isinstance(self.newbw, int):
            if self.carcir_new_in == self.newbw * 1024:
                self.is_behavior_new_in = True
            else:
                self.is_behavior_new_in = False
                self.send_email_carcir_in = True
                self.message.append(f"El carcir_new_in {self.carcir_new_in} no coincide con el que debería {self.newbw * 1024} por lo que no se crearán los comandos")

        if self.os == "huawei" and (self.behavior_new_out == self.trafficpolice_new_out) and isinstance(self.newbw, int): 
            if self.carcir_new_out == self.newbw * 1024:
                self.is_behavior_new_out = True
            else:
                self.is_behavior_new_out = False
                self.send_email_carcir_out = True
                self.message.append(f"El carcir_new_out {self.carcir_new_out} no coincide con el que debería {self.newbw * 1024} por lo que no se crearán los comandos.")
                
    def create_commands(self):
        if self.os == "huawei" and self.newbw and self.lt_umbral and not self.send_email_carcir_in and not self.send_email_carcir_out:
            if not self.is_behavior_new_in:
                self.commands.extend(
                    [
                        "traffic behavior {trafficpolicy_in}".format(trafficpolicy_in=self.trafficpolice_new_in),
                        " car cir {car_cir}".format(car_cir=self.newbw * 1024),
                        " quit",
                    ]
                )
                self.is_behavior_new_in = True
            
            if not self.is_behavior_new_out:
                self.commands.extend(
                    [
                        "traffic behavior {trafficpolicy_out}".format(trafficpolicy_out=self.trafficpolice_new_out),
                        " car cir {car_cir}".format(car_cir=self.newbw * 1024),
                        " quit",
                    ]
                )
                self.is_behavior_new_out = True 

            if self.is_behavior_new_in and not self.behavior_new_in:
                self.commands.extend(
                    [
                        "traffic policy {trafficpolicy_in}".format(trafficpolicy_in=self.trafficpolice_new_in),
                        " undo share-mode",
                        " statistics enable",
                        " classifier {classifier_in} behavior {trafficpolicy_in} precedence 1".format(classifier_in=self.classifier_in, trafficpolicy_in=self.trafficpolice_new_in),
                        " quit",   
                    ]
                )

            if self.is_behavior_new_out and not self.behavior_new_out:
                self.commands.extend(
                    [
                        "traffic policy {trafficpolicy_out}".format(trafficpolicy_out=self.trafficpolice_new_out),
                        " undo share-mode",
                        " statistics enable",
                        " classifier {classifier_out} behavior {trafficpolicy_out} precedence 1".format(classifier_out=self.classifier_out, trafficpolicy_out=self.trafficpolice_new_out),
                        " quit",   
                    ]
                )

            if self.is_behavior_new_in and self.is_behavior_new_out:
                self.commands.extend(
                    [
                        "interface {subinterface}".format(subinterface=self.subinterface),
                        " undo traffic-policy inbound",
                        " undo traffic-policy outbound",
                        " traffic-policy {trafficpolicy_in} inbound".format(trafficpolicy_in=self.trafficpolice_new_in),
                        " traffic-policy {trafficpolicy_out} outbound".format(trafficpolicy_out=self.trafficpolice_new_out),
                        " quit",
                    ]
                )

    def configuration(self, commit):
        if hasattr(self, "os"):
            if self.os == "huawei" and hasattr(self, "commands"):
                self.view_configuration = []
                prompt_output = self.child.after.decode("utf-8")
                run_step(child=self.child, 
                        command=f"system-view",
                        expected_output=r"\[\S+\]", 
                        step_name="PE - system-view", 
                        timeout=self.timeout, 
                        device="PE"
                        )
                output = self.child.before.decode("utf-8")
                self.view_configuration.extend((prompt_output + output).splitlines())
                
                for command in self.commands:
                    prompt_output = self.child.after.decode("utf-8")
                    run_step(child=self.child, 
                            command=command,
                            expected_output=r"\[\S+\]", 
                            step_name="PE - configuration", 
                            timeout=self.timeout, 
                            device="PE"
                            )
                    output = self.child.before.decode("utf-8")
                    self.view_configuration.extend((prompt_output + output).splitlines())
                
                prompt_output = self.child.after.decode("utf-8")
                index = run_step(child=self.child, 
                        command="quit",
                        expected_output=[r"\[Y\(yes\)\/N\(no\)\/C\(cancel\)\]:", r"\n<[\w\-.]+>"], 
                        step_name="PE - configuration", 
                        timeout=self.timeout, 
                        device="PE"
                        )
                output = self.child.before.decode("utf-8")
                self.view_configuration.extend((prompt_output + output).splitlines())
                
                if index == 0:
                    prompt_output = self.child.after.decode("utf-8")
                    run_step(child=self.child, 
                            command=commit,
                            expected_output=r"\n<[\w\-.]+>", 
                            step_name="PE - configuration", 
                            timeout=self.timeout, 
                            device="PE"
                            )
                    output = self.child.before.decode("utf-8")
                    self.view_configuration.extend((prompt_output + output).splitlines())

                prompt_output = self.child.after.decode("utf-8")
                run_step(child=self.child, 
                        command=" ",
                        expected_output=r"\n<[\w\-.]+>", 
                        step_name="PE - configuration", 
                        timeout=self.timeout, 
                        device="PE"
                        )
                output = self.child.before.decode("utf-8")
                self.view_configuration.extend((prompt_output + output).splitlines())


    def exit(self):
        if self.os == "huawei":
            try:
                run_step(child=self.child, 
                        command="quit",
                        expected_output=r"~\]\$\s*$", 
                        step_name="PE - EXIT", 
                        timeout=self.timeout, 
                        device="PE"
                        )
                    
            except CustomPexpectError as e:
                return e
            else:
                return self.child


class AgentCPE(object):
    def __init__(self, child, username, password, cpe, timeout=30):
        self.child = child
        self.username = username
        self.password = password
        self.ip = cpe
        self.timeout = timeout
        self.os = None
        self.is_ratelimit = False
    
    def enter(self):
        try:
            run_step(child=self.child, 
                    command=f"telnet {self.ip}", 
                    expected_output=r"[Uu]sername:", 
                    step_name="CPE - TELNET", 
                    timeout=self.timeout, 
                    device="CPE"
                    )
            run_step(child=self.child, 
                    command=self.username,
                    expected_output=r"[Pp]assword:", 
                    step_name="CPE - USERNAME", 
                    timeout=self.timeout,
                    device="CPE"
                    )
            index = run_step(child=self.child,                              
                            command=self.password,
                            expected_output= [r"\s[\w\-.]+>", r"\s[\w\-.]+#", r"\n<[\w\-.]+>"],
                            step_name="CPE - PASSWORD", 
                            timeout=self.timeout,
                            device="CPE"
                            )
            if index == 0:
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
            elif index == 1:
                self.os = "cisco"
            elif index == 2:
                self.os = "huawei"
            else:
                pass
        except CustomPexpectError as e:
            return e
        else:
            return self.child
        
    def get_values(self):
        if hasattr(self, "os") and self.os == "huawei":
            try:
                run_step(child=self.child, 
                        command=f"screen-length 0 temporary",
                        expected_output=r"\n<[\w\-.]+>", 
                        step_name="CPE - terminal length", 
                        timeout=self.timeout,
                        device="CPE"
                        )

                run_step(child=self.child, 
                        command=f"display version",
                        expected_output=r"\n<[\w\-.]+>", 
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
                        command=f"display current-configuration  | include sysname",
                        expected_output=r"\n<[\w\-.]+>", 
                        step_name="CPE - HOSTNAME", 
                        timeout=self.timeout, 
                        device="CPE"
                        )
                sysname_output = self.child.before.decode("utf-8")
                sysname_pattern = re.compile(r"\n ?sysname (?P<sysname>\S+)")
                sysname_pattern_find = sysname_pattern.search(sysname_output)
                if sysname_pattern_find:
                    self.hostname = sysname_pattern_find.group("sysname")

                run_step(child=self.child, 
                        command=f"display ip interface brief",
                        expected_output=r"\n<[\w\-.]+>", 
                        step_name="CPE - terminal length", 
                        timeout=self.timeout,
                        device="CPE"
                        )
                ipinterface_output = self.child.before.decode("utf-8")
                ipinterface_pattern = re.compile(rf'\n(?P<interface>\S+) +{self.ip}')
                ipinterface_find = ipinterface_pattern.search(ipinterface_output)
                if ipinterface_find:
                    self.interface = ipinterface_find.group("interface")

                if hasattr(self, "interface"):
                    prompt = self.child.after.decode("utf-8")
                    run_step(child=self.child, 
                            command=f"display current-configuration interface {self.interface}",
                            expected_output=r"\n<[\w\-.]+>", 
                            step_name="CPE - interface", 
                            timeout=self.timeout,
                            device="CPE"
                            )
                    interface_output = self.child.before.decode("utf-8")
                    self.view_interface = (prompt + interface_output).splitlines()

                    bandwidth_pattern = re.compile(r'bandwidth (?P<bandwidth>\d+)')
                    bandwidth_find = bandwidth_pattern.search(interface_output)
                    if bandwidth_find:
                        self.bandwidth = bandwidth_find.group("bandwidth")

                    description_pattern = re.compile(r"description (?P<description>.*)(?=\r\n)")
                    description_find = description_pattern.search(interface_output)
                    if description_find:
                         self.description = description_find.group("description")

                    ratelimit_pattern = re.compile(r"qos car (?P<type>\w+) cir (?P<cir>\d+) cbs (?P<cbs>\d+) pbs (?P<pbs>\d+) ")
                    ratelimit_find = ratelimit_pattern.finditer(interface_output)
                    self.ratelimit = []
                    for j in ratelimit_find:
                        item = {}
                        self.is_ratelimit = True
                        item["type"] = j.group("type")
                        item["cir"] = int(j.group("cir"))
                        item["cbs"] = int(j.group("cbs"))
                        item["pbs"] = int(j.group("pbs"))
                        self.ratelimit.append(item)

            except CustomPexpectError as e:
                return e
            else:
                return self.child
        elif hasattr(self, "os") and self.os == "cisco":
            try:
                run_step(child=self.child, 
                        command="terminal length 0",
                        expected_output=r"\s[\w\-.]+#", 
                        step_name="CPE - terminal length", 
                        timeout=self.timeout,
                        device="CPE"
                        )
                run_step(child=self.child, 
                        command="show version",
                        expected_output=r"\s[\w\-.]+#$", 
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
                        expected_output=r"\s[\w\-\.]+#$", 
                        step_name="CPE - hostname", 
                        timeout=self.timeout,
                        device="CPE"
                        )
                hostname_output = self.child.before.decode("utf-8")
                hostname_pattern = re.compile(r"\nhostname\s+(?P<hostname>\S+)")
                hostname_find = hostname_pattern.search(hostname_output)
                if hostname_find:
                    self.hostname = hostname_find.group("hostname")

                run_step(child=self.child, 
                        command=f"sh ip int brief",
                        expected_output=r"\s[\w\-\.]+#$", 
                        step_name="CPE - ipinter", 
                        timeout=self.timeout,
                        device="CPE"
                        )

                ipinter_output = self.child.before.decode("utf-8")
                ipinter_pattern = re.compile(rf'\n(?P<interface>\S+) +{self.ip}')
                ipinter_find = ipinter_pattern.search(ipinter_output)
                if ipinter_find:
                    self.interface = ipinter_find.group("interface")

                if hasattr(self, "interface"):
                    prompt = self.child.after.decode("utf-8")
                    run_step(child=self.child, 
                            command=f"sh run int {self.interface}",
                            expected_output=r"\s[\w\-.]+#", 
                            step_name="CPE - interface", 
                            timeout=self.timeout,
                            device="CPE"
                            )
                    interface_output = self.child.before.decode("utf-8")
                    self.view_interface = (prompt + interface_output).splitlines()

                    bandwidth_pattern = re.compile(r'bandwidth (?P<bandwidth>\d+)')
                    bandwidth_find = bandwidth_pattern.search(interface_output)
                    if bandwidth_find:
                        self.bandwidth = bandwidth_find.group("bandwidth")

                    description_pattern = re.compile(r"description (?P<description>.*)(?=\r\n)")
                    description_find = description_pattern.search(interface_output)
                    if description_find:
                        self.description = description_find.group("description")

                    ratelimit_pattern = re.compile(r"rate-limit (?P<type>\w+) cir (?P<cir>\d+) (?P<cbs>\d+) (?P<pbs>\d+) ")
                    ratelimit_find = ratelimit_pattern.finditer(interface_output)
                    self.ratelimit = []
                    for j in ratelimit_find:
                        item = {}
                        self.is_ratelimit = True
                        item["type"] = j.group("type")
                        item["cir"] = int(j.group("cir"))
                        item["cbs"] = int(j.group("cbs"))
                        item["pbs"] = int(j.group("pbs"))
                        self.ratelimit.append(item)

            except CustomPexpectError as e:
                return e
            else:
                return self.child
        else:
            return

    def analizar(self, upgrade):
        self.upgrade = upgrade
        self.newbw = upgrade
        self.commands = []
        if self.os == "cisco":
            if hasattr(self, "description"):
                self.description_new = re.sub(r"\d+ *mbps", rf" {self.newbw} Mbps ", self.description, flags=re.IGNORECASE)
        elif self.os == "huawei":
            if hasattr(self, "description"):
                self.description_new = re.sub(r"\d+ *mbps", rf" {self.newbw} Mbps ", self.description, flags=re.IGNORECASE)


    
    def create_commands(self):
        if self.is_ratelimit and len(self.ratelimit) == 2:
            type1, cir1, cbs1, pbs1 = "inbound", self.newbw * 1024, self.newbw * 1024 * 0.1875 * 1000, self.newbw * 1024 * 0.1875 * 2 * 1000
            type2, cir2, cbs2, pbs2 = "outbound", self.newbw * 1024, self.newbw * 1024 * 0.1875 * 1000, self.newbw * 1024 * 0.1875 * 2 * 1000

        if self.os == "cisco":
            if hasattr(self, "description_new"):
                self.commands.extend(
                    [
                        f"interface {self.interface}",
                        f" bandwidth {self.newbw * 1024}",
                        f" description {self.description_new}",
                        f" no rate-limit inbound" if self.is_ratelimit else None,
                        f" no rate-limit outbound" if self.is_ratelimit else None,
                        f" rate-limit {type1} cir {cir1:.0f} {cbs1:.0f} {pbs1:.0f} conform-action transmit exceed-action drop" if self.is_ratelimit else None,
                        f" rate-limit {type2} cir {cir2:.0f} {cbs2:.0f} {pbs2:.0f} conform-action transmit exceed-action drop" if self.is_ratelimit else None,
                        f" exit",
                    ]
                )
        elif self.os == "huawei":
            if hasattr(self, "description_new"):
                self.commands.extend(
                    [
                        "interface {subinterface}".format(subinterface=self.interface),
                        " bandwidth {newbw} kbps".format(newbw=self.newbw * 1024),
                        " description {description} ".format(description=self.description_new),
                        f" undo qos car inbound" if self.is_ratelimit else None,
                        f" undo qos car outbound" if self.is_ratelimit else None,
                        f" qos car {type1} cir {cir1:.0f} cbs {cbs1:.0f} pbs {pbs1:.0f} green pass yellow pass red discard" if self.is_ratelimit else None,
                        f" qos car {type2} cir {cir2:.0f} cbs {cbs2:.0f} pbs {pbs2:.0f} green pass yellow pass red discard" if self.is_ratelimit else None,
                        " quit",
                    ]
                )
        
        self.commands = [ x for x in self.commands if x is not None]

    
    def configuration(self, commit):
        if hasattr(self, "os"):
            self.view_configuration = []
            if self.os == "huawei" and hasattr(self, "commands"):
                prompt_output = self.child.after.decode("utf-8")
                run_step(child=self.child, 
                        command=f"system-view",
                        expected_output=r"\[\S+\]", 
                        step_name="CPE - system-view", 
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
                                expected_output=r"\[\S+\]", 
                                step_name="CPE - configuration", 
                                timeout=self.timeout, 
                                device="CPE"
                                )
                        configuration_output = self.child.before.decode("utf-8")
                        self.view_configuration.extend((prompt_output + configuration_output).splitlines())
                    
                    prompt_output = self.child.after.decode("utf-8")
                    run_step(child=self.child, 
                            command="quit",
                            expected_output=r"<[\w\-.]+>", 
                            step_name="CPE - configuration", 
                            timeout=self.timeout, 
                            device="CPE"
                            )
                    configuration_output = self.child.before.decode("utf-8")
                    self.view_configuration.extend((prompt_output + configuration_output).splitlines())
                    
                    prompt_output = self.child.after.decode("utf-8")
                    run_step(child=self.child, 
                            command="save",
                            expected_output=r"\[Y\/N\]:",
                            step_name="CPE - configuration", 
                            timeout=self.timeout, 
                            device="CPE"
                            )
                    configuration_output = self.child.before.decode("utf-8")
                    self.view_configuration.extend((prompt_output + configuration_output).splitlines())

                    prompt_output = self.child.after.decode("utf-8")
                    run_step(child=self.child, 
                            command="Y",
                            expected_output=r"\n<[\w\-.]+>", 
                            step_name="CPE - configuration", 
                            timeout=self.timeout, 
                            device="CPE"
                            )
                    configuration_output = self.child.before.decode("utf-8")
                    self.view_configuration.extend((prompt_output + configuration_output).splitlines())

                    prompt_output = self.child.after.decode("utf-8")
                    run_step(child=self.child, 
                            command=" ",
                            expected_output=r"<[\w\-.]+>", 
                            step_name="CPE - configuration", 
                            timeout=self.timeout, 
                            device="CPE"
                            )
                    configuration_output = self.child.before.decode("utf-8")
                    self.view_configuration.extend((prompt_output + configuration_output).splitlines())

                else:
                    prompt_output = self.child.after.decode("utf-8")
                    run_step(child=self.child, 
                            command="quit",
                            expected_output=r"<[\w\-.]+>", 
                            step_name="CPE - configuration", 
                            timeout=self.timeout, 
                            device="CPE"
                            )
                    configuration_output = self.child.before.decode("utf-8")
                    self.view_configuration.extend((prompt_output + configuration_output).splitlines())

                    prompt_output = self.child.after.decode("utf-8")
                    run_step(child=self.child, 
                            command=" ",
                            expected_output=r"<[\w\-.]+>", 
                            step_name="CPE - configuration", 
                            timeout=self.timeout, 
                            device="CPE"
                            )
                    configuration_output = self.child.before.decode("utf-8")
                    self.view_configuration.extend((prompt_output + configuration_output).splitlines())
                    
            elif self.os == "cisco" and hasattr(self, "commands"):
                prompt_output = self.child.after.decode("utf-8")
                run_step(child=self.child, 
                        command="configure terminal",
                        expected_output=r"\S+\#", 
                        step_name="CPE - system-view", 
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
                                expected_output=r"\S+\#", 
                                step_name="CPE - configuration", 
                                timeout=self.timeout, 
                                device="CPE"
                                )
                        configuration_output = self.child.before.decode("utf-8")
                        self.view_configuration.extend((prompt_output + configuration_output).splitlines())
                    
                    prompt_output = self.child.after.decode("utf-8")
                    run_step(child=self.child, 
                            command="exit",
                            expected_output=r"\S+\#", 
                            step_name="CPE - configuration", 
                            timeout=self.timeout, 
                            device="CPE"
                            )
                    configuration_output = self.child.before.decode("utf-8")
                    self.view_configuration.extend((prompt_output + configuration_output).splitlines())

                    prompt_output = self.child.after.decode("utf-8")
                    run_step(child=self.child, 
                            command="wr",
                            expected_output=r"\S+\#", 
                            step_name="CPE - configuration", 
                            timeout=self.timeout, 
                            device="CPE"
                            )
                    configuration_output = self.child.before.decode("utf-8")
                    self.view_configuration.extend((prompt_output + configuration_output).splitlines())

                    prompt_output = self.child.after.decode("utf-8")
                    run_step(child=self.child, 
                            command=" ",
                            expected_output=r"\S+\#", 
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
                            expected_output=r"\S+\#", 
                            step_name="CPE - configuration", 
                            timeout=self.timeout, 
                            device="CPE"
                            )
                    configuration_output = self.child.before.decode("utf-8")
                    self.view_configuration.extend((prompt_output + configuration_output).splitlines())

                    prompt_output = self.child.after.decode("utf-8")
                    run_step(child=self.child, 
                            command=" ",
                            expected_output=r"\S+\#", 
                            step_name="CPE - configuration", 
                            timeout=self.timeout, 
                            device="CPE"
                            )
                    configuration_output = self.child.before.decode("utf-8")
                    self.view_configuration.extend((prompt_output + configuration_output).splitlines())


        
    def exit(self):
        if self.os == "huawei":
            try:
                run_step(child=self.child, 
                        command="quit",
                        expected_output=r"\n<[\w\-.]+>", 
                        step_name="CPE - EXIT", 
                        timeout=self.timeout, 
                        device="CPE"
                        )
                    
            except CustomPexpectError as e:
                return e
            else:
                return self.child
            
        elif self.os == "cisco":
            try:
                run_step(child=self.child, 
                        command="exit",
                        expected_output=r"\n<[\w\-.]+>",
                        step_name="CPE - EXIT", 
                        timeout=self.timeout, 
                        device="CPE"
                        )
                    
            except CustomPexpectError as e:
                return e
            else:
                return self.child


class AgentACCESO(object):
    def __init__(self, child, username, password, acceso, vendor, timeout=30):
        self.child = child
        self.username = username
        self.password = password
        self.acceso = acceso
        self.vendor = vendor
        self.timeout = timeout
        self.os = None
        self.hostname = None 
        self.version = None
        self.subinterface = None
        self.trafficpolice_in = None
        self.trafficpolice_out = None
        self.ip = None

    def enter(self):
        try:
            pattern = re.compile("huawei", re.IGNORECASE)
            if  self.vendor and pattern.search(self.vendor) and self.acceso and self.acceso.lower().startswith("cmetro"):
                run_step(child=self.child, 
                        command=f"ssh -o StrictHostKeyChecking=no {self.username}@{self.acceso}", 
                        expected_output=r"[Pp]assword:", 
                        step_name="ACCESO - SSH", 
                        timeout=self.timeout, 
                        device="ACCESO"
                        )
                run_step(child=self.child, 
                        command=self.password,
                        expected_output=r"\n<[\w\-.]+>", 
                        step_name="ACCESO - PASSWORD", 
                        timeout=self.timeout,
                        device="ACCESO"
                        )
                self.os = "huawei"
                run_step(child=self.child, 
                        command=f"screen-length 0 temporary",
                        expected_output=r"\n<[\w\-.]+>", 
                        step_name="ACCESO - NO MORE", 
                        timeout=self.timeout, 
                        device="ACCESO"
                        )
                run_step(child=self.child, 
                        command=f"display version | include uptime",
                        expected_output=r"\n<[\w\-.]+>", 
                        step_name="ACCESO - VERSION", 
                        timeout=self.timeout, 
                        device="ACCESO"
                        )
                version_output = self.child.before.decode("utf-8")
                version_pattern = re.compile(r"\n(?P<version>.*?)(?=\s+uptime)")
                version_pattern_find = version_pattern.search(version_output)
                if version_pattern_find:
                    self.version = version_pattern_find.group("version")

                run_step(child=self.child, 
                        command=f"display current-configuration  | include sysname",
                        expected_output=r"\n<[\w\-.]+>", 
                        step_name="ACCESO - HOSTNAME", 
                        timeout=self.timeout, 
                        device="ACCESO"
                        )
                sysname_output = self.child.before.decode("utf-8")
                sysname_pattern = re.compile(r"\nsysname (?P<sysname>\S+)")
                sysname_pattern_find = sysname_pattern.search(sysname_output)
                if sysname_pattern_find:
                    self.hostname = sysname_pattern_find.group("sysname")
            else:
                return None
        except CustomPexpectError as e:
            return e
        else:
            return self.child

    def get_values(self, mac):
        if self.os == "huawei" and mac:
            try:
                run_step(child=self.child, 
                        command=f"display mac-address | i {mac}",
                        expected_output=r"\n<[\w\-.]+>", 
                        step_name="ACCESO - MAC", 
                        timeout=self.timeout, 
                        device="ACCESO"
                        )
                mac_output = self.child.before.decode("utf-8")
                mac_pattern = re.compile(rf'\n{mac} +\S+ +(?P<subinterface>\S+)')
                mac_pattern_find = mac_pattern.search(mac_output)
                if mac_pattern_find:
                    self.subinterface = mac_pattern_find.group("subinterface")
                
                    if not re.search(r"^\d+", self.subinterface):
                        self.subinterface = self.subinterface.replace("GE", "Gi")

                prompt = self.child.after.decode("utf-8")
                run_step(child=self.child, 
                        command=f"display curr int {self.subinterface}",
                        expected_output=r"\n<[\w\-.]+>", 
                        step_name="ACCESO - CONFIG SUB INTERFACE", 
                        timeout=self.timeout, 
                        device="ACCESO"
                        )
                interface_output = self.child.before.decode("utf-8")
                self.view_interface = (prompt + interface_output).splitlines()

                trafficpolice_in_pattern = re.compile(r'traffic-policy (?P<trafficpolice_in>\S+) inbound')
                trafficpolice_in_find = trafficpolice_in_pattern.search(interface_output)
                if trafficpolice_in_find:
                    self.trafficpolice_in = trafficpolice_in_find.group("trafficpolice_in")
 
                trafficpolice_out_pattern = re.compile(r'traffic-policy (?P<trafficpolice_out>\S+) outbound')
                trafficpolice_out_find = trafficpolice_out_pattern.search(interface_output)
                if trafficpolice_out_find:
                    self.trafficpolice_out = trafficpolice_out_find.group("trafficpolice_out")
                
                if self.trafficpolice_in:
                    prompt = self.child.after.decode("utf-8")
                    run_step(child=self.child, 
                            command=f"display curr configuration trafficpolicy {self.trafficpolice_in}",
                            expected_output=r"\n<[\w\-.]+>", 
                            step_name="ACCESO - CONFIG SUB TRAFFICPOLICE", 
                            timeout=self.timeout, 
                            device="ACCESO"
                            )
                    trafficpolice_in_output = self.child.before.decode("utf-8")
                    self.view_trafficpolice_in = (prompt + trafficpolice_in_output).splitlines()

                    classifier_in_pattern = re.compile(r'classifier (?P<classifier>[\S_]*?INTERNET[_\S]*?) behavior (?P<behavior>\w+)', flags=re.IGNORECASE)
                    classifier_in_find = classifier_in_pattern.search(trafficpolice_in_output)
                    if classifier_in_find:
                        self.classifier_in = classifier_in_find.group("classifier")
                        self.behavior_in = classifier_in_find.group("behavior")
                    
                if self.trafficpolice_out:
                    prompt = self.child.after.decode("utf-8")
                    run_step(child=self.child, 
                            command=f"display curr configuration trafficpolicy {self.trafficpolice_out}",
                            expected_output=r"\n<[\w\-.]+>", 
                            step_name="ACCESO - CONFIG SUB TRAFFICPOLICE", 
                            timeout=self.timeout, 
                            device="ACCESO"
                            )
                    trafficpolice_out_output = self.child.before.decode("utf-8")
                    self.view_trafficpolice_out = (prompt + trafficpolice_out_output).splitlines()

                    classifier_out_pattern = re.compile(r'classifier (?P<classifier>[\S_]*?INTERNET[_\S]*?) behavior (?P<behavior>\w+)', flags=re.IGNORECASE)
                    classifier_out_find = classifier_out_pattern.search(trafficpolice_out_output)
                    if classifier_out_find:
                        self.classifier_out = classifier_out_find.group("classifier")
                        self.behavior_out = classifier_out_find.group("behavior")


            except CustomPexpectError as e:
                return e
            else:
                return self.child

    def analizar(self, upgrade):
        self.upgrade = upgrade
        self.newbw = self.upgrade * 1024
        self.cbs_pbs = int((self.newbw / 8) * 1.5 * 1000)
        self.by_interface_in = False
        self.by_interface_out = False

        if self.os == "huawei" and self.trafficpolice_in and self.trafficpolice_out:
            if re.search("(\d+\/\d+\/\d+)", self.trafficpolice_in):
                self.by_interface_in = True
                self.trafficpolice_new_in = self.trafficpolice_in
            else:
                self.trafficpolice_new_in = re.sub("\d+", f"{self.newbw}", self.trafficpolice_in)

            if re.search("(\d+\/\d+\/\d+)", self.trafficpolice_out):
                self.by_interface_out = True
                self.trafficpolice_new_out = self.trafficpolice_out
            else:
                self.trafficpolice_new_out = re.sub("\d+", f"{self.newbw}", self.trafficpolice_out)

            self.behavior_in_new = re.sub("\d+", f"{self.newbw}", self.behavior_in)
            self.behavior_out_new = re.sub("\d+", f"{self.newbw}", self.behavior_out)
        
        if self.os == "huawei" and self.trafficpolice_in and self.trafficpolice_out and self.behavior_in_new and self.behavior_out_new:
            prompt = self.child.after.decode("utf-8")
            run_step(child=self.child, 
                    command=f"display curr configuration trafficpolicy {self.trafficpolice_new_in}",
                    expected_output=r"\n<[\w\-.]+>", 
                    step_name="ACCESO - CONFIG TRAFFICPOLICE NEW", 
                    timeout=self.timeout, 
                    device="ACCESO"
                    )
            trafficpolice_new_in_output = self.child.before.decode("utf-8")
            self.view_trafficpolice_new_in = (prompt + trafficpolice_new_in_output).splitlines()

            output_trafficpolicy_in_pattern = re.search(rf'traffic policy {self.trafficpolice_new_in}', trafficpolice_new_in_output)
            if output_trafficpolicy_in_pattern:
                self.trafficpolice_new_in_created = True
            else:
                self.trafficpolice_new_in_created = False
            
            classifier_new_in_pattern = re.compile(rf'classifier {self.classifier_in} behavior {self.behavior_in_new}')
            classifier_new_in_find = classifier_new_in_pattern.search(trafficpolice_new_in_output)
            if classifier_new_in_find:
                self.classifier_new_in_created = True
            else:
                self.classifier_new_in_created = False

            output_trafficpolicy_in_pattern = re.search(rf'traffic policy {self.trafficpolice_new_in}', trafficpolice_new_in_output)
            if output_trafficpolicy_in_pattern and self.classifier_new_in_created:
                self.trafficpolice_new_in_created = True
            else:
                self.trafficpolice_new_in_created = False
            
            prompt = self.child.after.decode("utf-8")
            run_step(child=self.child, 
                    command=f"display curr configuration behavior {self.behavior_in_new}",
                    expected_output=r"\n<[\w\-.]+>", 
                    step_name="ACCESO - BEHAVIOR NEW", 
                    timeout=self.timeout, 
                    device="ACCESO"
                    )
            behavior_in_new_output = self.child.before.decode("utf-8")
            self.view_behavior_new_in = (prompt + behavior_in_new_output).splitlines()

            behavior_in_new_name_pattern = re.compile(f"traffic behavior {self.behavior_in_new}")
            behavior_in_new_name_find = behavior_in_new_name_pattern.search(behavior_in_new_output)
            if behavior_in_new_name_find:
                self.classifier_new_in_created = True
            
            behavior_in_new_pattern = re.compile(f"car cir {self.newbw} ")
            behavior_in_new_find = behavior_in_new_pattern.search(behavior_in_new_output)
            if behavior_in_new_find:
                self.carcir_in = True
            else:
                self.carcir_in = False

            prompt = self.child.after.decode("utf-8")
            run_step(child=self.child, 
                    command=f"display curr configuration trafficpolicy {self.trafficpolice_new_out}",
                    expected_output=r"\n<[\w\-.]+>", 
                    step_name="ACCESO - CONFIG TRAFFICPOLICE NEW", 
                    timeout=self.timeout, 
                    device="ACCESO"
                    )
            trafficpolice_new_out_output = self.child.before.decode("utf-8")
            self.view_trafficpolice_new_out = (prompt + trafficpolice_new_out_output).splitlines()

            classifier_new_out_pattern = re.compile(rf'classifier {self.classifier_out} behavior {self.behavior_out_new}')
            classifier_new_out_find = classifier_new_out_pattern.search(trafficpolice_new_out_output)
            if classifier_new_out_find:
                self.classifier_new_out_created = True
            else:
                self.classifier_new_out_created = False

            output_trafficpolicy_out_pattern = re.search(rf'traffic policy {self.trafficpolice_new_out}', trafficpolice_new_out_output)
            if output_trafficpolicy_out_pattern and self.classifier_new_out_created:
                self.trafficpolice_new_out_created = True
            else:
                self.trafficpolice_new_out_created = False


            prompt = self.child.after.decode("utf-8")
            run_step(child=self.child, 
                    command=f"display curr configuration behavior {self.behavior_out_new}",
                    expected_output=r"\n<[\w\-.]+>", 
                    step_name="ACCESO - BEHAVIOR NEW", 
                    timeout=self.timeout, 
                    device="ACCESO"
                    )
            behavior_out_new_output = self.child.before.decode("utf-8")
            self.view_behavior_new_out = (prompt + behavior_out_new_output).splitlines()

            behavior_out_new_name_pattern = re.compile(f"traffic behavior {self.behavior_out_new}")
            behavior_out_new_name_find = behavior_out_new_name_pattern.search(behavior_out_new_output)
            if behavior_out_new_name_find:
                self.classifier_new_out_created = True

            behavior_out_new_pattern = re.compile(f"car cir {self.newbw} ")
            behavior_out_new_find = behavior_out_new_pattern.search(behavior_out_new_output)
            if behavior_out_new_find:
                self.carcir_out = True
            else:
                self.carcir_out = False

        if self.os == "huawei":
            run_step(child=self.child, 
                    command=f"display current-configuration | inc traffic policy",
                    expected_output=r"\n<[\w\-.]+>", 
                    step_name="ACCESO - COUNT traffic policy", 
                    timeout=self.timeout, 
                    device="ACCESO"
                    )
            trafficpolice_count_output = self.child.before.decode("utf-8")
            trafficpolice_count_pattern= re.compile(f"traffic policy (\S+)")
            trafficpolice_count_find = trafficpolice_count_pattern.findall(trafficpolice_count_output)
            if len(trafficpolice_count_find) <= 254:
                self.trafficpolice_count_find = len(trafficpolice_count_find)
                self.trafficpolice_count = True

    def create_commands(self):
        self.commands = []
        if self.os == "huawei" and self.newbw:
            if hasattr(self, "classifier_new_in_created") and not self.classifier_new_in_created and not self.carcir_in:
                self.commands.extend(
                    [
                    "traffic behavior {behavior}".format(behavior=self.behavior_in_new),
                    " remark dscp default",
                    " car cir {bw} pir {bw} cbs {cbs_pbs} pbs {cbs_pbs} green pass yellow pass red discard".format(bw=self.newbw, cbs_pbs=self.cbs_pbs),
                    " statistic enable",
                    " quit",
                    ]
                )
                self.classifier_new_in_created = True
            else:
                if hasattr(self, "carcir_in") and not self.carcir_in:
                    self.send_email_carcir_in = True

            if hasattr(self, "classifier_new_out_created") and not self.classifier_new_out_created and not self.carcir_out:
                self.commands.extend(
                    [
                    "traffic behavior {behavior}".format(behavior=self.behavior_out_new),
                    " remark dscp default",
                    " car cir {bw} pir {bw} cbs {cbs_pbs} pbs {cbs_pbs} green pass yellow pass red discard".format(bw=self.newbw, cbs_pbs=self.cbs_pbs),
                    " statistic enable",
                    " quit",
                    ]
                )
                self.classifier_new_out_created = True
            else:
                if hasattr(self, "carcir_out") and self.carcir_out:
                    self.send_email_carcir_out = True

            if hasattr(self, "classifier_new_in_created") and self.classifier_new_in_created:
                if hasattr(self, "trafficpolice_new_in_created") and not self.trafficpolice_new_in_created:
                    self.commands.extend(
                        [
                            "traffic policy {trafficpolice}".format(trafficpolice=self.trafficpolice_new_in),
                            " classifier {classifier} behavior {behavior}".format(classifier=self.classifier_in, behavior=self.behavior_in_new),
                            " quit",
                        ]
                    )
                    self.trafficpolice_new_in_created = True

            if hasattr(self, "classifier_new_out_created") and self.classifier_new_out_created:
                if hasattr(self, "trafficpolice_new_out_created") and not self.trafficpolice_new_out_created:
                    self.commands.extend(
                        [
                            "traffic policy {trafficpolice}".format(trafficpolice=self.trafficpolice_new_out),
                            " classifier {classifier} behavior {behavior}".format(classifier=self.classifier_out, behavior=self.behavior_out_new),
                            " quit",
                        ]
                    )
                    self.trafficpolice_new_out_created = True

            if hasattr(self, "trafficpolice_new_in_created") and hasattr(self, "trafficpolice_new_out_created"):
                if self.trafficpolice_new_in_created or self.trafficpolice_new_out_created:
                    self.commands.extend(
                        [
                            "interface {subinterface}".format(subinterface=self.subinterface),
                            " undo traffic-policy inbound",
                            " undo traffic-policy outbound",
                            " traffic-policy {trafficpolicy_in} inbound".format(trafficpolicy_in=self.trafficpolice_new_in),
                            " traffic-policy {trafficpolicy_out} outbound".format(trafficpolicy_out=self.trafficpolice_new_out),
                            " quit",
                        ]
                    )

    def configuration(self, commit):
        if hasattr(self, "os"):
            self.view_configuration = []
            if self.os == "huawei" and hasattr(self, "commands"):
                prompt = self.child.after.decode("utf-8")
                run_step(child=self.child, 
                        command=f"system-view",
                        expected_output=r"\[\S+\]", 
                        step_name="ACCESO - system-view", 
                        timeout=self.timeout, 
                        device="ACCESO"
                        )
                output = self.child.before.decode("utf-8")
                self.view_configuration.extend((prompt + output).splitlines())
                
                if commit == "Y":
                    for command in self.commands:
                        prompt = self.child.after.decode("utf-8")
                        run_step(child=self.child, 
                                command=command,
                                expected_output=r"\[\S+\]", 
                                step_name="ACCESO - configuration", 
                                timeout=self.timeout, 
                                device="ACCESO"
                                )
                        output = self.child.before.decode("utf-8")
                        self.view_configuration.extend((prompt + output).splitlines())
                    
                    prompt = self.child.after.decode("utf-8")
                    run_step(child=self.child, 
                            command="quit",
                            expected_output=r"<[\w\-.]+>", 
                            step_name="ACCESO - configuration", 
                            timeout=self.timeout, 
                            device="ACCESO"
                            )
                    output = self.child.before.decode("utf-8")
                    self.view_configuration.extend((prompt + output).splitlines())
                    
                    prompt = self.child.after.decode("utf-8")
                    run_step(child=self.child, 
                            command="save",
                            expected_output=r"\[Y\/N\]:?", 
                            step_name="ACCESO - configuration", 
                            timeout=self.timeout, 
                            device="ACCESO"
                            )
                    output = self.child.before.decode("utf-8")
                    self.view_configuration.extend((prompt + output).splitlines())

                    prompt = self.child.after.decode("utf-8")
                    run_step(child=self.child, 
                            command="Y",
                            expected_output=r"\n<[\w\-.]+>", 
                            step_name="ACCESO - configuration", 
                            timeout=self.timeout, 
                            device="ACCESO"
                            )
                    output = self.child.before.decode("utf-8")
                    self.view_configuration.extend((prompt + output).splitlines())

                    prompt = self.child.after.decode("utf-8")
                    run_step(child=self.child, 
                            command=" ",
                            expected_output=r"\n<[\w\-.]+>", 
                            step_name="ACCESO - configuration", 
                            timeout=self.timeout, 
                            device="ACCESO"
                            )
                    output = self.child.before.decode("utf-8")
                    self.view_configuration.extend((prompt + output).splitlines())

                else:
                    prompt = self.child.after.decode("utf-8")
                    run_step(child=self.child, 
                            command="quit",
                            expected_output=r"<[\w\-.]+>", 
                            step_name="ACCESO - configuration", 
                            timeout=self.timeout, 
                            device="ACCESO"
                            )
                    output = self.child.before.decode("utf-8")
                    self.view_configuration.extend((prompt + output).splitlines())

                    prompt = self.child.after.decode("utf-8")
                    run_step(child=self.child, 
                            command=" ",
                            expected_output=r"<[\w\-.]+>", 
                            step_name="ACCESO - configuration", 
                            timeout=self.timeout, 
                            device="ACCESO"
                            )
                    output = self.child.before.decode("utf-8")
                    self.view_configuration.extend((prompt + output).splitlines())
                    


    def exit(self):
        if self.os == "huawei":
            try:
                run_step(child=self.child, 
                        command="quit",
                        expected_output=r"~\]\$\s*$", 
                        step_name="ACCESO - EXIT", 
                        timeout=self.timeout, 
                        device="ACCESO"
                        )
                    
            except CustomPexpectError as e:
                return e
            else:
                return self.child


def proceso(user_tacacs, pass_tacacs, cid_list, now, commit):
    load_dotenv(override=True)
    CYBERARK_USER = os.getenv("CYBERARK_USER")
    CYBERARK_PASS = os.getenv("CYBERARK_PASS")
    CYBERARK_IP = os.getenv("CYBERARK_IP")
    CRT_IP = os.getenv("CRT_IP")
    CRT_USER = os.getenv("CRT_USER")
    ROUTER_PRIMARIO = os.getenv("ROUTER_PRIMARIO")
    result = []
    enter_toserver = EnterToServer(CYBERARK_IP, CYBERARK_USER, CYBERARK_PASS, "media/internet_upgrade", now, CRT_USER, CRT_IP, 30)
    server = enter_toserver.enter()
    enter_toserver.get_values()
    if isinstance(server, pexpect.pty_spawn.spawn):
        for item in cid_list:
            cid = item["cid"]
            newbw = item["newbw"]
            action = item["action"]
            item["commit"] = commit

            enterInPolo = AgentPolo(server, user_tacacs, pass_tacacs, ROUTER_PRIMARIO, cid)
            enterInPolo.get_wan()
            enterInPolo.get_PE()
            
            enterInPE = AgentPE(server, user_tacacs, pass_tacacs, enterInPolo.pe, action, is_wanprivade=enterInPolo.is_wanprivade)
            inPE = enterInPE.enter()
            enterInPE.get_values(wan=enterInPolo.wan)
            enterInPE.analizar(upgrade=newbw)
            enterInPE.create_commands()
            enterInPE.configuration(commit=commit)
            data_PE = {
                "os": enterInPE.os if hasattr(enterInPE, "os") else None,
                "ip": enterInPE.ip if hasattr(enterInPE, "ip") else None,
                "device": enterInPE.device if hasattr(enterInPE, "device") else None,
                "version": enterInPE.version if hasattr(enterInPE, "version") else None,
                "hostname": enterInPE.hostname if hasattr(enterInPE, "hostname") else None,
                "subinterface": enterInPE.subinterface if hasattr(enterInPE, "subinterface") else None,
                "newbw": enterInPE.newbw if hasattr(enterInPE, "newbw") else None,
                "umbral": enterInPE.umbral if hasattr(enterInPE, "umbral") else None,
                "lt_umbral_value": enterInPE.lt_umbral_value if hasattr(enterInPE, "lt_umbral_value") else None,
                "interface_ip": enterInPE.interface_ip if hasattr(enterInPE, "interface_ip") else None,
                "interface_mask": enterInPE.interface_mask if hasattr(enterInPE, "interface_mask") else None,
                "is_mask30": enterInPE.is_mask30 if hasattr(enterInPE, "is_mask30") else None,
                "trafficpolice_in": enterInPE.trafficpolice_in if hasattr(enterInPE, "trafficpolice_in") else None,
                "trafficpolice_out": enterInPE.trafficpolice_out if hasattr(enterInPE, "trafficpolice_out") else None,
                "capacidad_inMegas": enterInPE.capacidad if hasattr(enterInPE, "capacidad") else None,
                "in_trunk": enterInPE.in_trunk if hasattr(enterInPE, "in_trunk") else None,
                "link": enterInPE.link if hasattr(enterInPE, "link") else None,
                "input_peak": enterInPE.input_peak if hasattr(enterInPE, "input_peak") else None,
                "output_peak": enterInPE.output_peak if hasattr(enterInPE, "output_peak") else None,
                "input_peak_porcentaje": enterInPE.input_peak_porcentaje if hasattr(enterInPE, "input_peak_porcentaje") else None,
                "output_peak_porcentaje": enterInPE.output_peak_porcentaje if hasattr(enterInPE, "output_peak_porcentaje") else None,
                "message": enterInPE.message if hasattr(enterInPE, "message") else None,
                "commands": enterInPE.commands if hasattr(enterInPE, "commands") else None,
                "view_subinterface": enterInPE.view_subinterface if hasattr(enterInPE, "view_subinterface") else None,
                "view_trafficpolice_in": enterInPE.view_trafficpolice_in if hasattr(enterInPE, "view_trafficpolice_in") else None,
                "view_trafficpolice_out": enterInPE.view_trafficpolice_out if hasattr(enterInPE, "view_trafficpolice_out") else None,
                "view_behavior_new_in": enterInPE.view_behavior_new_in if hasattr(enterInPE, "view_behavior_new_in") else None,
                "view_behavior_new_out": enterInPE.view_behavior_new_out if hasattr(enterInPE, "view_behavior_new_out") else None,
                "view_trafficpolice_new_in": enterInPE.view_trafficpolice_new_in if hasattr(enterInPE, "view_trafficpolice_new_in") else None,
                "view_trafficpolice_new_out": enterInPE.view_trafficpolice_new_out if hasattr(enterInPE, "view_trafficpolice_new_out") else None,
                "view_configuration": enterInPE.view_configuration if hasattr(enterInPE, "view_configuration") else None,
            }

            enterInCPE = AgentCPE(inPE, user_tacacs, pass_tacacs, enterInPolo.wan)
            if not enterInPE.is_mask30 and enterInPE.subinterface:
                enterInCPE.enter()
                enterInCPE.get_values()
                enterInCPE.analizar(newbw)
                enterInCPE.create_commands()
                enterInCPE.configuration(commit=commit)
                enterInCPE.exit()
            data_CPE = {
                "os": enterInCPE.os if hasattr(enterInCPE, "os") else None,
                "ip": enterInCPE.ip if hasattr(enterInCPE, "ip") else None,
                "hostname": enterInCPE.hostname if hasattr(enterInCPE, "hostname") else None,
                "bandwidth": enterInCPE.bandwidth if hasattr(enterInCPE, "bandwidth") else None,
                "description": enterInCPE.description if hasattr(enterInCPE, "description") else None,
                "version": enterInCPE.version if hasattr(enterInCPE, "version") else None,
                "newbw": enterInCPE.newbw if hasattr(enterInCPE, "newbw") else None,
                "description_new": enterInCPE.description_new if hasattr(enterInCPE, "description_new") else None,
                "is_ratelimit": enterInCPE.is_ratelimit if hasattr(enterInCPE, "is_ratelimit") else None,
                "ratelimit": enterInCPE.ratelimit if hasattr(enterInCPE, "ratelimit") else None,
                "commands": enterInCPE.commands if hasattr(enterInCPE, "commands") else None,
                "view_interface": enterInCPE.view_interface if hasattr(enterInCPE, "view_interface") else None,
                "view_configuration": enterInCPE.view_configuration if hasattr(enterInCPE, "view_configuration") else None,
            }
            enterInPE.exit()

            enterInACCESO = AgentACCESO(server, user_tacacs, pass_tacacs, enterInPE.lldp, enterInPE.lldp_vendor)
            enterInACCESO.enter()
            enterInACCESO.get_values(enterInPE.mac)
            enterInACCESO.analizar(newbw)
            
            if not enterInCPE.is_ratelimit:
                enterInACCESO.create_commands()
                enterInACCESO.configuration(commit=commit)
            
            data_ACCESO = {
                "os": enterInACCESO.os if hasattr(enterInACCESO, "os") else None,
                "hostname": enterInACCESO.hostname if hasattr(enterInACCESO, "hostname") else None,
                "ip": enterInACCESO.ip if hasattr(enterInACCESO, "ip") else None,
                "version": enterInACCESO.version if hasattr(enterInACCESO, "version") else None,
                "acceso_lldp": enterInACCESO.acceso if hasattr(enterInACCESO, "acceso") else None,
                "acceso_lldp_vendor": enterInACCESO.vendor if hasattr(enterInACCESO, "vendor") else None,
                "subinterface": enterInACCESO.subinterface if hasattr(enterInACCESO, "subinterface") else None,
                "trafficpolice_in": enterInACCESO.trafficpolice_in if hasattr(enterInACCESO, "trafficpolice_in") else None,
                "trafficpolice_out": enterInACCESO.trafficpolice_out if hasattr(enterInACCESO, "trafficpolice_out") else None,
                "behavior_in": enterInACCESO.behavior_in if hasattr(enterInACCESO, "behavior_in") else None,
                "behavior_out": enterInACCESO.behavior_out if hasattr(enterInACCESO, "behavior_out") else None,
                "classifier_in": enterInACCESO.classifier_in if hasattr(enterInACCESO, "classifier_in") else None,
                "classifier_out": enterInACCESO.classifier_out if hasattr(enterInACCESO, "classifier_out") else None,
                "trafficpolice_new_in": enterInACCESO.trafficpolice_new_in if hasattr(enterInACCESO, "trafficpolice_new_in") else None,
                "trafficpolice_new_out": enterInACCESO.trafficpolice_new_out if hasattr(enterInACCESO, "trafficpolice_new_out") else None,
                "behavior_in_new": enterInACCESO.behavior_in_new if hasattr(enterInACCESO, "behavior_in_new") else None,
                "behavior_out_new": enterInACCESO.behavior_out_new if hasattr(enterInACCESO, "behavior_out_new") else None,
                "traffic_count_find": enterInACCESO.trafficpolice_count_find if hasattr(enterInACCESO, "trafficpolice_count_find") else None,
                "commands": enterInACCESO.commands if hasattr(enterInACCESO, "commands") else None,
                "view_interface": enterInACCESO.view_interface if hasattr(enterInACCESO, "view_interface") else None,
                "view_trafficpolice_in": enterInACCESO.view_trafficpolice_in if hasattr(enterInACCESO, "view_trafficpolice_in") else None,
                "view_trafficpolice_out": enterInACCESO.view_trafficpolice_out if hasattr(enterInACCESO, "view_trafficpolice_out") else None,
                "view_trafficpolice_new_in": enterInACCESO.view_trafficpolice_new_in if hasattr(enterInACCESO, "view_trafficpolice_new_in") else None,
                "view_trafficpolice_new_out": enterInACCESO.view_trafficpolice_new_out if hasattr(enterInACCESO, "view_trafficpolice_new_out") else None,
                "view_behavior_new_in": enterInACCESO.view_behavior_new_in if hasattr(enterInACCESO, "view_behavior_new_in") else None,
                "view_behavior_new_out": enterInACCESO.view_behavior_new_out if hasattr(enterInACCESO, "view_behavior_new_out") else None,
                "view_configuration": enterInACCESO.view_configuration if hasattr(enterInACCESO, "view_configuration") else None,
            }
            enterInACCESO.exit()

            item["device_pe"] = data_PE
            item["device_cpe"] = data_CPE
            item["device_acceso"] = data_ACCESO
            result.append(item)
        enter_toserver.exit()
    return result


