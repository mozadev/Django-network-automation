from docxtpl import DocxTemplate
import re
import pandas as pd

class CreateInforme:
    def __init__(self, template, data, now):
        self.template = template
        self.data = data
        self.name = f"media/informes/{now}.docx"

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
        DATE_PATTERN = re.compile(
            r"(?i)^\s*fecha\s*y\s*hora\s*(de\s*)?(inicio|fin)?:?\s*\d{1,2}/\d{1,2}/\d{4}\s*\d{1,2}:\d{2}\s*$"
        )
        lines = text.split("\n")

        while lines and DATE_PATTERN.search(lines[-1].strip()):
            lines.pop()

        return "\n".join(lines)
    
def validate_required_columns_from_excel(excel_file):
    required_columns = [
        'nro_incidencia',  # ticket
        'canal_ingreso',  # tipo generacion ticket
        'interrupcion_inicio',  # fecha/hora interrupcion
        'fecha_generacion',  # fecha/hora generacion
        'interrupcion_fin',  # fecha/ hora subsanacion
        'cid',  # CID
        'tipo_caso',  # Tipo Caso
        'tipificacion_problema',  # averia
        'it_determinacion_de_la_causa',  # DETERMINACION DE LA CAUSA
        'it_medidas_tomadas',  # MEDIDAS CORRECTIVAS Y/O PREVENTIVAS TOMADAS
        'it_conclusiones',  # RECOMENDACIONES
        'tiempo_interrupcion',  # tiempo subsanacion efectivo
        'tipificacion_interrupcion',  # tiempo de indisponibilidad
        'tipificacion_tipo',  # ATRIBUIBLE
        'fecha_comunicacion_cliente'  # Fecha hora solicitud  
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




