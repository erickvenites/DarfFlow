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

    def process_upload(self, file, company_id: str, cnpj: str, event: str) -> dict:
        """
        Processa o upload de uma spreadsheet e a salva no diretório apropriado.

        Args:
            file: Arquivo da spreadsheet a ser sent.
            company_id (str): Identificador da empresa (código, nome, etc).
            cnpj (str): CNPJ da empresa (14 dígitos).
            event (str): Tipo de event.

        Returns:
            dict: Resultado do processamento.
        """
        company_id = company_id.upper()
        current_year = str(datetime.now().year)
        filename = secure_filename(file.filename)

        # Validações iniciais
        if not allowed_file_xlsx(filename):
            logger.warning("Extensão de file não permitida: %s", filename)
            return {"message": "Extensão de file não permitida"}, 400

        # Detecta o tipo do arquivo pela extensão
        file_extension = os.path.splitext(filename)[1].lower().replace('.', '')
        if not file_extension:
            file_extension = "xlsx"  # Default para xlsx se não conseguir detectar

        # Caminho do diretório
        folder_path = os.path.join(self.RECEIVED_FOLDER, company_id, event, current_year)

        # Valida o diretório
        if not self._validate_directory(folder_path):
            os.makedirs(folder_path,exist_ok=True)
            logger.info("Arquivos criado com sucesso: %s",folder_path)
            #return {"message": "O diretório referente não existe"}, 404

        file_path = os.path.join(folder_path, filename)

        # Verifica duplicatas
        if EventSpreadsheet.query.filter_by(path=file_path).first():
            logger.warning("Arquivo duplicado: %s", filename)
            return {"message": f"Arquivo {filename} já existe"}, 409

        # Salva o file fisicamente
        file.save(file_path)

        try:
            # Cria o registro no banco de dados
            new_spreadsheet = EventSpreadsheet(
                company_id=company_id,
                cnpj=cnpj,
                event=event,
                filename=filename,
                file_type=file_extension,
                status=FileStatus.RECEBIDO,
                path=file_path,
            )
            db.session.add(new_spreadsheet)
            db.session.commit()

            logger.info("Arquivo %s processado com sucesso", filename)

            return {"message": "Arquivo salvo com sucesso", "spreadsheet_id": str(new_spreadsheet.id)}, 201
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error("Erro ao salvar no banco: %s", str(e))
            return {"message": "Erro ao salvar no banco"}, 500

    @classmethod
    def get_total_rows(cls, file_path: str) -> int:
        """
        Conta o total de linhas em uma spreadsheet.

        Args:
            file_path (str): Caminho do file da spreadsheet.

        Returns:
            int: Número de linhas na spreadsheet.
        """
        try:
            df = pd.read_excel(file_path)
            return len(df)
        except Exception as e:
            logger.error("Erro ao contar linhas no file %s: %s", file_path, str(e))
            return 0

    def download_file(self, spreadsheet_id: int) -> tuple:
        """
        Prepara o file para download usando o ID da spreadsheet.

        Args:
            spreadsheet_id (int): ID da spreadsheet a ser baixada.

        Returns:
            tuple: Mensagem e status do processo.
        """
        spreadsheet = EventSpreadsheet.query.filter_by(id=spreadsheet_id).first()

        if not spreadsheet:
            logger.error("Planilha não encontrada no banco de dados com ID: %s", spreadsheet_id)
            return {"message": "Arquivo não encontrado"}, 404

        file_path = spreadsheet.path

        # Verifica se o file existe
        if not os.path.exists(file_path):
            logger.error("Arquivo não encontrado no sistema de arquivos: %s", file_path)
            return {"message": "Arquivo não encontrado"}, 404

        if os.path.getsize(file_path) == 0:
            logger.warning("Arquivo vazio: %s", file_path)
            return {"message": "Arquivo vazio"}, 400

        logger.info("Fazendo download do file: %s", file_path)
        return {"message": "Fazendo download do file"}, 200, file_path

    def get_spreadsheet_by_id(self, file_id: int) -> dict:
        """
        Busca uma spreadsheet pelo ID no banco de dados.

        Args:
            file_id (int): ID da spreadsheet.

        Returns:
            dict: Dados da spreadsheet ou erro.
        """
        try:
            if not file_id:
                logger.error("ID da spreadsheet está como None")
                return {"message": "ID da spreadsheet não pode ser None"}, 400

            spreadsheet = EventSpreadsheet.query.filter_by(id=file_id).first()

            if not spreadsheet:
                logger.error("Planilha não encontrada")
                return {"message": "Planilha não encontrada"}, 404

            return {"data": spreadsheet.to_dict()}, 200
        except ValueError:
            logger.error(f"ID inválido: {file_id}")
            return {"message": "ID inválido"}, 400
        except Exception as e:
            logger.error(f"Erro ao buscar a spreadsheet: {str(e)}")
            return {"message": "Erro interno ao buscar a spreadsheet."}, 500

    def delete_event_and_associated_spreadsheet(self, event_id: int) -> dict:
        """
        Deleta uma spreadsheet e seus registros associados.

        Args:
            event_id (int): ID do event para buscar a spreadsheet associada.

        Returns:
            dict: Resultado da operação de exclusão.
        """
        spreadsheet = EventSpreadsheet.query.filter_by(id=event_id).first()

        if not spreadsheet:
            return {"message": "Planilha não encontrada"}, 404

        file_path = spreadsheet.path

        try:
            # Remoção do file físico
            if os.path.exists(file_path):
                os.remove(file_path)

            # Remove do banco
            db.session.delete(spreadsheet)
            db.session.commit()
            logger.info(f"Planilha {file_path} deletada com sucesso.")

            return {"message": "Planilha deletada com sucesso"}, 200
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error("Erro ao deletar spreadsheet: %s", str(e))
            return {"message": "Erro ao deletar do banco"}, 500
        except OSError as e:
            logger.error("Erro ao deletar file físico: %s", str(e))
            return {"message": "Erro ao deletar file físico"}, 500

    def get_event_class(self, event_id: str) -> object:
        """
        Retorna a classe correspondente ao event baseado no ID.

        Args:
            event_id (str): ID do event.

        Returns:
            object: Classe associada ao event.
        """
        event_class = self.event_map.get(event_id)
        if not event_class:
            logger.error("Evento %s não suportado.", event_id)
            raise ValueError(f"Evento {event_id} não suportado.")
        return event_class

    def process_spreadsheet(self, spreadsheet_id: int, cnpj: str = None) -> dict:
        """
        Processa a spreadsheet com base no ID da spreadsheet.
        Usa o CNPJ armazenado no banco de dados ou o fornecido como parâmetro.

        Args:
            spreadsheet_id (int): ID da spreadsheet.
            cnpj (str, optional): CNPJ para validação (usado apenas para retrocompatibilidade).

        Returns:
            dict: Resultado do processamento.
        """
        # Busca a spreadsheet pelo ID
        spreadsheet = EventSpreadsheet.query.filter_by(id=spreadsheet_id).first()

        if not spreadsheet:
            logger.error("Planilha com ID %s não encontrada.", spreadsheet_id)
            return {"message": "Planilha não encontrada"}, 404

        # Usa o CNPJ do banco de dados, ou o fornecido como parâmetro
        cnpj_to_use = spreadsheet.cnpj or cnpj

        if not cnpj_to_use:
            logger.error("CNPJ não encontrado para a planilha %s", spreadsheet_id)
            return {"message": "CNPJ não encontrado. Atualize o registro da planilha."}, 400

        file_path = spreadsheet.path
        folder_path = os.path.dirname(file_path)
        company_id = spreadsheet.company_id
        event = spreadsheet.event

        # Verifica se o path da pasta tem profundidade suficiente para obter o year
        folder_parts = folder_path.split(os.sep)
        if len(folder_parts) < 2:
            logger.error("Caminho da pasta inválido: %s", folder_path)
            return {"message": "Caminho da pasta inválido"}, 400

        year = folder_parts[-1]  # Obtém o year a partir do path

        # Obtém o nome do file sem a extensão
        base_name = os.path.splitext(os.path.basename(file_path))[0]

        # Monta o path do diretório planilhas_convertidos sem a extensão .xlsx
        converted_sheets_folder = os.path.join(
            self.PROCESSED_FOLDER, company_id, event, year, base_name
        )

        # Verifica se o file existe
        if not os.path.exists(file_path):
            os.makedirs(converted_sheets_folder,exist_ok=True)
            logger.error("Arquivo %s criado com sucesso.", file_path)
            #return {"message": "Arquivo não encontrado"}, 404

        try:
            # Verifica se a spreadsheet já foi convertida
            existing_conversion = ConvertedSpreadsheet.query.filter_by(
                spreadsheet_id=spreadsheet_id
            ).first()

            if existing_conversion:
                logger.info("A spreadsheet %s já foi convertida.", spreadsheet_id)
                return {"message": "A spreadsheet já foi convertida"}, 200

            # AQUI ESTÁ A VALIDAÇÃO DE QUE TODAS AS CÉLULAS OBRIGATÓRIAS ESTÃO PREENCHIDAS
            event_class = self.get_event_class(event)
            event_instance = event_class(file_path=file_path, nrInsc=cnpj_to_use, nrInscEstab=cnpj_to_use)

            # Valida linha por linha da spreadsheet
            df = pd.read_excel(file_path)  # Lê a spreadsheet
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
                logger.error("O year de %s não corresponde com o atual: %s", year, current_year)
                return {"message": f"O year de {year} não corresponde com o atual: {current_year}"}, 400

            # Exporta os XMLs gerados
            for xml_str in xmls:
                event_instance.export_xml(xml_str, company_id=company_id, year=year, event=event)

            # Salva a referência na tabela tb_planilhas_convertidas
            new_converted_spreadsheet = ConvertedSpreadsheet(
                spreadsheet_id=spreadsheet_id,  # Referência à spreadsheet convertida
                path=converted_sheets_folder,  # Caminho atualizado para a pasta de XMLs convertidos
                total_generated_xmls=len(xmls),
                converted_date=datetime.now(),
            )
            db.session.add(new_converted_spreadsheet)

            # Atualiza o status da spreadsheet na tabela Events para CONVERTIDO
            spreadsheet.status = FileStatus.CONVERTIDO  # Atualiza o status para 'CONVERTIDO'
            db.session.add(spreadsheet)

            db.session.commit()  # Salva todas as referências

            logger.info("Processamento da spreadsheet %s concluído com sucesso.", spreadsheet_id)
            return {"message": "Processamento concluído com sucesso"}, 200

        except ValueError as ve:
            logger.error("Erro de valor: %s", str(ve))
            return {"message": str(ve)}, 400
        except Exception as e:
            logger.error("Erro ao processar a spreadsheet: %s", str(e))
            return {"message": "Erro ao processar a spreadsheet"}, 500
