from docxtpl import DocxTemplate


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
        }
        doc.render(self.context)
        doc.save(self.name)

        return self.name
    
