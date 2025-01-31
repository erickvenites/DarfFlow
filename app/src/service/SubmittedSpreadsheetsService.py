import os
import uuid
from datetime import datetime
from flask import json
from numpy import extract
import pandas as pd
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename
from src.utils.file_handler import allowed_file_xlsx
from src.config.folder_upload_config import UPLOAD_FOLDER
from src.config.logging_config import logger
from src.models.Events.v2_01_02.Event_4020 import Evento4020
from src import db
from src.models.database import (
    EventSpreadsheet,
    FileStatus,
    ConvertedSpreadsheet,
)

class SubmittedSpreadsheetsService:
    """
    Serviço responsável pelo gerenciamento e processamento de planilhas enviadas.
    Inclui operações de validação, upload, conversão e exclusão de planilhas.
    """
    def __init__(self) -> None:
        """
        Inicializa os diretórios para arquivos recebidos e convertidos,
        além de mapear eventos a suas respectivas classes.
        """
        self.RECEIVED_FOLDER = os.path.join(UPLOAD_FOLDER, "planilhas_recebidas")
        self.PROCESSED_FOLDER = os.path.join(UPLOAD_FOLDER, "planilhas_convertidas")
        self.event_map = {
            "4020": Evento4020,
            # Adicione outros eventos conforme necessário
        }

    def _validate_directory(self, folder_path: str) -> bool:
        """
        Verifica se o diretório existe.

        Args:
            folder_path (str): Caminho do diretório a ser verificado.

        Returns:
            bool: Retorna True se o diretório existir, caso contrário, False.
        """
        if not os.path.exists(folder_path):
            logger.error("O diretório %s não existe", folder_path)
            return False
        return True

    def process_upload(self, file, om: str, event: str) -> dict:
        """
        Processa o upload de uma planilha e a salva no diretório apropriado.

        Args:
            file: Arquivo da planilha a ser enviado.
            om (str): Organização Militar.
            event (str): Tipo de evento.

        Returns:
            dict: Resultado do processamento.
        """
        om = om.upper()
        current_year = str(datetime.now().year)
        filename = secure_filename(file.filename)

        # Validações iniciais
        if not allowed_file_xlsx(filename):
            logger.warning("Extensão de arquivo não permitida: %s", filename)
            return {"message": "Extensão de arquivo não permitida"}, 400

        # Caminho do diretório
        folder_path = os.path.join(self.RECEIVED_FOLDER, om, event, current_year)

        # Valida o diretório
        if not self._validate_directory(folder_path):
            os.makedirs(folder_path,exist_ok=True)
            logger.info("Arquivos criado com sucesso: %s",folder_path)
            #return {"message": "O diretório referente não existe"}, 404

        file_path = os.path.join(folder_path, filename)

        # Verifica duplicatas
        if EventSpreadsheet.query.filter_by(caminho=file_path).first():
            logger.warning("Arquivo duplicado: %s", filename)
            return {"message": f"Arquivo {filename} já existe"}, 409

        # Salva o arquivo fisicamente
        file.save(file_path)

        try:
            # Cria o registro no banco de dados
            new_spreadsheet = EventSpreadsheet(
                om=om,
                evento=event,
                nome_arquivo=filename,
                tipo="xlsx",
                status=FileStatus.RECEBIDO,
                caminho=file_path,
            )
            db.session.add(new_spreadsheet)
            db.session.commit()

            logger.info("Arquivo %s processado com sucesso", filename)

            # Obter total de linhas da planilha
            total_rows = self.get_total_rows(file_path)
            new_spreadsheet.total_linhas = total_rows
            db.session.commit()

            return {"message": "Arquivo salvo com sucesso"}, 201
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error("Erro ao salvar no banco: %s", str(e))
            return {"message": "Erro ao salvar no banco"}, 500

    @classmethod
    def get_total_rows(cls, file_path: str) -> int:
        """
        Conta o total de linhas em uma planilha.

        Args:
            file_path (str): Caminho do arquivo da planilha.

        Returns:
            int: Número de linhas na planilha.
        """
        try:
            df = pd.read_excel(file_path)
            return len(df)
        except Exception as e:
            logger.error("Erro ao contar linhas no arquivo %s: %s", file_path, str(e))
            return 0

    def download_file(self, spreadsheet_id: int) -> tuple:
        """
        Prepara o arquivo para download usando o ID da planilha.

        Args:
            spreadsheet_id (int): ID da planilha a ser baixada.

        Returns:
            tuple: Mensagem e status do processo.
        """
        spreadsheet = EventSpreadsheet.query.filter_by(id=spreadsheet_id).first()

        if not spreadsheet:
            logger.error("Planilha não encontrada no banco de dados com ID: %s", spreadsheet_id)
            return {"message": "Arquivo não encontrado"}, 404

        file_path = spreadsheet.caminho

        # Verifica se o arquivo existe
        if not os.path.exists(file_path):
            logger.error("Arquivo não encontrado no sistema de arquivos: %s", file_path)
            return {"message": "Arquivo não encontrado"}, 404

        if os.path.getsize(file_path) == 0:
            logger.warning("Arquivo vazio: %s", file_path)
            return {"message": "Arquivo vazio"}, 400

        logger.info("Fazendo download do arquivo: %s", file_path)
        return {"message": "Fazendo download do arquivo"}, 200, file_path

    def get_spreadsheet_by_id(self, file_id: int) -> dict:
        """
        Busca uma planilha pelo ID no banco de dados.

        Args:
            file_id (int): ID da planilha.

        Returns:
            dict: Dados da planilha ou erro.
        """
        try:
            if not file_id:
                logger.error("ID da planilha está como None")
                return {"message": "ID da planilha não pode ser None"}, 400

            spreadsheet = EventSpreadsheet.query.filter_by(id=file_id).first()

            if not spreadsheet:
                logger.error("Planilha não encontrada")
                return {"message": "Planilha não encontrada"}, 404

            return {"data": spreadsheet.to_dict()}, 200
        except ValueError:
            logger.error(f"ID inválido: {file_id}")
            return {"message": "ID inválido"}, 400
        except Exception as e:
            logger.error(f"Erro ao buscar a planilha: {str(e)}")
            return {"message": "Erro interno ao buscar a planilha."}, 500

    def delete_event_and_associated_spreadsheet(self, event_id: int) -> dict:
        """
        Deleta uma planilha e seus registros associados.

        Args:
            event_id (int): ID do evento para buscar a planilha associada.

        Returns:
            dict: Resultado da operação de exclusão.
        """
        spreadsheet = EventSpreadsheet.query.filter_by(id=event_id).first()

        if not spreadsheet:
            return {"message": "Planilha não encontrada"}, 404

        file_path = spreadsheet.caminho

        try:
            # Remoção do arquivo físico
            if os.path.exists(file_path):
                os.remove(file_path)

            # Remove do banco
            db.session.delete(spreadsheet)
            db.session.commit()
            logger.info(f"Planilha {file_path} deletada com sucesso.")

            return {"message": "Planilha deletada com sucesso"}, 200
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error("Erro ao deletar planilha: %s", str(e))
            return {"message": "Erro ao deletar do banco"}, 500
        except OSError as e:
            logger.error("Erro ao deletar arquivo físico: %s", str(e))
            return {"message": "Erro ao deletar arquivo físico"}, 500

    def get_event_class(self, event_id: str) -> object:
        """
        Retorna a classe correspondente ao evento baseado no ID.

        Args:
            event_id (str): ID do evento.

        Returns:
            object: Classe associada ao evento.
        """
        event_class = self.event_map.get(event_id)
        if not event_class:
            logger.error("Evento %s não suportado.", event_id)
            raise ValueError(f"Evento {event_id} não suportado.")
        return event_class

    def process_spreadsheet(self, spreadsheet_id: int, cnpj: str) -> dict:
        """
        Processa a planilha com base no ID da planilha e CNPJ fornecido.

        Args:
            spreadsheet_id (int): ID da planilha.
            cnpj (str): CNPJ para validação.

        Returns:
            dict: Resultado do processamento.
        """
        # Busca a planilha pelo ID
        spreadsheet = EventSpreadsheet.query.filter_by(id=spreadsheet_id).first()

        if not spreadsheet:
            logger.error("Planilha com ID %s não encontrada.", spreadsheet_id)
            return {"message": "Planilha não encontrada"}, 404

        file_path = spreadsheet.caminho
        folder_path = os.path.dirname(file_path)
        om = spreadsheet.om
        event = spreadsheet.evento

        # Verifica se o caminho da pasta tem profundidade suficiente para obter o ano
        folder_parts = folder_path.split(os.sep)
        if len(folder_parts) < 2:
            logger.error("Caminho da pasta inválido: %s", folder_path)
            return {"message": "Caminho da pasta inválido"}, 400

        year = folder_parts[-1]  # Obtém o ano a partir do caminho

        # Obtém o nome do arquivo sem a extensão
        base_name = os.path.splitext(os.path.basename(file_path))[0]

        # Monta o caminho do diretório planilhas_convertidos sem a extensão .xlsx
        converted_sheets_folder = os.path.join(
            self.PROCESSED_FOLDER, om, event, year, base_name
        )

        # Verifica se o arquivo existe
        if not os.path.exists(file_path):
            os.makedirs(converted_sheets_folder,exist_ok=True)
            logger.error("Arquivo %s criado com sucesso.", file_path)
            #return {"message": "Arquivo não encontrado"}, 404

        try:
            # Verifica se a planilha já foi convertida
            existing_conversion = ConvertedSpreadsheet.query.filter_by(
                planilha_id=spreadsheet_id
            ).first()

            if existing_conversion:
                logger.info("A planilha %s já foi convertida.", spreadsheet_id)
                return {"message": "A planilha já foi convertida"}, 200

            # AQUI ESTÁ A VALIDAÇÃO DE QUE TODAS AS CÉLULAS OBRIGATÓRIAS ESTÃO PREENCHIDAS
            event_class = self.get_event_class(event)
            event_instance = event_class(file_path=file_path, nrInsc=cnpj, nrInscEstab=cnpj)

            # Valida linha por linha da planilha
            df = pd.read_excel(file_path)  # Lê a planilha
            errors = []  # Lista para armazenar erros de validação

            for row_index, row in df.iterrows():
                event_data = event_instance.prepare_event(row, row_index)
                if "error" in event_data:  # Verifica se há erro na linha
                    logger.info(f"Erro na linha {row_index + 1}: {event_data['error']}")
                    errors.append({"row": row_index + 1, "error": event_data["error"]})

            if errors:
                return {"message": "Erros encontrados nas linhas", "errors": errors}, 400

            # Processa os eventos caso todas as linhas sejam válidas
            xmls = event_instance.process_events(event=event)

            current_year = str(datetime.now().year)
            if year != current_year:
                logger.error("O ano de %s não corresponde com o atual: %s", year, current_year)
                return {"message": f"O ano de {year} não corresponde com o atual: {current_year}"}, 400

            # Exporta os XMLs gerados
            for xml_str in xmls:
                event_instance.export_xml(xml_str, om=om, year=year, event=event)

            # Salva a referência na tabela tb_planilhas_convertidas
            new_converted_spreadsheet = ConvertedSpreadsheet(
                planilha_id=spreadsheet_id,  # Referência à planilha convertida
                caminho=converted_sheets_folder,  # Caminho atualizado para a pasta de XMLs convertidos
                total_xmls_gerados=len(xmls),
                data_conversao=datetime.now(),
            )
            db.session.add(new_converted_spreadsheet)

            # Atualiza o status da planilha na tabela Events para CONVERTIDO
            spreadsheet.status = FileStatus.CONVERTIDO  # Atualiza o status para 'CONVERTIDO'
            db.session.add(spreadsheet)

            db.session.commit()  # Salva todas as referências

            logger.info("Processamento da planilha %s concluído com sucesso.", spreadsheet_id)
            return {"message": "Processamento concluído com sucesso"}, 200

        except ValueError as ve:
            logger.error("Erro de valor: %s", str(ve))
            return {"message": str(ve)}, 400
        except Exception as e:
            logger.error("Erro ao processar a planilha: %s", str(e))
            return {"message": "Erro ao processar a planilha"}, 500
