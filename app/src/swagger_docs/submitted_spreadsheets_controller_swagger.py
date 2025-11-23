"""
Controller de Planilhas Submetidas com documentação Swagger
"""
from flask import request, send_file
from flask_restx import Resource
from src.service.SubmittedSpreadsheetsService import SubmittedSpreadsheetsService
from src.config.logging_config import logger
from src.models.database import EventSpreadsheet, FileStatus
from src import db
from src.middleware.auth import verify_token
from src.config.swagger_config import (
    ns_spreadsheets, 
    spreadsheet_model, 
    upload_response_model,
    error_model,
    upload_parser,
    download_spreadsheet_parser,
    get_spreadsheets_parser,
    delete_spreadsheet_parser,
    process_spreadsheet_parser
)

received_service = SubmittedSpreadsheetsService()

@ns_spreadsheets.route('/upload')
class SpreadsheetUpload(Resource):
    @ns_spreadsheets.doc('upload_spreadsheet')
    @ns_spreadsheets.expect(upload_parser)
    @ns_spreadsheets.response(200, 'Upload realizado com sucesso', upload_response_model)
    @ns_spreadsheets.response(400, 'Parâmetros inválidos', error_model)
    @ns_spreadsheets.response(500, 'Erro interno', error_model)
    def post(self):
        """
        Faz upload de uma planilha para processamento

        Aceita arquivos Excel (.xlsx, .xls) ou CSV contendo os dados dos eventos.
        A planilha será validada e armazenada para posterior processamento.
        """
        try:
            # Usar request diretamente ao invés do parser para evitar erros de parsing
            company_id = request.args.get('company_id')
            event = request.args.get('event')

            if not company_id or not event:
                return {"message": "company_id e event são obrigatórios"}, 400

            if 'spreadsheet' not in request.files:
                return {"message": "Nenhuma planilha enviada"}, 400

            file = request.files['spreadsheet']

            if file.filename == "":
                return {"message": "Nenhuma planilha selecionada"}, 400

            response_message, status_code = received_service.process_upload(file, company_id, event)
            return response_message, status_code

        except Exception as e:
            logger.error("Erro ao processar o upload: %s", str(e))
            return {"message": "Ocorreu um erro ao processar o upload"}, 500


@ns_spreadsheets.route('/download')
class SpreadsheetDownload(Resource):
    @ns_spreadsheets.doc('download_spreadsheet', security='Bearer')
    @ns_spreadsheets.expect(download_spreadsheet_parser)
    @ns_spreadsheets.response(200, 'Download realizado com sucesso')
    @ns_spreadsheets.response(400, 'ID da planilha não fornecido', error_model)
    @ns_spreadsheets.response(404, 'Planilha não encontrada', error_model)
    @ns_spreadsheets.response(500, 'Erro interno', error_model)
    @verify_token
    def post(self):
        """
        Faz download de uma planilha registrada
        
        Retorna o arquivo original da planilha que foi enviada anteriormente.
        """
        try:
            args = download_spreadsheet_parser.parse_args()
            spreadsheet_id = args['spreadsheet_id']

            logger.info("Download solicitado para Planilha ID: %s", spreadsheet_id)

            if not spreadsheet_id:
                return {"message": "ID da planilha é obrigatório!"}, 400

            response_message, status_code, file_path = received_service.download_file(spreadsheet_id)
            if status_code != 200:
                logger.error("Erro ao realizar download: %s", response_message)
                return response_message, status_code

            logger.info("Download concluído com sucesso: %s", file_path)
            return send_file(file_path, as_attachment=True)

        except Exception as e:
            logger.error("Erro ao fazer o download: %s", str(e))
            return {"message": "Ocorreu um erro ao fazer o download"}, 500


@ns_spreadsheets.route('/')
class SpreadsheetList(Resource):
    @ns_spreadsheets.doc('get_spreadsheets')
    @ns_spreadsheets.expect(get_spreadsheets_parser)
    @ns_spreadsheets.response(200, 'Planilhas encontradas', [spreadsheet_model])
    @ns_spreadsheets.response(400, 'Parâmetros inválidos', error_model)
    @ns_spreadsheets.response(404, 'Planilha não encontrada', error_model)
    @ns_spreadsheets.response(500, 'Erro interno', error_model)
    def get(self):
        """
        Busca planilhas por ID específico, por filtros, ou lista todas

        Três modos de operação:
        - Com spreadsheet_id: retorna uma planilha específica
        - Com company_id, year e event: retorna planilhas filtradas
        - Sem parâmetros: retorna todas as planilhas
        """
        args = get_spreadsheets_parser.parse_args()
        spreadsheet_id = args.get('spreadsheet_id')

        # Busca por ID específico
        if spreadsheet_id:
            try:
                response, status_code = received_service.get_spreadsheet_by_id(spreadsheet_id)
                return response, status_code
            except Exception as e:
                logger.error(f"Erro ao buscar spreadsheet por ID: {str(e)}")
                return {"message": "Erro interno do servidor."}, 500

        # Busca com filtros ou todas
        company_id = args.get('company_id')
        year = args.get('year')
        event = args.get('event')

        try:
            # Se não tem nenhum parâmetro, retorna todas
            if not company_id and not year and not event:
                spreadsheets = EventSpreadsheet.query.order_by(EventSpreadsheet.received_date.desc()).all()
            else:
                # Monta filtros dinâmicos
                filters = []
                if company_id:
                    filters.append(EventSpreadsheet.company_id == company_id.upper())
                if year:
                    filters.append(db.extract('year', EventSpreadsheet.received_date) == int(year))
                if event:
                    filters.append(EventSpreadsheet.event == event)

                spreadsheets = EventSpreadsheet.query.filter(*filters).order_by(EventSpreadsheet.received_date.desc()).all()

            spreadsheets_data = [
                {
                    "id": str(spreadsheet.id),
                    "company_id": spreadsheet.company_id,
                    "event": spreadsheet.event,
                    "filename": spreadsheet.filename,
                    "file_type": spreadsheet.file_type,
                    "status": spreadsheet.status.value,
                    "path": spreadsheet.path,
                    "received_date": spreadsheet.received_date.isoformat(),
                }
                for spreadsheet in spreadsheets
            ]

            return spreadsheets_data, 200

        except Exception as e:
            logger.error(f"Erro ao buscar planilhas: {str(e)}")
            return {"message": "Erro interno do servidor."}, 500

    @ns_spreadsheets.doc('delete_spreadsheet', security='Bearer')
    @ns_spreadsheets.expect(delete_spreadsheet_parser)
    @ns_spreadsheets.response(200, 'Planilha deletada com sucesso')
    @ns_spreadsheets.response(400, 'ID não fornecido', error_model)
    @ns_spreadsheets.response(500, 'Erro interno', error_model)
    @verify_token
    def delete(self):
        """
        Deleta uma planilha e eventos associados
        
        Remove a planilha do sistema, incluindo todos os arquivos e registros relacionados.
        """
        try:
            args = delete_spreadsheet_parser.parse_args()
            spreadsheet_id = args['spreadsheet_id']

            logger.info("Deletando spreadsheet com id: %s", spreadsheet_id)

            if not spreadsheet_id:
                return {"message": "ID do event é obrigatório!"}, 400

            response_message, status_code = received_service.delete_event_and_associated_spreadsheet(spreadsheet_id)

            if status_code != 200:
                logger.error("Erro ao deletar event: %s", response_message)

            logger.info("Evento deletado com sucesso para a spreadsheet com ID: %s", spreadsheet_id)
            return response_message, status_code

        except Exception as e:
            logger.error("Erro ao deletar event: %s", str(e))
            return {"message": "Ocorreu um erro ao deletar o event"}, 500


@ns_spreadsheets.route('/process')
class SpreadsheetProcess(Resource):
    @ns_spreadsheets.doc('process_spreadsheet')
    @ns_spreadsheets.expect(process_spreadsheet_parser)
    @ns_spreadsheets.response(200, 'Planilha processada com sucesso')
    @ns_spreadsheets.response(400, 'Parâmetros inválidos', error_model)
    @ns_spreadsheets.response(500, 'Erro no processamento', error_model)
    def post(self):
        """
        Processa uma planilha e gera arquivos XML
        
        Converte os dados da planilha em arquivos XML no formato do eSocial.
        A planilha deve estar no status RECEBIDO.
        """
        try:
            args = process_spreadsheet_parser.parse_args()
            spreadsheet_id = args['spreadsheet_id']
            cnpj = args['cnpj']

            if not spreadsheet_id or not cnpj:
                return {"message": "ID da spreadsheet e CNPJ são obrigatórios"}, 400

            response_message, status_code = received_service.process_spreadsheet(
                spreadsheet_id=spreadsheet_id, 
                cnpj=cnpj
            )
            return response_message, status_code

        except Exception as e:
            logger.error("Erro ao processar a spreadsheet: %s", str(e))
            return {"message": "Erro ao processar a spreadsheet"}, 500