from docxtpl import DocxTemplate

class CreateInforme:
    def __init__(self, template, data, now):
        self.template = template
        self.data = data
        self.name = f"media/informes/{now}.docx"

