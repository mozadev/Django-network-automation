from docxtpl import DocxTemplate
from pathlib import Path
import pandas as pd
import re
import numpy as np

class CreateInforme(object):

    def __init__(self, template, data, now):
        self.template = template
        self.data = data
        self.name = "media/informes/{now}.docx".format(now=now)

    def create(self):
        doc = DocxTemplate(self.template)
       

        self.context = {
            "titulo": self.data["titulo"],
            "cliente": self.data["cliente"],
            "reportes": self.apply_clean_format(self.data["reportes"]) 

        }
        doc.render(self.context)
        doc.save(self.name)
        return self.name


    def apply_clean_format(self, reportes):

        # Se utiliza una list comprehension para generar una nueva lista de reportes.
        # Si en un reporte existe 'it_medidas_tomadas' y es una cadena, se actualiza esa clave.
        return [
                {**reporte,
                  "it_medidas_tomadas": self.remove_last_lines(
                    reporte["it_medidas_tomadas"]
                    )
                }
                if "it_medidas_tomadas" in reporte and isinstance(reporte["it_medidas_tomadas"],str) 
                else reporte
                for reporte in reportes
            ]
    
    def remove_last_lines(self, text):
        """
        Removes the last two lines if they contain dates or specific keywords.
        """
       
        DATE_PATTERN = re.compile(
         r"(?i)^\s*fecha\s*y\s*hora\s*(de\s*)?(inicio|fin)?:?\s*\d{1,2}/\d{1,2}/\d{4}\s*\d{1,2}:\d{2}\s*$"
        )
        lines = text.split("\n") 

        while lines and DATE_PATTERN.search(lines[-1].strip()):
            lines.pop()

        cleaned_text = "\n".join(lines)

        return cleaned_text 


def validate_required_columns_from_excel(excel_file):
   
    required_columns = [
        'nro_incidencia', # ticket
        'canal_ingreso', # tipo generacion ticket
        'interrupcion_inicio',  # fecha/hora interrupcion
        'fecha_generacion', # fecha/hora generacion
        'interrupcion_fin',  # fecha/ hora subsanacion
        'cid', # CID
        'tipo_caso', # Tipo Caso
        'tipificacion_problema', #averia
        'it_determinacion_de_la_causa', # DETERMINACION DE LA CAUSA
        'it_medidas_tomadas', # MEDIDAS CORRECTIVAS Y/O PREVENTIVAS TOMADAS
        'it_conclusiones', # RECOMENDACIONES
        'tiempo_interrupcion', #tiempo subsanacion efectivo
        'tipificacion_interrupcion', # tiempo de indisponibilidad,
        'tipificacion_tipo' # ATRIBUIBLE

        
    ]
    try:
        df = pd.read_excel(excel_file, dtype=str, engine="openpyxl")
    except Exception as e:
        raise ValueError(f"Error 400: Could not read Excel file: {str(e)}")
    
    df.columns = df.columns.str.strip()

    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        error_message = [
        f"Error 400: Columnas requeridas faltantes en el archivo Excel. "
        f"Columnas faltantes: {missing_columns}",
        "Por favor, compruebe que los nombres de las columnas de su archivo Excel coinciden exactamente."
        ]
        raise ValueError(error_message)
    
    df_clean = df[required_columns].apply(
        lambda col: col.str.replace("_x000D_", "", regex=False).str.strip()
    ).fillna("-")

    return df_clean

def create_reportes_by_ticket_by_client(df):

    df['canal_ingreso'] = df['canal_ingreso'].replace({
        'e-mail': 'Reportado por el usuario',
        'Telefono': 'Reportado por el usuario',
        'Interno': 'Reportado por el usuario'
       })
    
    df['fecha_hora_solicitud'] = np.where(df['canal_ingreso'] == 'Proactivo', '-', 'Por definir') 

    df['fecha_hora_llegada_personal'] = "-"
    df['tiempo_llegada_personal'] = "-"
    df['horas_excedidas_plazo_reparacion_bases'] = 0
    df['descripcion_problema'] = 'Se detectó la pérdida de gestión del servicio en los Sistemas de Monitoreo de Claro.'
    
    df['interrupcion_inicio'] = pd.to_datetime(df['interrupcion_inicio'], errors='coerce')
    df['fecha_generacion'] = pd.to_datetime(df['fecha_generacion'], errors='coerce')
    df['interrupcion_fin'] = pd.to_datetime(df['interrupcion_fin'], errors='coerce')

    df_sorted = df.sort_values(by='interrupcion_inicio', ascending=True)

    df_sorted['interrupcion_inicio'] = df_sorted['interrupcion_inicio'].dt.strftime('%d/%m/%Y %H:%M')
    df_sorted['fecha_generacion'] = df_sorted['fecha_generacion'].dt.strftime('%d/%m/%Y %H:%M')
    df_sorted['interrupcion_fin'] = df_sorted['interrupcion_fin'].dt.strftime('%d/%m/%Y %H:%M')

    df_sorted['tipificacion_problema'] = df_sorted['tipificacion_problema'].str.split('-').str[0].str.strip()
    
    df_sorted["tipificacion_problema"] = df_sorted["tipificacion_problema"].apply(
    lambda x: "PROBLEMA DE ENERGIA COMERCIAL EN SITE/POP" if "PROBLEMA DE ENERGIA COMERCIAL EN SITE/POP" in x else x
)   
    
    df_sorted['tipificacion_tipo'] = df_sorted['tipificacion_tipo'].replace({
        'CLARO - DEGRADACION': 'CLARO', 
        'TERCEROS - CORTE' : 'TERCEROS'
       })
   
    
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
    file_path_sedes = BASE_DIR / "media" / "pronatel" / "sedes" / "RELACIÓN DE CADs CON CID.xlsx"

    if not  file_path_sedes.exists():
            raise FileNotFoundError(f" File not found {file_path_sedes}")
    
    df_sedes_by_cid = pd.read_excel(file_path_sedes)

    df_sorted["cid"] = df_sorted["cid"].astype(str)  
    df_sedes_by_cid["cid"] = df_sedes_by_cid["cid"].astype(str)
    
    df_sorted = df_sorted.merge(df_sedes_by_cid, on="cid", how="left")

    return df_sorted.to_dict(orient="records")


