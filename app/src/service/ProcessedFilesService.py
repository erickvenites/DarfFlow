import os
import shutil
import zipfile
from flask import send_file
from typing import Optional, Tuple, Dict, Any
from src.models.database import ConvertedSpreadsheet, EventSpreadsheet, FileStatus
from src import db
from sqlalchemy import extract
from sqlalchemy.exc import SQLAlchemyError
from src.config.logging_config import logger
from src.models.Events.v2_01_02.Event_4020 import Evento4020
from src.config.folder_upload_config import UPLOAD_FOLDER

class ProcessedFilesService:
    """
    Serviço responsável pelo processamento de arquivos convertidos de planilhas,
    incluindo operações de listagem, busca, download e exclusão de diretórios e arquivos XML.

    A classe oferece funcionalidades como a obtenção de planilhas convertidas relacionadas
    a eventos, o empacotamento de arquivos XML em um file ZIP para download e a exclusão
    de diretórios de arquivos, incluindo o manejo das referências no banco de dados.
    """
    def __init__(self) -> None:
        """
        Inicializa o serviço, configurando os paths e mapeando os eventos para suas respectivas classes.

        Atributos:
            PROCESSED_FOLDER (str): Caminho para a pasta de planilhas convertidas.
            event_map (dict): Mapeamento dos eventos com suas respectivas classes.
        """
        self.PROCESSED_FOLDER = os.path.join(UPLOAD_FOLDER, "planilhas_convertidas")
        self.event_map = {
            "4020": Evento4020
            # Adicione aqui os futuros eventos mapeando o ID do event à sua classe
        }

    def _get_converted_spreadsheet(self, company_id: str, event: str, year: int) -> Optional[ConvertedSpreadsheet]:
        """
        Recupera uma spreadsheet convertida específica para a empresa, event e year fornecidos.

        Args:
            company_id (str): Identificador da empresa para filtrar.
            event (str): O código do event para filtrar.
            year (int): O year para filtrar.

        Returns:
            Optional[ConvertedSpreadsheet]: A spreadsheet convertida encontrada, ou None se não encontrar.
        """
        try:
            converted_spreadsheet = ConvertedSpreadsheet.query.join(EventSpreadsheet).filter(
                EventSpreadsheet.company_id == company_id,
                EventSpreadsheet.event == event,
                extract('year', EventSpreadsheet.received_date) == year,
                EventSpreadsheet.status == FileStatus.CONVERTIDO
            ).first()

            if not converted_spreadsheet:
                logger.error(f"Nenhuma spreadsheet convertida encontrada para o event {event} no year {year} e empresa {company_id}")
                return None

            logger.info(f"Planilha convertida encontrada: {converted_spreadsheet}")
            return converted_spreadsheet
        except SQLAlchemyError as e:
            logger.error(f"Erro ao consultar banco de dados para a spreadsheet convertida: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao obter a spreadsheet convertida: {e}")
            return None

    def list_all(self, company_id: str, event: str, year: int, xmls_directory: Optional[str] = None) -> Tuple[Dict[str, Any], int]:
        """
        Lista os diretórios e arquivos XML relacionados a uma empresa, event e year específicos.

        Args:
            company_id (str): Identificador da empresa para filtrar.
            event (str): O código do event para filtrar.
            year (int): O year para filtrar.
            xmls_directory (Optional[str]): O diretório específico dentro dos arquivos XML para listar.

        Returns:
            Tuple[Dict[str, Any], int]: Um dicionário contendo os arquivos ou informações sobre a falha na operação,
                                          e o código HTTP da resposta.
        """
        try:
            # Obtém todas as planilhas convertidas para a empresa/event/year
            # Inclui planilhas com status CONVERTIDO ou ASSINADO
            converted_spreadsheets = db.session.query(ConvertedSpreadsheet).join(
                EventSpreadsheet,
                ConvertedSpreadsheet.spreadsheet_id == EventSpreadsheet.id
            ).filter(
                EventSpreadsheet.company_id == company_id,
                EventSpreadsheet.event == event,
                extract('year', EventSpreadsheet.received_date) == year,
                EventSpreadsheet.status.in_([FileStatus.CONVERTIDO, FileStatus.ASSINADO])
            ).all()

            if not converted_spreadsheets:
                logger.error("Planilhas convertidas não encontradas para o event %s", event)
                return {"message": "Planilhas convertidas não encontradas"}, 404

            # Caminho base para arquivos convertidos
            folder_path = os.path.join(self.PROCESSED_FOLDER, company_id, event, str(year))

            result = {
                "data": [cs.to_dict() for cs in converted_spreadsheets]
            }

            # Verifica se o xmls_directory foi fornecido
            if xmls_directory:
                specific_folder_path = os.path.join(folder_path, xmls_directory)

                if not os.path.exists(specific_folder_path):
                    logger.error("Diretório não encontrado: %s", specific_folder_path)
                    return {"message": "Diretório não encontrado"}, 404

                # Lista arquivos XML dentro do diretório
                xml_files = [f for f in os.listdir(specific_folder_path) if f.endswith(".xml")]
                if not xml_files:
                    logger.warning("Nenhum file XML encontrado no diretório: %s", specific_folder_path)
                    return {"message": "Nenhum file XML encontrado"}, 404

                logger.info("Arquivos XML encontrados no diretório %s: %s", specific_folder_path, xml_files)
                result["files"] = xml_files
            else:
                # Lista os subdiretórios caso xmls_directory não seja fornecido
                if not os.path.exists(folder_path):
                    logger.error("Caminho base não encontrado: %s", folder_path)
                    return {"message": "Caminho base não encontrado"}, 404

            return result, 200

        except SQLAlchemyError as e:
            logger.error(f"Erro ao consultar banco de dados: {e}")
            return {"message": "Erro interno no servidor"}, 500
        except Exception as e:
            logger.error(f"Erro inesperado ao listar diretórios: {e}")
            return {"message": "Erro ao listar diretórios"}, 500

    def list_all_without_filters(self) -> Tuple[Dict[str, Any], int]:
        """
        Lista TODAS as planilhas convertidas sem filtros.
        Inclui planilhas com status CONVERTIDO ou ASSINADO.

        Returns:
            Tuple[Dict[str, Any], int]: Lista com todas as planilhas convertidas e código HTTP.
        """
        try:
            # Busca todas as planilhas convertidas (inclui CONVERTIDO e ASSINADO)
            converted_spreadsheets = db.session.query(ConvertedSpreadsheet).join(
                EventSpreadsheet,
                ConvertedSpreadsheet.spreadsheet_id == EventSpreadsheet.id
            ).filter(
                EventSpreadsheet.status.in_([FileStatus.CONVERTIDO, FileStatus.ASSINADO])
            ).order_by(ConvertedSpreadsheet.converted_date.desc()).all()

            if not converted_spreadsheets:
                logger.info("Nenhuma planilha convertida encontrada")
                return {"data": []}, 200

            result = {
                "data": [cs.to_dict() for cs in converted_spreadsheets]
            }

            logger.info(f"Encontradas {len(converted_spreadsheets)} planilhas convertidas")
            return result, 200

        except SQLAlchemyError as e:
            logger.error(f"Erro ao consultar banco de dados: {e}")
            return {"message": "Erro interno no servidor"}, 500
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            return {"message": "Erro ao listar planilhas convertidas"}, 500

    def list_by_company(self, company_id: str) -> Tuple[Dict[str, Any], int]:
        """
        Lista todas as planilhas convertidas de uma empresa específica.
        Inclui planilhas com status CONVERTIDO ou ASSINADO.

        Args:
            company_id (str): Identificador da empresa.

        Returns:
            Tuple[Dict[str, Any], int]: Lista com as planilhas da empresa e código HTTP.
        """
        try:
            # Busca planilhas convertidas da empresa (inclui CONVERTIDO e ASSINADO)
            converted_spreadsheets = db.session.query(ConvertedSpreadsheet).join(
                EventSpreadsheet,
                ConvertedSpreadsheet.spreadsheet_id == EventSpreadsheet.id
            ).filter(
                EventSpreadsheet.company_id == company_id,
                EventSpreadsheet.status.in_([FileStatus.CONVERTIDO, FileStatus.ASSINADO])
            ).order_by(ConvertedSpreadsheet.converted_date.desc()).all()

            if not converted_spreadsheets:
                logger.info(f"Nenhuma planilha convertida encontrada para {company_id}")
                return {"data": []}, 200

            result = {
                "data": [cs.to_dict() for cs in converted_spreadsheets]
            }

            logger.info(f"Encontradas {len(converted_spreadsheets)} planilhas convertidas para {company_id}")
            return result, 200

        except SQLAlchemyError as e:
            logger.error(f"Erro ao consultar banco de dados: {e}")
            return {"message": "Erro interno no servidor"}, 500
        except Exception as e:
            logger.error(f"Erro inesperado ao listar planilhas convertidas: {e}")
            return {"message": "Erro ao listar planilhas convertidas"}, 500

    def get_by_id(self, file_id: int) -> Tuple[Dict[str, Any], int]:
        """
        Recupera os detalhes de uma spreadsheet convertida específica pelo seu ID.

        Args:
            file_id (int): O ID da spreadsheet convertida.

        Returns:
            Tuple[Dict[str, Any], int]: Dados da spreadsheet convertida, ou erro se não encontrada,
                                        e o código HTTP da resposta.
        """
        try:
            if not file_id:
                logger.error("O id está vazio")
                return {"message": "Id do file é obrigatório"}, 400

            # Buscando a spreadsheet convertida com o id fornecido
            converted = ConvertedSpreadsheet.query.filter_by(id=file_id).first()

            if not converted:
                logger.error(f"Arquivo não encontrado para o id: {file_id}")
                return {"message": "Arquivo não encontrado"}, 404

            # Retorna os dados da spreadsheet convertida
            return {"data": converted.to_dict()}, 200

        except ValueError:
            logger.error(f"ID inválido: {file_id}")
            return {"message": "ID inválido"}, 400
        except Exception as e:
            logger.error(f"Erro ao buscar file: {str(e)}")
            return {"message": "Erro interno ao buscar o file."}, 500

    def download_all_xml_in_directory(self, file_id: int) -> Tuple[str, int, str]:
        """
        Baixa todos os arquivos XML de uma spreadsheet convertida, compactando-os em um file ZIP.

        Args:
            file_id (int): O ID da spreadsheet convertida.

        Returns:
            Tuple[str, int, str]: Caminho para o file ZIP gerado, código HTTP da resposta
                                   e o path do file ZIP para o envio.
        """
        # Busca a spreadsheet convertida com base no arquivo_id
        converted_spreadsheet = db.session.query(ConvertedSpreadsheet).filter_by(id=file_id).first()

        if not converted_spreadsheet:
            logger.error("Nenhuma spreadsheet convertida encontrada para o arquivo_id: %s", file_id)
            return {"message": "Nenhuma spreadsheet convertida encontrada"}, 400

        # Usa o path da spreadsheet convertida para localizar os arquivos XML
        folder_path = converted_spreadsheet.path
        temp_path = os.path.join(self.PROCESSED_FOLDER, "temp")

        # Lista todos os arquivos XML no diretório especificado
        all_files = [
            os.path.join(folder_path, file)
            for file in os.listdir(folder_path)
            if file.endswith(".xml")
        ]

        if not all_files:
            logger.warning("Nenhum file XML encontrado no diretório: %s", folder_path)
            return {"message": "Nenhum file XML encontrado no diretório"}, 400

        # Define o nome e path do file zip
        zip_filename = f"{file_id}_xmls.zip"
        zip_file_path = os.path.join(temp_path, zip_filename)

        # Garante que o diretório temporário exista
        os.makedirs(temp_path, exist_ok=True)

        try:
            # Cria o file zip contendo todos os XMLs
            with zipfile.ZipFile(zip_file_path, "w") as zip_file:
                for file_path in all_files:
                    zip_file.write(file_path, os.path.basename(file_path))
            logger.info("Arquivos zipados para download: %s", zip_file_path)

            # Retorna o file zip para download
            return zip_file_path, 200, zip_file_path

        except Exception as e:
            logger.error("Erro ao criar o file zip: %s", str(e))
            return {"message": "Erro ao criar o file zip"}, 500

    def delete_directory(self, directory_id: int) -> Tuple[Dict[str, Any], int]:
        """
        Exclui o diretório relacionado a uma spreadsheet convertida e remove a referência do banco de dados.

        Args:
            directory_id (int): O ID da spreadsheet convertida para exclusão.

        Returns:
            Tuple[Dict[str, Any], int]: Mensagem de sucesso ou erro e o código HTTP da resposta.
        """
        # Busca a spreadsheet convertida com base no arquivo_id
        converted_spreadsheet = db.session.query(ConvertedSpreadsheet).filter_by(id=directory_id).first()

        if not converted_spreadsheet:
            logger.error("Nenhuma spreadsheet convertida encontrada para o arquivo_id: %s", directory_id)
            return {"message": "Nenhuma spreadsheet convertida encontrada"}, 404

        # Usa o path da spreadsheet convertida para localizar o diretório
        folder_path = converted_spreadsheet.path
        directory_path = os.path.join(folder_path)

        if not os.path.exists(directory_path):
            logger.error("Diretório não encontrado: %s", directory_path)
            return {"message": "Diretório não encontrado"}, 404

        try:
            # Deleta o diretório fisicamente no sistema de arquivos
            shutil.rmtree(directory_path)
            db.session.delete(converted_spreadsheet)
            db.session.commit()
            logger.info("Diretório deletado e referência removida do banco de dados: %s", directory_path)
            return {"message": "Diretório deletado com sucesso"}, 200

        except Exception as e:
            logger.error("Erro ao excluir o diretório: %s", str(e))
            return {"message": "Erro ao excluir o diretório"}, 500
