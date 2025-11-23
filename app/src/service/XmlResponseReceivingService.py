import os
from src.config.logging_config import logger
from src.config.folder_upload_config import UPLOAD_FOLDER




class XmlResponseReceivingService:
        def __init__(self):
            self.SEND_FOLDER = os.path.join(UPLOAD_FOLDER, 'enviados')


        def get_response_endpoint():
              ...
            #Aqui deve pegar a responsa do envio dos eventos e monstrar para o usuario se o event foi cadastrado com sucesso ou fracasso
            #Se tiver fracassado, informar o Por que
            
        
