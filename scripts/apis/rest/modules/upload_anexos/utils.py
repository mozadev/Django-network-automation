import pandas as pd
import json

def clean_data(file, fecha):
    data = pd.read_csv(file, sep=",", usecols=["key", "login"])
    print(data)
    if data.isnull().sum().sum() == 0:
        data_key = data["key"].str.split(pat="__", expand=True).rename(columns={0: "key", 1: "status"})
        data_login = data["login"].str.split(pat="@", expand=True).rename(columns={0: "anexo", 1: "dominio"})
        data_result = pd.concat([data_key, data_login], axis=1)
        data_result["status"] = data_result["status"].apply(status_anexo)
        data_result.drop(columns=["dominio"], inplace=True)

        if pd.Timestamp(fecha).tzinfo is None:
            fecha = pd.Timestamp(fecha).tz_localize('America/Lima')
        else:
            fecha = pd.Timestamp(fecha).tz_convert('America/Lima')

        data_result["registro"] = fecha
        
        return data_result.to_dict(orient="records"), 200
    else:
        return "ERROR: Valores nulos encontrados", 404
    

def status_anexo(item):
  if item:
    return True
  else:
    return False 
 