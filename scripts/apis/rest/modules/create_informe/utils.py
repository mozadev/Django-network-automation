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

