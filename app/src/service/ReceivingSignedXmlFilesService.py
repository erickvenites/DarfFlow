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

    def list_all(self, company_id: str, event: str, year: int) -> dict:
        """
        Lista todos os dados dos arquivos assinados para uma OM, event e year específicos.

        Args:
            company_id (str): Identificador da empresa.
            event (str): Nome do event.
            year (int): Ano do event.

        Returns:
            dict: Resposta com os dados dos arquivos XML ou message de erro.
        """
        try:
            # Consultando os eventos ASSINADOS associados
            event_spreadsheets = (
                db.session.query(EventSpreadsheet)
                .filter(
                    EventSpreadsheet.company_id == company_id,
                    EventSpreadsheet.event == event,
                    extract("year", EventSpreadsheet.received_date) == year,
                    EventSpreadsheet.status == FileStatus.ASSINADO,
                )
                .all()
            )

            if not event_spreadsheets:
                logger.error(
                    f"Nenhum event encontrado para company_id: {company_id}, Evento: {event}, Ano: {year}"
                )
                return {"message": "Nenhum event encontrado"}, 404

            # Obter os IDs das planilhas
            event_ids = [es.id for es in event_spreadsheets]

            # Buscar todas as planilhas convertidas associadas
            converted_spreadsheets = (
                db.session.query(ConvertedSpreadsheet)
                .filter(ConvertedSpreadsheet.spreadsheet_id.in_(event_ids))
                .all()
            )

            if not converted_spreadsheets:
                logger.warning(f"Nenhuma spreadsheet convertida encontrada para os eventos.")
                return {"message": "Nenhuma spreadsheet convertida encontrada"}, 404

            # Obter os IDs das planilhas convertidas
            converted_ids = [cs.id for cs in converted_spreadsheets]

            # Buscar todos os XMLs assinados associados
            signed_xmls = (
                db.session.query(SignedXmls)
                .filter(SignedXmls.converted_spreadsheet_id.in_(converted_ids))
                .all()
            )

            if not signed_xmls:
                logger.warning(f"Nenhum file XML assinado encontrado.")
                return {"message": "Nenhum file XML assinado encontrado"}, 404

            # Construir resultado final utilizando to_dict()
            zip_files = [
                {
                    **signed.to_dict(),  # Usando o método to_dict() da classe SignedXmls
                    "event": es.event,
                    "company_id": es.company_id,
                }
                for signed in signed_xmls
                for es in event_spreadsheets if signed.converted.spreadsheet_id == es.id
            ]

            logger.info(f"Arquivos ZIP encontrados: {len(zip_files)}")
            return {"data": zip_files}, 200

        except SQLAlchemyError as e:
            logger.error(f"Erro ao consultar banco de dados: {e}")
            return {"message": "Erro interno no servidor"}, 500
        except Exception as e:
            logger.error(f"Erro inesperado ao listar diretórios: {e}")
            return {"message": "Erro ao listar diretórios"}, 500

    def list_all_without_filters(self) -> dict:
        """
        Lista TODOS os arquivos XML assinados sem filtros.

        Returns:
            dict: Resposta com todos os arquivos XML assinados ou lista vazia.
        """
        try:
            # Buscar todos os XMLs assinados
            signed_xmls = db.session.query(SignedXmls).all()

            if not signed_xmls:
                logger.info("Nenhum arquivo XML assinado encontrado")
                return {"data": []}, 200

            # Construir resultado com informações completas
            result_data = []
            for signed in signed_xmls:
                try:
                    # Obter informações da planilha associada
                    event_spreadsheet = (
                        db.session.query(EventSpreadsheet)
                        .join(ConvertedSpreadsheet)
                        .filter(ConvertedSpreadsheet.id == signed.converted_spreadsheet_id)
                        .first()
                    )

                    signed_dict = signed.to_dict()
                    if event_spreadsheet:
                        signed_dict["event"] = event_spreadsheet.event
                        signed_dict["company_id"] = event_spreadsheet.company_id

                    result_data.append(signed_dict)
                except Exception as e:
                    logger.warning(f"Erro ao processar XML assinado ID {signed.id}: {e}")
                    continue

            logger.info(f"Encontrados {len(result_data)} arquivos XML assinados")
            return {"data": result_data}, 200

        except SQLAlchemyError as e:
            logger.error(f"Erro ao consultar banco de dados: {e}")
            return {"message": "Erro interno no servidor"}, 500
        except Exception as e:
            logger.error(f"Erro inesperado ao listar XMLs assinados: {e}")
            return {"message": "Erro ao listar XMLs assinados"}, 500

    def list_by_company(self, company_id: str) -> dict:
        """
        Lista todos os arquivos XML assinados de uma empresa específica.

        Args:
            company_id (str): Identificador da empresa.

        Returns:
            dict: Resposta com os arquivos da empresa ou lista vazia.
        """
        try:
            # Busca XMLs assinados da empresa
            signed_xmls = (
                db.session.query(SignedXmls)
                .join(ConvertedSpreadsheet, SignedXmls.converted_spreadsheet_id == ConvertedSpreadsheet.id)
                .join(EventSpreadsheet, ConvertedSpreadsheet.spreadsheet_id == EventSpreadsheet.id)
                .filter(EventSpreadsheet.company_id == company_id)
                .all()
            )

            if not signed_xmls:
                logger.info(f"Nenhum arquivo XML assinado encontrado para {company_id}")
                return {"data": []}, 200

            result_data = []
            for signed in signed_xmls:
                try:
                    signed_dict = signed.to_dict()
                    result_data.append(signed_dict)
                except Exception as e:
                    logger.warning(f"Erro ao processar XML assinado ID {signed.id}: {e}")
                    continue

            logger.info(f"Encontrados {len(result_data)} arquivos XML assinados para {company_id}")
            return {"data": result_data}, 200

        except SQLAlchemyError as e:
            logger.error(f"Erro ao consultar banco de dados: {e}")
            return {"message": "Erro interno no servidor"}, 500
        except Exception as e:
            logger.error(f"Erro inesperado ao listar XMLs assinados: {e}")
            return {"message": "Erro ao listar XMLs assinados"}, 500

    def list_by_id(self, file_id: int) -> dict:
        """
        Lista um file XML assinado pelo ID.

        Args:
            file_id (int): ID do file XML.

        Returns:
            dict: Dados do file ou message de erro.
        """
        try:
            if not file_id:
                logger.error("O id está vazio")
                return {"message": "Id do file é obrigatório"}, 400
                
            # Buscando a spreadsheet convertida com o id fornecido
            signed = SignedXmls.query.filter_by(id=file_id).first()

            if not signed:
                logger.error(f"Arquivo não encontrado para o id: {file_id}")
                return {"message": "Arquivo não encontrado"}, 404

            # Retorna os dados da spreadsheet convertida
            return {"data": signed.to_dict()}, 200

        except ValueError:
            logger.error(f"ID inválido: {file_id}")
            return {"message": "ID inválido"}, 400
        except Exception as e:
            logger.error(f"Erro ao buscar file: {str(e)}")
            return {"message": "Erro interno ao buscar o file."}, 500

    def save_signed_xml(self, company_id: str, event: str, year: str, zip_file, spreadsheet_id: int) -> dict:
        """
        Salva um file ZIP contendo XMLs assinados, associando-o a uma spreadsheet convertida.

        Args:
            company_id (str): Identificador da empresa.
            event (str): Nome do event.
            year (str): Ano do event.
            zip_file: Arquivo ZIP contendo os XMLs assinados.
            spreadsheet_id (int): ID da spreadsheet convertida associada.

        Returns:
            dict: Mensagem de sucesso ou erro.
        """
        folder_path = os.path.join(self.SIGNED_FOLDER, company_id, event, year)

        # Verifica se o diretório existe
        if not os.path.exists(folder_path):
            os.makedirs(folder_path,exist_ok=True)
            logger.info(" diretório referente ao path %s criado com sucesso", folder_path)
            #return {"message": "O diretório referente não existe"}, 404

        try:
            # Buscar a spreadsheet convertida associada
            converted_spreadsheet = ConvertedSpreadsheet.query.filter_by(spreadsheet_id=spreadsheet_id).first()
            if not converted_spreadsheet:
                logger.error("Nenhuma spreadsheet convertida associada ao ID %s", spreadsheet_id)
                return {"message": "Planilha convertida não encontrada"}, 404

            # Verificar se já existe um file XML assinado associado à spreadsheet convertida
            existing_signed_xml = db.session.query(SignedXmls).filter_by(converted_spreadsheet_id=converted_spreadsheet.id).first()
            if existing_signed_xml:
                logger.error(
                    "Já existe um file XML assinado associado à spreadsheet convertida com ID %s",
                    converted_spreadsheet.id,
                )
                return {
                    "message": "Apenas um file XML pode ser associado a essa spreadsheet convertida"
                }, 400

            # Salvar o file ZIP com o nome correto
            zip_filename = secure_filename(zip_file.filename)  # Nome seguro para o file
            zip_file_path = os.path.join(folder_path, zip_filename)
            zip_file.save(zip_file_path)

            # Verificar se o file foi salvo corretamente
            if not os.path.exists(zip_file_path) or os.path.getsize(zip_file_path) == 0:
                logger.error("Erro ao salvar ou file ZIP está vazio: %s", zip_file_path)
                return {"message": "Erro ao salvar o file ZIP ou file vazio"}, 500

            # Criar a entrada de XML assinado
            signed_xmls = SignedXmls(
                converted_spreadsheet_id=converted_spreadsheet.id,  # Relaciona ao XML convertido
                path=zip_file_path,
            )
            db.session.add(signed_xmls)

            # Atualizar o status da spreadsheet original
            converted_spreadsheet.status = FileStatus.ASSINADO  # Atualiza o status para 'ASSINADO'
            db.session.commit()

            logger.info("Arquivo ZIP salvo e status da spreadsheet atualizado com sucesso.")
            return {"message": "Arquivo enviado com sucesso"}, 201

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error("Erro ao salvar ou atualizar o banco de dados: %s", str(e))
            return {"message": "Erro ao salvar no banco de dados"}, 500
        except Exception as e:
            logger.error("Erro inesperado ao salvar o file: %s", str(e))
            return {"message": "Erro ao salvar o file"}, 500


    def delete(self, file_id: int) -> dict:
        """
        Deleta um file XML assinado do banco de dados e do sistema de arquivos.

        Args:
            file_id (int): ID do file XML.

        Returns:
            dict: Mensagem de sucesso ou erro.
        """
        try:
            # Buscar a referência no banco de dados
            signed_xml = SignedXmls.query.filter_by(id=file_id).first()
            if not signed_xml:
                logger.error("Arquivo não encontrado no banco de dados: ID %s", file_id)
                return {"message": "Arquivo não encontrado no banco"}, 404

            file_path = os.path.join(signed_xml.path)
            if not os.path.exists(file_path):
                logger.error("Arquivo não encontrado no banco de dados: ID %s", file_id)
                return {"message": "Arquivo não encontrado"}, 404

            os.remove(file_path)

            # Remover referência do banco
            db.session.delete(signed_xml)
            db.session.commit()
            logger.info(
                "Referência de spreadsheet convertida deletada do banco de dados: %s",
                file_id,
            )

            logger.info("Arquivo deletado com sucesso do banco: ID %s", file_id)
            return {"message": "Arquivo deletado com sucesso"}, 200

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error("Erro ao deletar o file do banco: %s", str(e))
            return {"message": "Erro ao deletar o file do banco"}, 500

    def process_xml_and_save_response(
        self, spreadsheet_id: int, cnpj: str, company_id: str, event: str, year: int, certificate_path: str
    ) -> list:
        """
        Processa um file ZIP, envia os arquivos XML, salva as respostas em um único fluxo e registra no banco de dados.

        Args:
            spreadsheet_id (int): ID da spreadsheet associada ao event.
            cnpj (str): CNPJ do contribuinte.
            company_id (str): Identificador da empresa (OM).
            event (str): Nome do event.
            year (int): Ano do event.
            certificate_path (str): Caminho do certificado para autenticação.

        Returns:
            list: Respostas do envio para cada file XML.
        """
        try:
            # Instância de XmlLoteAssincrono
            xml_lote = XmlLoteAssincrono(nrInsc=cnpj)

            # Obter spreadsheet do event
            event_spreadsheet = db.session.query(EventSpreadsheet).filter_by(id=spreadsheet_id).first()
            if not event_spreadsheet:
                logger.error(f"Nenhum event encontrado para company_id: {company_id}, Evento: {event}")
                return {"message": "Nenhum event encontrado"}, 404

            # Consultar spreadsheet convertida
            converted_spreadsheet = db.session.query(ConvertedSpreadsheet).filter_by(spreadsheet_id=event_spreadsheet.id).first()
            if not converted_spreadsheet:
                logger.warning(f"Planilha convertida não encontrada para spreadsheet ID {event_spreadsheet.id}.")
                return {"message": "Planilha convertida não encontrada"}, 404

            # Consultar SignedXmls
            signed_xmls = db.session.query(SignedXmls).filter_by(converted_spreadsheet_id=converted_spreadsheet.id).first()
            if not signed_xmls:
                logger.error(f"SignedXmls não encontrado para spreadsheet convertida ID {converted_spreadsheet.id}.")
                return {"message": "file assinado não encontrado"}, 404

            # Processar file ZIP
            with open(signed_xmls.path, "rb") as f:
                filename_without_extension = os.path.splitext(str(signed_xmls.id))[0]
                xml_lote.process_xmls_zip(zip_file=f, company_id=company_id, event=event, zip_filename=filename_without_extension)

            # Diretório de saída
            output_processed_dir = os.path.join("uploads", "temp", company_id, event, filename_without_extension)
            if not os.path.exists(output_processed_dir):
                os.makedirs(output_processed_dir, exist_ok=True)
                logger.info(f"Diretório de saída criado com sucesso: {output_processed_dir}")

            responses = []
            for xml_file in os.listdir(output_processed_dir):
                if xml_file.endswith(".xml"):
                    xml_file_path = os.path.join(output_processed_dir, xml_file)
                    response = self.send_xml_file_to_endpoint(xml_file_path, certificate_path)

                    # Salva a resposta associada ao ID da spreadsheet
                    folder_path = os.path.join(self.SEND_FOLDER, company_id, event, year, "enviados")
                    if not os.path.exists(folder_path):
                        os.makedirs(folder_path, exist_ok=True)
                        logger.info(f"Pastas criadas com sucesso: {folder_path}")

                    file_path = os.path.join(folder_path, f"{signed_xmls.id}_{os.path.splitext(xml_file)[0]}.xml")
                    # Salvar o conteúdo XML no file
                    with open(file_path, "w", encoding="utf-8") as file:
                        file.write(response.get("resposta", "Erro: Resposta não encontrada"))
                    
                    logger.info(f"Conteúdo salvo com sucesso em {file_path}")
                    responses.append(response)

            # Atualiza o status da spreadsheet após envio
            event_spreadsheet.status = FileStatus.ENVIADO
            db.session.commit()

            return responses

        except Exception as e:
            logger.error(f"Erro ao processar e salvar resposta no serviço: {e}")
            return {"message": "Erro interno ao processar e salvar resposta"}, 500

    @staticmethod
    def send_xml_file_to_endpoint(xml_file_path: str, certificate_path: str) -> dict:
        """
        Envia um file XML para o endpoint especificado.

        Args:
            xml_file_path (str): Caminho do file XML.
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
            return {"message": "Erro ao enviar file XML para o endpoint"}, 500
