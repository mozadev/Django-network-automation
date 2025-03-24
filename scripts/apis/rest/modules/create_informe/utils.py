from docxtpl import DocxTemplate

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


