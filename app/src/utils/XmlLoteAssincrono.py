import os
from io import BytesIO
import zipfile
import random
import string
from typing import List, Optional, Union
from src.config.folder_upload_config import UPLOAD_FOLDER
from src.config.logging_config import logger
from src.utils.XmlModel import XmlModel


class XmlLoteAssincrono(XmlModel):
    """
    Classe para gerar e gerenciar lotes assíncronos de XMLs a partir de arquivos ZIP.
    
    Attributes:
        tpInsc (int): Tipo de inscrição.
        nrInsc (str): Número de inscrição.
        SIGNED_FOLDER (str): Diretório onde os XMLs assinados serão armazenados.
        lotes (List[str]): Lista de lotes de eventos processados.
        base_xml_path (str): Caminho para a estrutura base do XML.
    """

    def __init__(self, nrInsc: str):
        """
        Inicializa a classe XmlLoteAssincrono.

        Args:
            nrInsc (str): Número de inscrição.
        """
        self.tpInsc: int = 1
        self.nrInsc: str = nrInsc
        self.SIGNED_FOLDER: str = os.path.join(UPLOAD_FOLDER, "xmls_assinados")
        self.lotes: List[str] = []
        self.base_xml_path: str = "docs/schemaPadrao/envioAssincrono(padrao).xml"

    @staticmethod
    def generate_random_id_event(tamanho: int = 8) -> str:
        """
        Gera um identificador aleatório para um evento.

        Args:
            tamanho (int): Tamanho do identificador. Padrão é 8.

        Returns:
            str: Identificador aleatório gerado.
        """
        letters: str = string.ascii_letters
        digits: str = string.digits
        first_char: str = random.choice(letters)
        remaining_chars: str = "".join(
            random.choice(letters + digits) for _ in range(tamanho - 1)
        )
        return first_char + remaining_chars

    def load_base_xml_structure(self) -> Optional[str]:
        """
        Carrega a estrutura base do XML.

        Returns:
            Optional[str]: Estrutura base do XML ou None em caso de erro.
        """
        try:
            with open(self.base_xml_path, "r", encoding="utf-8") as file:
                return file.read()
        except Exception as e:
            logger.error(
                f"Erro ao carregar o arquivo base XML: {type(e).__name__} - {e}"
            )
            return None

    def save_events_to_file(
        self, events: List[str], output_dir: str, file_index: int
    ) -> None:
        """
        Salva eventos em um arquivo XML.

        Args:
            events (List[str]): Lista de eventos em formato XML.
            output_dir (str): Diretório de saída.
            file_index (int): Índice do arquivo.
        """
        try:
            base_xml: Optional[str] = self.load_base_xml_structure()
            if base_xml is None:
                return

            ide_contribuinte_start: int = base_xml.find("<ideContribuinte>") + len(
                "<ideContribuinte>"
            )
            ide_contribuinte_end: int = base_xml.find("</ideContribuinte>")
            ide_contribuinte_content: str = (
                f"<tpInsc>{self.tpInsc}</tpInsc>"
                f"<nrInsc>{self.nrInsc}</nrInsc>"
            )
            base_xml = (
                base_xml[:ide_contribuinte_start]
                + ide_contribuinte_content
                + base_xml[ide_contribuinte_end:]
            )

            eventos_start: int = base_xml.find("<eventos>") + len("<eventos>")
            eventos_end: int = base_xml.find("</eventos>")
            eventos_content: str = "".join(events)
            final_xml: str = (
                base_xml[:eventos_start] + eventos_content + base_xml[eventos_end:]
            )

            minified_xml: str = XmlModel.minify_xml(final_xml)
            xml_with_declaration: str = (
                f'<?xml version="1.0" encoding="UTF-8"?>{minified_xml}'
            )

            file_name: str = f"evento-lote-{file_index}.xml"
            file_path: str = os.path.join(output_dir, file_name)
            os.makedirs(output_dir, exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(xml_with_declaration)

            logger.info(f"Lote de eventos salvo no arquivo: {file_path}")
        except Exception as e:
            logger.error(
                f"Erro ao salvar o lote de eventos no arquivo: {type(e).__name__} - {e}"
            )

    def process_xmls_zip(
        self, zip_file: Union[str, BytesIO], om: str, zip_filename: str, event: str
    ) -> Optional[str]:
        """
        Processa os arquivos XML contidos em um arquivo ZIP.

        Args:
            zip_file (Union[str, BytesIO]): Caminho ou conteúdo do arquivo ZIP.
            om (str): Organização militar ou identificador associado.
            zip_filename (str): Nome do arquivo ZIP.
            event (str): Nome do evento.

        Returns:
            Optional[str]: Mensagem de sucesso ou None em caso de erro.
        """
        try:
            output_processed_dir: str = os.path.join(
                UPLOAD_FOLDER, "temp", om, event, zip_filename
            )
            os.makedirs(output_processed_dir, exist_ok=True)

            events: List[str] = []
            xml_files: List[BytesIO] = self.extract_zip_files(zip_file)

            for file in xml_files:
                content: str = file.getvalue().decode("utf-8").strip()
                if content.startswith('<?xml version="1.0" encoding="UTF-8"?>'):
                    content = content.replace(
                        '<?xml version="1.0" encoding="UTF-8"?>', ""
                    ).strip()

                event_xml: str = (
                    f'<evento Id="{self.generate_random_id_event()}">{content}</evento>'
                )
                events.append(event_xml)

            for i in range(0, len(events), 50):
                self.save_events_to_file(
                    events[i : i + 50], output_processed_dir, (i // 50) + 1
                )

            self.lotes = events
            return "Todos os eventos processados e salvos."
        except Exception as e:
            logger.error(f"Erro ao processar o ZIP: {type(e).__name__} - {e}")
            return None

    @staticmethod
    def extract_zip_files(zip_file: Union[str, BytesIO]) -> List[BytesIO]:
        """
        Extrai arquivos XML de um arquivo ZIP.

        Args:
            zip_file (Union[str, BytesIO]): Caminho ou conteúdo do arquivo ZIP.

        Returns:
            List[BytesIO]: Lista de arquivos XML extraídos.
        """
        try:
            with zipfile.ZipFile(zip_file, "r") as zip_ref:
                return [
                    BytesIO(zip_ref.read(f))
                    for f in zip_ref.namelist()
                    if f.endswith(".xml")
                ]
        except Exception as e:
            logger.error(f"Erro ao extrair os arquivos ZIP: {type(e).__name__} - {e}")
            return []
