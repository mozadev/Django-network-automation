import pandas as pd
import logging
import re


logger = logging.getLogger(__name__)    

def process_anexos(data):
    columns = [
        "key", 
        "login", 
        "firstName", 
        "handle", 
        "location", 
        "ipAddress", 
        "deviceMac", 
        "deviceModel", 
        "deviceSerial"
        ]
    try:
        datos = pd.read_csv(data, usecols=columns, sep=",")
        datos["status"] = datos["key"].apply(get_status)
        datos["login"] = datos["login"].apply(sub_correo)
        datos["key_only"] = datos["login"].apply(get_anexo_of_login)
        datos.drop("key", axis=1, inplace=True)
        datos.rename(columns={
           "firstName": "first_name",
           "ipAddress": "ip_address",
           "deviceMac": "device_mac",
           "deviceModel": "device_model",
           "deviceSerial": "device_serial",
           "key_only": "key",
        }, inplace=True)
        datos = datos.where(pd.notnull(datos), None)

    except ValueError as e:
        logger.error(f"{e}")
        raise e
    else:
        result = datos.to_dict(orient="records")
        return result
    

def get_key(key):
  search = re.search("^(?P<key>\d+)__", key)
  if search:
    return  int(search.group("key"))
  else:
    return None

def get_status(key):
  search = re.search("__(?P<status>\S+)", key)
  if search:
    return  True
  else:
    return False
  
def sub_correo(login):
    if login:
      return re.sub("@\S+", "@mpfn.gob.pe", login)
    else:
       return None
    
def get_anexo_of_login(login):
  search = re.compile(r"(?P<anexo>\d+)@")
  match = search.search(login)
  return match.group("anexo") if match else None
