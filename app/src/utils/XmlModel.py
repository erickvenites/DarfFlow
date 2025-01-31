from datetime import datetime, date
import pandas as pd
from lxml import etree
import os
from typing import List, Dict, Optional, Type
from src.config.folder_upload_config import UPLOAD_FOLDER
from src.config.logging_config import logger


class XmlModel:
    """
    Classe base para processar planilhas Excel, gerar eventos e convertê-los em XMLs.

    Attributes:
        PROCESSED_FOLDER (str): Diretório onde os arquivos processados serão armazenados.
        file_path (str): Caminho do arquivo Excel de entrada.
        df_spreadsheet (pd.DataFrame): DataFrame contendo os dados da planilha.
        event_cls (Type): Classe associada ao tipo de evento.
        current_date (Optional[date]): Data atual, usada para controle de arquivos diários.
        daily_index (int): Índice diário para evitar duplicação de nomes de arquivos.
    """

    def __init__(self, file_path: str, event_cls: Type):
        """
        Inicializa a instância do XmlModel.

        Args:
            file_path (str): Caminho para o arquivo Excel.
            event_cls (Type): Classe associada ao evento.
        """
        self.PROCESSED_FOLDER: str = os.path.join(UPLOAD_FOLDER, "planilhas_convertidas")
        self.file_path: str = file_path
        self.df_spreadsheet: Optional[pd.DataFrame] = None
        self.event_cls: Type = event_cls
        self.current_date: Optional[date] = None
        self.daily_index: int = 0

        self.read_spreadsheet()

    def read_spreadsheet(self) -> None:
        """
        Lê a planilha Excel e armazena os dados em um DataFrame.

        Se houver erro durante a leitura, um DataFrame vazio será atribuído.
        """
        try:
            self.df_spreadsheet = pd.read_excel(self.file_path)
        except Exception as e:
            logger.error(f"Erro ao ler a planilha Excel: {e}")
            self.df_spreadsheet = pd.DataFrame()

    def process_events(self, event: Dict) -> List[str]:
        """
        Processa eventos a partir dos dados na planilha e retorna uma lista de XMLs.

        Args:
            event (Dict): Estrutura inicial do evento, podendo ser modificada durante o processamento.

        Returns:
            List[str]: Lista de strings contendo os XMLs gerados.
        """
        xmls: List[str] = []
        if self.df_spreadsheet is None:
            logger.error("DataFrame da planilha está vazio. Nenhum evento será processado.")
            return xmls

        for index, row in self.df_spreadsheet.iterrows():
            if row.isnull().all():
                logger.info(f"Parando o processamento, linha {index + 1} está vazia.")
                break

            event_data = self.prepare_event(row, index)
            if "error" in event_data:
                logger.error(f"Erro no evento da linha {index + 1}: {event_data['error']}")
                continue

            xml_str = self.generate_xml(event_data)
            if xml_str and isinstance(xml_str, str):
                xmls.append(xml_str)
            else:
                logger.error("Erro ao gerar XML, o resultado não é uma string válida.")
        return xmls

    def prepare_event(self, row: pd.Series, row_index: int) -> Dict:
        """
        Prepara os dados de um evento a partir de uma linha da planilha.

        Args:
            row (pd.Series): Linha da planilha.
            row_index (int): Índice da linha atual.

        Returns:
            Dict: Dados do evento prontos para serem processados.
        """
        return {col: row[col] for col in row.index if pd.notnull(row[col])}

    def export_xml(self, xml_str: str, om: str, year: str, event: str) -> None:
        """
        Exporta o XML gerado para o diretório apropriado.

        Args:
            xml_str (str): String contendo o XML.
            om (str): Organização Militar ou identificador associado.
            year (str): Ano relacionado ao evento.
            event (str): Nome do evento.
        """
        spreadsheet_name: str = os.path.splitext(os.path.basename(self.file_path))[0]
        output_folder: str = os.path.join(self.PROCESSED_FOLDER, om, event, year, spreadsheet_name)

        current_year: str = str(datetime.now().year)
        if year != current_year:
            logger.error(f"O ano de {year} não corresponde com o atual: {current_year}")
            return

        os.makedirs(output_folder, exist_ok=True)
        current_date: date = datetime.now().date()

        if self.current_date != current_date:
            self.current_date = current_date
            self.daily_index = 1
        else:
            self.daily_index += 1

        formatted_date: str = self.current_date.strftime("%d-%m-%Y")
        identifier: str = f"{formatted_date}-{self.daily_index}"
        event_name: str = self.event_cls.__name__.lower()
        file_name: str = f"{event_name}-{identifier}.xml"
        file_path: str = os.path.join(output_folder, file_name)

        try:
            with open(file_path, "w", encoding="utf-8") as xml_file:
                xml_file.write(xml_str)
                logger.info(f"Arquivo XML exportado para: {file_path}")
        except Exception as e:
            logger.error(f"Erro ao exportar o XML: {e}")

    @classmethod
    def minify_xml(cls, xml_str: str) -> str:
        """
        Remove espaços em branco desnecessários do XML.

        Args:
            xml_str (str): String contendo o XML a ser minificado.

        Returns:
            str: XML minificado ou o original em caso de erro.
        """
        try:
            parser = etree.XMLParser(remove_blank_text=True)
            root = etree.fromstring(xml_str.encode("utf-8"), parser=parser)
            return etree.tostring(root, pretty_print=False, encoding="UTF-8").decode()
        except etree.XMLSyntaxError as e:
            logger.info(f"Erro ao minificar XML: {e}")
            return xml_str

