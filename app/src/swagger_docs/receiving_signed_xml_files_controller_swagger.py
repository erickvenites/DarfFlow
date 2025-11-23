"""
Controller de Arquivos XML Assinados com documentação Swagger
"""
import os
from flask import request
from flask_restx import Resource
from src.service.ReceivingSignedXmlFilesService import ReceivingSignedXmlFilesService
from src.service.XmlSignatureService import XmlSignatureService
from src.config.logging_config import logger
from src.middleware.auth import verify_token
from datetime import datetime
from src.config.swagger_config import (
    ns_signed,
    signed_file_model,
    signature_response_model,
    send_events_response_model,
    error_model,
    upload_signed_parser,
    list_signed_parser,
    file_id_parser,
    sign_xml_parser,
    send_events_parser
)

signed_service = ReceivingSignedXmlFilesService()
signature_service = XmlSignatureService()

@ns_signed.route('/upload')
class SignedXmlUpload(Resource):
    @ns_signed.doc('upload_signed_xmls', security='Bearer')
    @ns_signed.expect(upload_signed_parser)
    @ns_signed.response(200, 'Upload realizado com sucesso')
    @ns_signed.response(400, 'Parâmetros inválidos ou arquivo não permitido', error_model)
    @ns_signed.response(500, 'Erro interno', error_model)
    @verify_token
    def post(self):
        """
        Faz upload de um arquivo ZIP contendo XMLs assinados
        
        O arquivo ZIP deve conter os arquivos XML assinados digitalmente.
        Todos os XMLs serão validados e armazenados para posterior envio ao eSocial.
        """
        try:
            from src.utils.file_handler import allowed_file_zip
            
            args = upload_signed_parser.parse_args()
            company_id = args['company_id'].upper()
            event = args['event']
            spreadsheet_id = args['spreadsheet_id']
            directory = args['file']

            logger.info(
                "Recebendo zip com arquivos XMLs assinados da company_id: %s, Evento: %s",
                company_id, event
            )

            if not company_id or not event or not spreadsheet_id:
                logger.warning(
                    "Parâmetros obrigatórios ausentes: company_id: %s, Evento: %s, Planilha ID: %s",
                    company_id, event, spreadsheet_id
                )
                return {"message": "company_id, event, file e ID da spreadsheet são obrigatórios"}, 400

            if directory.filename == "":
                logger.warning("Nenhum file foi selecionado")
                return {"message": "Nenhum file foi selecionado"}, 400

            if not allowed_file_zip(directory.filename):
                logger.warning("Extensão do file não permitida: %s", directory.filename)
                return {"message": "Arquivo não permitido"}, 400

            response, status_code = signed_service.save_signed_xml(
                company_id=company_id,
                event=event,
                year=str(datetime.now().year),
                zip_file=directory,
                spreadsheet_id=spreadsheet_id
            )

            return response, status_code

        except Exception as e:
            logger.error("Erro inesperado ao salvar o diretório de arquivos assinados: %s", str(e))
            return {"message": "Ocorreu um erro ao receber os arquivos"}, 500


@ns_signed.route('/list')
class SignedXmlList(Resource):
    @ns_signed.doc('list_signed_xmls')
    @ns_signed.expect(list_signed_parser)
    @ns_signed.response(200, 'Arquivos listados com sucesso', [signed_file_model])
    @ns_signed.response(400, 'Parâmetros inválidos', error_model)
    @ns_signed.response(500, 'Erro interno', error_model)
    def get(self):
        """
        Lista todos os arquivos assinados

        Pode listar todos ou filtrar por empresa, evento e ano.
        Filtros são opcionais.
        """
        try:
            args = list_signed_parser.parse_args()
            company_id = args.get('company_id')
            event = args.get('event')
            year = args.get('year')

            # Se não tem filtros, lista todos
            if not company_id and not event and not year:
                response, status_code = signed_service.list_all_without_filters()
                return response, status_code

            # Se tem apenas company_id, filtra apenas por empresa
            if company_id and not event and not year:
                response, status_code = signed_service.list_by_company(company_id.upper())
                logger.info("Arquivos assinados listados para company_id: %s", company_id)
                return response, status_code

            # Se tem todos os filtros, usa a busca completa
            if company_id and event and year:
                response, status_code = signed_service.list_all(
                    company_id=company_id.upper(),
                    event=event,
                    year=year
                )
                return response, status_code

            # Se tem filtros parciais (não todos), retorna erro
            return {"message": "Use company_id sozinho OU todos os filtros (company_id, event, year)"}, 400

        except Exception as e:
            logger.error("Erro ao listar diretórios: %s", str(e))
            return {"message": "Erro ao listar diretórios"}, 500


@ns_signed.route('')
class SignedXmlDetail(Resource):
    @ns_signed.doc('get_signed_xml')
    @ns_signed.expect(file_id_parser)
    @ns_signed.response(200, 'Arquivo encontrado', signed_file_model)
    @ns_signed.response(400, 'ID não fornecido', error_model)
    @ns_signed.response(404, 'Arquivo não encontrado', error_model)
    @ns_signed.response(500, 'Erro interno', error_model)
    def get(self):
        """
        Busca um arquivo assinado pelo ID
        
        Retorna os detalhes completos de um arquivo ZIP assinado específico.
        """
        args = file_id_parser.parse_args()
        file_id = args['arquivo_id']

        if not file_id:
            logger.warning("Parâmetro obrigatório ausente: arquivo_id")
            return {"message": "O parâmetro arquivo_id é obrigatório"}, 400
        
        try:
            response, status_code = signed_service.list_by_id(file_id)

            if not response:
                logger.warning("Arquivo inexistente para o id: %s", file_id)
                return {"message": "Arquivo não encontrado"}, 404
            
            return response, status_code
        except Exception as e:
            logger.error(f"Erro ao buscar file: {str(e)}")
            return {"message": "Erro interno do servidor."}, 500

    @ns_signed.doc('delete_signed_xml', security='Bearer')
    @ns_signed.expect(file_id_parser)
    @ns_signed.response(200, 'Arquivo deletado com sucesso')
    @ns_signed.response(400, 'ID não fornecido', error_model)
    @ns_signed.response(500, 'Erro ao deletar', error_model)
    @verify_token
    def delete(self):
        """
        Exclui um arquivo ZIP de XMLs assinados
        
        Remove permanentemente o arquivo ZIP do sistema.
        """
        try:
            args = file_id_parser.parse_args()
            file_id = args['arquivo_id']

            if not file_id:
                logger.warning("Parâmetro obrigatório ausente: arquivo_id")
                return {"message": "file_id é obrigatório"}, 400

            response, status_code = signed_service.delete(file_id)
            return response, status_code

        except Exception as e:
            logger.error("Erro ao deletar o file: %s", str(e))
            return {"message": "Erro ao deletar o file"}, 500


@ns_signed.route('/sign')
class XmlSigner(Resource):
    @ns_signed.doc('sign_xmls')
    @ns_signed.expect(sign_xml_parser)
    @ns_signed.response(200, 'XMLs assinados com sucesso', signature_response_model)
    @ns_signed.response(400, 'Parâmetros inválidos ou status incorreto', error_model)
    @ns_signed.response(404, 'Planilha ou XMLs não encontrados', error_model)
    @ns_signed.response(500, 'Erro ao assinar', error_model)
    def post(self):
        """
        Assina digitalmente os arquivos XML de uma planilha
        
        Busca os XMLs gerados a partir de uma planilha processada e assina
        cada um deles digitalmente usando o certificado digital configurado.
        A planilha deve estar no status CONVERTIDO.
        
        Requer certificado digital válido configurado no servidor.
        """
        try:
            from src.models.database import EventSpreadsheet, ConvertedSpreadsheet, FileStatus
            from src import db
            import glob

            args = sign_xml_parser.parse_args()
            spreadsheet_id = args['spreadsheet_id']
            event = args['event']
            certificate_password = args.get('certificate_password')

            if not spreadsheet_id or not event:
                return {
                    "message": "Parâmetros 'spreadsheet_id' e 'event' são obrigatórios"
                }, 400

            logger.info(f"Iniciando assinatura de XMLs para spreadsheet {spreadsheet_id}")

            # Busca a spreadsheet
            spreadsheet = EventSpreadsheet.query.get(spreadsheet_id)
            if not spreadsheet:
                return {"message": "Planilha não encontrada"}, 404

            # Verifica status
            if spreadsheet.status != FileStatus.CONVERTIDO:
                return {
                    "message": f"Planilha deve estar no status CONVERTIDO. Status atual: {spreadsheet.status.value}"
                }, 400

            # Busca XMLs convertidos
            converted = ConvertedSpreadsheet.query.filter_by(spreadsheet_id=spreadsheet_id).first()
            if not converted:
                return {"message": "Nenhum XML convertido encontrado para esta spreadsheet"}, 404

            xml_dir = converted.path
            if not os.path.exists(xml_dir):
                return {"message": f"Diretório de XMLs não encontrado: {xml_dir}"}, 404

            xml_files = glob.glob(os.path.join(xml_dir, "*.xml"))
            if not xml_files:
                return {"message": "Nenhum file XML encontrado no diretório"}, 404

            logger.info(f"Encontrados {len(xml_files)} file(s) XML para assinar")

            # Diretório para XMLs assinados
            signed_dir = os.path.join(xml_dir, "assinados")
            os.makedirs(signed_dir, exist_ok=True)

            # Assina cada XML
            signed_count = 0
            errors = []

            for xml_file in xml_files:
                try:
                    with open(xml_file, 'r', encoding='utf-8') as f:
                        xml_content = f.read()

                    signed_xml = signature_service.sign_xml(
                        xml_content=xml_content,
                        event_type=event,
                        password=certificate_password
                    )

                    filename = os.path.basename(xml_file)
                    signed_filename = filename.replace('.xml', '_signed.xml')
                    signed_path = os.path.join(signed_dir, signed_filename)

                    with open(signed_path, 'w', encoding='utf-8') as f:
                        f.write(signed_xml)

                    signed_count += 1
                    logger.info(f"XML assinado com sucesso: {filename}")

                except Exception as e:
                    error_msg = f"Erro ao assinar {os.path.basename(xml_file)}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            # Atualiza status se todos foram assinados
            if signed_count == len(xml_files):
                spreadsheet.status = FileStatus.ASSINADO
                db.session.commit()
                logger.info(f"Status da spreadsheet atualizado para ASSINADO")

            response = {
                "message": "Processo de assinatura concluído",
                "total_xmls": len(xml_files),
                "signed_xmls": signed_count,
                "xmls_with_error": len(errors),
                "signed_directory": signed_dir,
                "spreadsheet_status": spreadsheet.status.value
            }

            if errors:
                response["erros"] = errors

            status_code = 200 if signed_count > 0 else 500
            return response, status_code

        except Exception as e:
            logger.error(f"Erro ao assinar XMLs: {str(e)}")
            return {"message": f"Erro ao assinar XMLs: {str(e)}"}, 500


@ns_signed.route('/send')
class EventSender(Resource):
    @ns_signed.doc('send_events', security='Bearer')
    @ns_signed.expect(send_events_parser)
    @ns_signed.response(200, 'Eventos enviados com sucesso', send_events_response_model)
    @ns_signed.response(500, 'Erro ao enviar eventos', error_model)
    @verify_token
    def post(self):
        """
        Processa e envia eventos assinados para o eSocial
        
        Envia os XMLs assinados para o sistema eSocial de forma assíncrona.
        Requer que os XMLs já estejam assinados digitalmente.
        """
        try:
            args = send_events_parser.parse_args()
            company_id = args['company_id'].upper()
            event = args['event']
            spreadsheet_id = args['spreadsheet_id']
            cnpj = args['cnpj']
            year = args['year']
            certificate_path = os.getenv("CERTIFICATE_PATH")

            if not certificate_path:
                logger.error("CERTIFICATE_PATH não configurado no ambiente")
                return {"message": "Erro de configuração: certificado não encontrado"}, 500

            response = signed_service.process_xml_and_save_response(
                spreadsheet_id=spreadsheet_id,
                cnpj=cnpj,
                company_id=company_id,
                event=event,
                year=year,
                certificate_path=certificate_path,
            )

            if response:
                return {"message": "Lote processado com sucesso", "response": response}, 200
            else:
                return {"message": "Falha ao processar o lote"}, 500

        except Exception as e:
            return {"message": "Erro no processamento do lote", "error": str(e)}, 500