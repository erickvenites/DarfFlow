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
    a eventos, o empacotamento de arquivos XML em um arquivo ZIP para download e a exclusão
    de diretórios de arquivos, incluindo o manejo das referências no banco de dados.
    """
    def __init__(self) -> None:
        """
        Inicializa o serviço, configurando os caminhos e mapeando os eventos para suas respectivas classes.

        Atributos:
            PROCESSED_FOLDER (str): Caminho para a pasta de planilhas convertidas.
            event_map (dict): Mapeamento dos eventos com suas respectivas classes.
        """
        self.PROCESSED_FOLDER = os.path.join(UPLOAD_FOLDER, "planilhas_convertidas")
        self.event_map = {
            "4020": Evento4020
            # Adicione aqui os futuros eventos mapeando o ID do evento à sua classe
        }

    def _get_converted_spreadsheet(self, om: str, event: str, year: int) -> Optional[ConvertedSpreadsheet]:
        """
        Recupera uma planilha convertida específica para a OM, evento e ano fornecidos.

        Args:
            om (str): A OM (Organização Militar) para filtrar.
            event (str): O código do evento para filtrar.
            year (int): O ano para filtrar.

        Returns:
            Optional[ConvertedSpreadsheet]: A planilha convertida encontrada, ou None se não encontrar.
        """
        try:
            converted_spreadsheet = ConvertedSpreadsheet.query.join(EventSpreadsheet).filter(
                EventSpreadsheet.om == om,
                EventSpreadsheet.evento == event,
                extract('year', EventSpreadsheet.data_recebimento) == year,
                EventSpreadsheet.status == FileStatus.CONVERTIDO
            ).first()
            
            if not converted_spreadsheet:
                logger.error(f"Nenhuma planilha convertida encontrada para o evento {event} no ano {year} e OM {om}")
                return None

            logger.info(f"Planilha convertida encontrada: {converted_spreadsheet}")
            return converted_spreadsheet
        except SQLAlchemyError as e:
            logger.error(f"Erro ao consultar banco de dados para a planilha convertida: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao obter a planilha convertida: {e}")
            return None

    def list_all(self, om: str, event: str, year: int, xmls_directory: Optional[str] = None) -> Tuple[Dict[str, Any], int]:
        """
        Lista os diretórios e arquivos XML relacionados a uma OM, evento e ano específicos.

        Args:
            om (str): A OM (Organização Militar) para filtrar.
            event (str): O código do evento para filtrar.
            year (int): O ano para filtrar.
            xmls_directory (Optional[str]): O diretório específico dentro dos arquivos XML para listar.

        Returns:
            Tuple[Dict[str, Any], int]: Um dicionário contendo os arquivos ou informações sobre a falha na operação,
                                          e o código HTTP da resposta.
        """
        try:
            # Obtém o evento específico
            event_spreadsheet = db.session.query(EventSpreadsheet).filter(
                EventSpreadsheet.om == om,
                EventSpreadsheet.evento == event,
                extract('year', EventSpreadsheet.data_recebimento) == year
            ).first()

            if not event_spreadsheet:
                logger.error("Evento não encontrado: %s", event)
                return {"message": "Evento não encontrado"}, 404

            # Obtém as planilhas convertidas relacionadas ao evento específico
            converted_spreadsheets = db.session.query(ConvertedSpreadsheet).filter(
                ConvertedSpreadsheet.planilha_id == event_spreadsheet.id
            ).all()

            if not converted_spreadsheets:
                logger.error("Planilhas convertidas não encontradas para o evento %s", event)
                return {"message": "Planilhas convertidas não encontradas"}, 404

            # Caminho base para arquivos convertidos
            folder_path = os.path.join(self.PROCESSED_FOLDER, om, event, str(year))

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
                    logger.warning("Nenhum arquivo XML encontrado no diretório: %s", specific_folder_path)
                    return {"message": "Nenhum arquivo XML encontrado"}, 404

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

    def get_by_id(self, file_id: int) -> Tuple[Dict[str, Any], int]:
        """
        Recupera os detalhes de uma planilha convertida específica pelo seu ID.

        Args:
            file_id (int): O ID da planilha convertida.

        Returns:
            Tuple[Dict[str, Any], int]: Dados da planilha convertida, ou erro se não encontrada,
                                        e o código HTTP da resposta.
        """
        try:
            if not file_id:
                logger.error("O id está vazio")
                return {"message": "Id do arquivo é obrigatório"}, 400

            # Buscando a planilha convertida com o id fornecido
            converted = ConvertedSpreadsheet.query.filter_by(id=file_id).first()

            if not converted:
                logger.error(f"Arquivo não encontrado para o id: {file_id}")
                return {"message": "Arquivo não encontrado"}, 404

            # Retorna os dados da planilha convertida
            return {"data": converted.to_dict()}, 200

        except ValueError:
            logger.error(f"ID inválido: {file_id}")
            return {"message": "ID inválido"}, 400
        except Exception as e:
            logger.error(f"Erro ao buscar arquivo: {str(e)}")
            return {"message": "Erro interno ao buscar o arquivo."}, 500

    def download_all_xml_in_directory(self, file_id: int) -> Tuple[str, int, str]:
        """
        Baixa todos os arquivos XML de uma planilha convertida, compactando-os em um arquivo ZIP.

        Args:
            file_id (int): O ID da planilha convertida.

        Returns:
            Tuple[str, int, str]: Caminho para o arquivo ZIP gerado, código HTTP da resposta
                                   e o caminho do arquivo ZIP para o envio.
        """
        # Busca a planilha convertida com base no arquivo_id
        converted_spreadsheet = db.session.query(ConvertedSpreadsheet).filter_by(id=file_id).first()

        if not converted_spreadsheet:
            logger.error("Nenhuma planilha convertida encontrada para o arquivo_id: %s", file_id)
            return {"message": "Nenhuma planilha convertida encontrada"}, 400

        # Usa o caminho da planilha convertida para localizar os arquivos XML
        folder_path = converted_spreadsheet.caminho
        temp_path = os.path.join(self.PROCESSED_FOLDER, "temp")

        # Lista todos os arquivos XML no diretório especificado
        all_files = [
            os.path.join(folder_path, file)
            for file in os.listdir(folder_path)
            if file.endswith(".xml")
        ]

        if not all_files:
            logger.warning("Nenhum arquivo XML encontrado no diretório: %s", folder_path)
            return {"message": "Nenhum arquivo XML encontrado no diretório"}, 400

        # Define o nome e caminho do arquivo zip
        zip_filename = f"{file_id}_xmls.zip"
        zip_file_path = os.path.join(temp_path, zip_filename)

        # Garante que o diretório temporário exista
        os.makedirs(temp_path, exist_ok=True)

        try:
            # Cria o arquivo zip contendo todos os XMLs
            with zipfile.ZipFile(zip_file_path, "w") as zip_file:
                for file_path in all_files:
                    zip_file.write(file_path, os.path.basename(file_path))
            logger.info("Arquivos zipados para download: %s", zip_file_path)

            # Retorna o arquivo zip para download
            return zip_file_path, 200, zip_file_path

        except Exception as e:
            logger.error("Erro ao criar o arquivo zip: %s", str(e))
            return {"message": "Erro ao criar o arquivo zip"}, 500

    def delete_directory(self, directory_id: int) -> Tuple[Dict[str, Any], int]:
        """
        Exclui o diretório relacionado a uma planilha convertida e remove a referência do banco de dados.

        Args:
            directory_id (int): O ID da planilha convertida para exclusão.

        Returns:
            Tuple[Dict[str, Any], int]: Mensagem de sucesso ou erro e o código HTTP da resposta.
        """
        # Busca a planilha convertida com base no arquivo_id
        converted_spreadsheet = db.session.query(ConvertedSpreadsheet).filter_by(id=directory_id).first()

        if not converted_spreadsheet:
            logger.error("Nenhuma planilha convertida encontrada para o arquivo_id: %s", directory_id)
            return {"message": "Nenhuma planilha convertida encontrada"}, 404

        # Usa o caminho da planilha convertida para localizar o diretório
        folder_path = converted_spreadsheet.caminho
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
