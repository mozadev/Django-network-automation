from docxtpl import DocxTemplate
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
            "reportes": self.apply_centered_format(self.data["reportes"]) 

        }
        doc.render(self.context)
        doc.save(self.name)
        return self.name

    def apply_centered_format(self, reportes):
        """
        Aplica centrado en las dos últimas líneas de la columna 'it_medidas_tomadas' dentro de cada ticket.
        """
        # Se utiliza una list comprehension para generar una nueva lista de reportes.
        # Si en un reporte existe 'it_medidas_tomadas' y es una cadena, se actualiza esa clave.
        return [
                {**reporte, "it_medidas_tomadas": self.center_last_lines(reporte["it_medidas_tomadas"])}
                if "it_medidas_tomadas" in reporte and isinstance(reporte["it_medidas_tomadas"],str) 
                else reporte
                for reporte in reportes
            ]

    def center_last_lines(self, text):
            """
            Centra solo las dos últimas líneas del texto en la columna 'it_medidas_tomadas'.
            """
            lines = text.split("\n")  

            if len(lines) >= 3:
                # Si la antepenúltima línea no está vacía (después de eliminar espacios) se inserta una línea vacía antes de la penutima
                 if lines[-3].strip():  
                    lines.insert(-2, "")
                # Se centran las dos últimas líneas después de limpiar los espacios internos
                 lines[-2:] = [self.clean_spaces(line).center(100) for line in lines[-2:]]

            return "\n".join(lines)

    def clean_spaces(self, text):
       
       """
       Quita espacios al inicio y al final, y reduce múltiples espacios internos a uno solo.
       """

       return re.sub(r'\s+', ' ', text.strip())  # Reemplaza múltiples espacios con uno solo y elimina espacios al inicio/final

def validate_required_columns_from_excel(excel_file):
    """
    Valida que el archivo Excel contenga las columnas requeridas y retorna un DataFrame limpio.

    Esta función realiza las siguientes operaciones:
    
    1. Lee el archivo Excel utilizando pandas y el motor "openpyxl".  
       Si ocurre algún error al leer el archivo, se lanza un ValueError con un mensaje descriptivo.
       
    2. Elimina espacios en blanco de los nombres de las columnas leídas.
    
    3. Verifica que el DataFrame contenga las siguientes columnas requeridas:   
       - 'nro_incidencia'            
       - 'canal_ingreso'                  
       - 'interrupcion_inicio'            
       - 'fecha_generacion'                 
       - 'interrupcion_fin'                 
       - 'cid'
       - 'tipo_caso'
       - 'tipificacion_problema'           
       - 'it_determinacion_de_la_causa'
       - 'it_medidas_tomadas'
       - 'it_conclusiones'                  
       - 'tiempo_interrupcion'              
       - 'tipificacion_interrupcion'        
       
       Si faltan algunas de estas columnas, se lanza un ValueError con un mensaje indicando
       cuáles son las columnas ausentes.
       
    4. Extrae del DataFrame únicamente las columnas requeridas, limpia el contenido de cada celda 
       aplicando la función `clean_texto_from_celdas` y reemplaza los valores nulos por "-".

    Parameters:
        excel_file

    Returns:
        pandas.DataFrame: DataFrame que contiene únicamente las columnas requeridas, con el texto de
        las celdas procesado y sin valores nulos.

    Raises:
        ValueError: Si ocurre algún error al leer el archivo Excel o si faltan columnas requeridas.

    """
  
    required_columns = [
        'nro_incidencia', # ticket
        'canal_ingreso', # tipo generacion ticket
        'interrupcion_inicio',  # fecha/hora interrupcion
        'fecha_generacion', # fecha/hora generacion
        'interrupcion_fin',  # fecha/ hora subsanacion
        'cid', 'tipo_caso', 
        'tipificacion_problema', #averia
        'it_determinacion_de_la_causa','it_medidas_tomadas',
        'it_conclusiones', # recomendaciones
        'tiempo_interrupcion', #tiempo subsanacion efectivo
        'tipificacion_interrupcion' # tiempo de indisponibilidad
        
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
    """
    Genera reportes por tickets a partir de un DataFrame.

    La función realiza las siguientes operaciones:
    
    1. Reemplaza ciertos valores en la columna 'canal_ingreso' para agrupar entradas bajo la categoría 'Reclamo'.
    2. Crea la columna 'fecha_hora_solicitud' basada en el valor de 'canal_ingreso': 
       si el valor es 'Proactivo', se asigna '-', de lo contrario 'Por definir'.
    3. Asigna valores constantes a las siguientes columnas:
       - 'fecha_hora_llegada_personal': "-"
       - 'tiempo_llegada_personal': "-"
       - 'horas_excedidas_plazo_reparacion_bases': 0
       - 'descripcion_problema': Mensaje fijo indicando la pérdida de gestión del servicio.
    4. Convierte las columnas de fecha ('interrupcion_inicio', 'fecha_generacion', 'interrupcion_fin') a tipo datetime,
       gestionando errores mediante 'coerce'.
    5. Ordena el DataFrame por la columna 'interrupcion_inicio' en orden ascendente.
    6. Formatea las columnas de fecha al formato '%d/%m/%Y %H:%M:%S'.
    7. Retorna el DataFrame transformado como una lista de diccionarios.

    Parameters:
        df (pandas.DataFrame): DataFrame con los datos originales del reporte.

    Returns:
        list: Lista de diccionarios, donde cada diccionario representa una fila del DataFrame transformado.

    Raises:
        Exception: Puede lanzar excepciones si faltan columnas requeridas o si ocurre un error durante la conversión de fechas.
    """

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

    return df_sorted.to_dict(orient="records")


