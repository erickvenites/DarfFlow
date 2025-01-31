import os
import xml.etree.ElementTree as ET
import requests
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import extract
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from src.models.database import (
    ConvertedSpreadsheet,
    EventSpreadsheet,
    SignedXmls,
    FileStatus,
    XmlsSent,
)
from src.models import db
from src.utils.XmlLoteAssincrono import XmlLoteAssincrono
from src.config.logging_config import logger
from src.config.folder_upload_config import UPLOAD_FOLDER


load_dotenv()


class ReceivingSignedXmlFilesService:
    """Serviço para gerenciar o recebimento, processamento e envio de arquivos XML assinados."""

    def __init__(self):
        """
        Inicializa o serviço, definindo as pastas de armazenamento de arquivos.

        As pastas incluem:
            - SIGNED_FOLDER: Pasta para arquivos XML assinados.
            - SEND_FOLDER: Pasta para arquivos XML enviados.
            - TEMP: Pasta para arquivos temporários.
        """
        self.SIGNED_FOLDER = os.path.join(UPLOAD_FOLDER, "xmls_assinados")
        self.SEND_FOLDER = os.path.join(UPLOAD_FOLDER, "xmls_enviados")
        self.TEMP = os.path.join(UPLOAD_FOLDER, "temp")
        self.lotes = []

    def list_all(self, om: str, event: str, year: int) -> dict:
        """
        Lista todos os dados dos arquivos assinados para uma OM, evento e ano específicos.

        Args:
            om (str): Organização Militar.
            event (str): Nome do evento.
            year (int): Ano do evento.

        Returns:
            dict: Resposta com os dados dos arquivos XML ou mensagem de erro.
        """
        try:
            # Consultando os eventos ASSINADOS associados
            event_spreadsheets = (
                db.session.query(EventSpreadsheet)
                .filter(
                    EventSpreadsheet.om == om,
                    EventSpreadsheet.evento == event,
                    extract("year", EventSpreadsheet.data_recebimento) == year,
                    EventSpreadsheet.status == FileStatus.ASSINADO,
                )
                .all()
            )

            if not event_spreadsheets:
                logger.error(
                    f"Nenhum evento encontrado para OM: {om}, Evento: {event}, Ano: {year}"
                )
                return {"message": "Nenhum evento encontrado"}, 404

            # Obter os IDs das planilhas
            event_ids = [es.id for es in event_spreadsheets]

            # Buscar todas as planilhas convertidas associadas
            converted_spreadsheets = (
                db.session.query(ConvertedSpreadsheet)
                .filter(ConvertedSpreadsheet.planilha_id.in_(event_ids))
                .all()
            )

            if not converted_spreadsheets:
                logger.warning(f"Nenhuma planilha convertida encontrada para os eventos.")
                return {"message": "Nenhuma planilha convertida encontrada"}, 404

            # Obter os IDs das planilhas convertidas
            converted_ids = [cs.id for cs in converted_spreadsheets]

            # Buscar todos os XMLs assinados associados
            signed_xmls = (
                db.session.query(SignedXmls)
                .filter(SignedXmls.planilha_convertida_id.in_(converted_ids))
                .all()
            )

            if not signed_xmls:
                logger.warning(f"Nenhum arquivo XML assinado encontrado.")
                return {"message": "Nenhum arquivo XML assinado encontrado"}, 404

            # Construir resultado final utilizando to_dict()
            zip_files = [
                {
                    **signed.to_dict(),  # Usando o método to_dict() da classe SignedXmls
                    "evento": es.evento,
                    "om": es.om,
                }
                for signed in signed_xmls
                for es in event_spreadsheets if signed.convertido.planilha_id == es.id
            ]

            logger.info(f"Arquivos ZIP encontrados: {len(zip_files)}")
            return {"data": zip_files}, 200

        except SQLAlchemyError as e:
            logger.error(f"Erro ao consultar banco de dados: {e}")
            return {"message": "Erro interno no servidor"}, 500
        except Exception as e:
            logger.error(f"Erro inesperado ao listar diretórios: {e}")
            return {"message": "Erro ao listar diretórios"}, 500

    def list_by_id(self, file_id: int) -> dict:
        """
        Lista um arquivo XML assinado pelo ID.

        Args:
            file_id (int): ID do arquivo XML.

        Returns:
            dict: Dados do arquivo ou mensagem de erro.
        """
        try:
            if not file_id:
                logger.error("O id está vazio")
                return {"message": "Id do arquivo é obrigatório"}, 400
                
            # Buscando a planilha convertida com o id fornecido
            signed = SignedXmls.query.filter_by(id=file_id).first()

            if not signed:
                logger.error(f"Arquivo não encontrado para o id: {file_id}")
                return {"message": "Arquivo não encontrado"}, 404

            # Retorna os dados da planilha convertida
            return {"data": signed.to_dict()}, 200

        except ValueError:
            logger.error(f"ID inválido: {file_id}")
            return {"message": "ID inválido"}, 400
        except Exception as e:
            logger.error(f"Erro ao buscar arquivo: {str(e)}")
            return {"message": "Erro interno ao buscar o arquivo."}, 500

    def save_signed_xml(self, om: str, event: str, year: str, zip_file, spreadsheet_id: int) -> dict:
        """
        Salva um arquivo ZIP contendo XMLs assinados, associando-o a uma planilha convertida.

        Args:
            om (str): Organização Militar.
            event (str): Nome do evento.
            year (str): Ano do evento.
            zip_file: Arquivo ZIP contendo os XMLs assinados.
            spreadsheet_id (int): ID da planilha convertida associada.

        Returns:
            dict: Mensagem de sucesso ou erro.
        """
        folder_path = os.path.join(self.SIGNED_FOLDER, om, event, year)

        # Verifica se o diretório existe
        if not os.path.exists(folder_path):
            os.makedirs(folder_path,exist_ok=True)
            logger.info(" diretório referente ao caminho %s criado com sucesso", folder_path)
            #return {"message": "O diretório referente não existe"}, 404

        try:
            # Buscar a planilha convertida associada
            planilha_convertida = ConvertedSpreadsheet.query.filter_by(planilha_id=spreadsheet_id).first()
            if not planilha_convertida:
                logger.error("Nenhuma planilha convertida associada ao ID %s", spreadsheet_id)
                return {"message": "Planilha convertida não encontrada"}, 404

            # Verificar se já existe um arquivo XML assinado associado à planilha convertida
            existing_signed_xml = db.session.query(SignedXmls).filter_by(planilha_convertida_id=planilha_convertida.id).first()
            if existing_signed_xml:
                logger.error(
                    "Já existe um arquivo XML assinado associado à planilha convertida com ID %s",
                    planilha_convertida.id,
                )
                return {
                    "message": "Apenas um arquivo XML pode ser associado a essa planilha convertida"
                }, 400

            # Salvar o arquivo ZIP com o nome correto
            zip_filename = secure_filename(zip_file.filename)  # Nome seguro para o arquivo
            zip_file_path = os.path.join(folder_path, zip_filename)
            zip_file.save(zip_file_path)

            # Verificar se o arquivo foi salvo corretamente
            if not os.path.exists(zip_file_path) or os.path.getsize(zip_file_path) == 0:
                logger.error("Erro ao salvar ou arquivo ZIP está vazio: %s", zip_file_path)
                return {"message": "Erro ao salvar o arquivo ZIP ou arquivo vazio"}, 500

            # Criar a entrada de XML assinado
            signed_xmls = SignedXmls(
                planilha_convertida_id=planilha_convertida.id,  # Relaciona ao XML convertido
                caminho=zip_file_path,
            )
            db.session.add(signed_xmls)

            # Atualizar o status da planilha original
            planilha_convertida.status = FileStatus.ASSINADO  # Atualiza o status para 'ASSINADO'
            db.session.commit()

            logger.info("Arquivo ZIP salvo e status da planilha atualizado com sucesso.")
            return {"message": "Arquivo enviado com sucesso"}, 201

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error("Erro ao salvar ou atualizar o banco de dados: %s", str(e))
            return {"message": "Erro ao salvar no banco de dados"}, 500
        except Exception as e:
            logger.error("Erro inesperado ao salvar o arquivo: %s", str(e))
            return {"message": "Erro ao salvar o arquivo"}, 500


    def delete(self, file_id: int) -> dict:
        """
        Deleta um arquivo XML assinado do banco de dados e do sistema de arquivos.

        Args:
            file_id (int): ID do arquivo XML.

        Returns:
            dict: Mensagem de sucesso ou erro.
        """
        try:
            # Buscar a referência no banco de dados
            signed_xml = SignedXmls.query.filter_by(id=file_id).first()
            if not signed_xml:
                logger.error("Arquivo não encontrado no banco de dados: ID %s", file_id)
                return {"message": "Arquivo não encontrado no banco"}, 404

            file_path = os.path.join(signed_xml.caminho)
            if not os.path.exists(file_path):
                logger.error("Arquivo não encontrado no banco de dados: ID %s", file_id)
                return {"message": "Arquivo não encontrado"}, 404

            os.remove(file_path)

            # Remover referência do banco
            db.session.delete(signed_xml)
            db.session.commit()
            logger.info(
                "Referência de planilha convertida deletada do banco de dados: %s",
                file_id,
            )

            logger.info("Arquivo deletado com sucesso do banco: ID %s", file_id)
            return {"message": "Arquivo deletado com sucesso"}, 200

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error("Erro ao deletar o arquivo do banco: %s", str(e))
            return {"message": "Erro ao deletar o arquivo do banco"}, 500

    def process_xml_and_save_response(
        self, spreadsheet_id: int, cnpj: str, om: str, event: str, year: int, certificate_path: str
    ) -> list:
        """
        Processa um arquivo ZIP, envia os arquivos XML, salva as respostas em um único fluxo e registra no banco de dados.

        Args:
            spreadsheet_id (int): ID da planilha associada ao evento.
            cnpj (str): CNPJ do contribuinte.
            om (str): Organização Militar (OM).
            event (str): Nome do evento.
            year (int): Ano do evento.
            certificate_path (str): Caminho do certificado para autenticação.

        Returns:
            list: Respostas do envio para cada arquivo XML.
        """
        try:
            # Instância de XmlLoteAssincrono
            xml_lote = XmlLoteAssincrono(nrInsc=cnpj)

            # Obter planilha do evento
            event_spreadsheet = db.session.query(EventSpreadsheet).filter_by(id=spreadsheet_id).first()
            if not event_spreadsheet:
                logger.error(f"Nenhum evento encontrado para OM: {om}, Evento: {event}")
                return {"message": "Nenhum evento encontrado"}, 404

            # Consultar planilha convertida
            converted_spreadsheet = db.session.query(ConvertedSpreadsheet).filter_by(planilha_id=event_spreadsheet.id).first()
            if not converted_spreadsheet:
                logger.warning(f"Planilha convertida não encontrada para planilha ID {event_spreadsheet.id}.")
                return {"message": "Planilha convertida não encontrada"}, 404

            # Consultar SignedXmls
            signed_xmls = db.session.query(SignedXmls).filter_by(planilha_convertida_id=converted_spreadsheet.id).first()
            if not signed_xmls:
                logger.error(f"SignedXmls não encontrado para planilha convertida ID {converted_spreadsheet.id}.")
                return {"message": "arquivo assinado não encontrado"}, 404

            # Processar arquivo ZIP
            with open(signed_xmls.caminho, "rb") as f:
                filename_without_extension = os.path.splitext(str(signed_xmls.id))[0]
                xml_lote.process_xmls_zip(zip_file=f, om=om, event=event, zip_filename=filename_without_extension)

            # Diretório de saída
            output_processed_dir = os.path.join("uploads", "temp", om, event, filename_without_extension)
            if not os.path.exists(output_processed_dir):
                os.makedirs(output_processed_dir, exist_ok=True)
                logger.info(f"Diretório de saída criado com sucesso: {output_processed_dir}")

            responses = []
            for xml_file in os.listdir(output_processed_dir):
                if xml_file.endswith(".xml"):
                    xml_file_path = os.path.join(output_processed_dir, xml_file)
                    response = self.send_xml_file_to_endpoint(xml_file_path, certificate_path)

                    # Salva a resposta associada ao ID da planilha
                    folder_path = os.path.join(self.SEND_FOLDER, om, event, year, "enviados")
                    if not os.path.exists(folder_path):
                        os.makedirs(folder_path, exist_ok=True)
                        logger.info(f"Pastas criadas com sucesso: {folder_path}")

                    file_path = os.path.join(folder_path, f"{signed_xmls.id}_{os.path.splitext(xml_file)[0]}.xml")
                    # Salvar o conteúdo XML no arquivo
                    with open(file_path, "w", encoding="utf-8") as file:
                        file.write(response.get("resposta", "Erro: Resposta não encontrada"))
                    
                    logger.info(f"Conteúdo salvo com sucesso em {file_path}")
                    responses.append(response)

            # Atualiza o status da planilha após envio
            event_spreadsheet.status = FileStatus.ENVIADO
            db.session.commit()

            return responses

        except Exception as e:
            logger.error(f"Erro ao processar e salvar resposta no serviço: {e}")
            return {"message": "Erro interno ao processar e salvar resposta"}, 500

    @staticmethod
    def send_xml_file_to_endpoint(xml_file_path: str, certificate_path: str) -> dict:
        """
        Envia um arquivo XML para o endpoint especificado.

        Args:
            xml_file_path (str): Caminho do arquivo XML.
            certificate_path (str): Caminho do certificado para autenticação.

        Returns:
            dict: Resposta do endpoint.
        """
        endpoint_url = os.getenv("ENDPOINT_URL")  # Insira a URL do endpoint
        try:
            with open(xml_file_path, "rb") as xml_file:
                files = {'file': xml_file}
                cert = (certificate_path, certificate_path)  # Usando o certificado para autenticação
                response = requests.post(endpoint_url, files=files, cert=cert)
                response.raise_for_status()
                return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao enviar XML para o endpoint: {e}")
            return {"message": "Erro ao enviar arquivo XML para o endpoint"}, 500
