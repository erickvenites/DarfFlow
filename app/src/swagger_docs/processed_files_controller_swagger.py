"""
Controller de Arquivos Processados com documentação Swagger
"""
from flask import request, send_file
from flask_restx import Resource
from src.service.ProcessedFilesService import ProcessedFilesService
from src.config.logging_config import logger
from src.middleware.auth import verify_token
from src.config.swagger_config import (
    ns_processed,
    processed_file_model,
    error_model,
    list_processed_parser,
    file_id_parser,
    download_processed_parser
)

processed_service = ProcessedFilesService()

@ns_processed.route('/list')
class ProcessedFileList(Resource):
    @ns_processed.doc('list_processed_files', security='Bearer')
    @ns_processed.expect(list_processed_parser)
    @ns_processed.response(200, 'Arquivos listados com sucesso', [processed_file_model])
    @ns_processed.response(400, 'Parâmetros inválidos', error_model)
    @ns_processed.response(500, 'Erro interno', error_model)
    @verify_token
    def get(self):
        """
        Lista todos os diretórios de XMLs processados
        
        Retorna uma lista de todos os diretórios contendo XMLs processados
        para uma combinação específica de empresa, ano e evento.
        """
        args = list_processed_parser.parse_args()
        company_id = args['company_id'].upper()
        year = args['year']
        event = args['event']

        if not company_id or not year or not event:
            logger.warning(
                "Parâmetros obrigatórios ausentes: company_id: %s, Ano: %s, Evento: %s",
                company_id, year, event
            )
            return {"message": "company_id, year e event são obrigatórios"}, 400

        response, status_code = processed_service.list_all(
            company_id=company_id, year=year, event=event
        )

        logger.info(
            "Diretórios listados: company_id: %s, Ano: %s, Código do Evento: %s",
            company_id, year, event
        )
        return response, status_code


@ns_processed.route('')
class ProcessedFileDetail(Resource):
    @ns_processed.doc('get_processed_file', security='Bearer')
    @ns_processed.expect(file_id_parser)
    @ns_processed.response(200, 'Arquivo encontrado', processed_file_model)
    @ns_processed.response(400, 'ID não fornecido', error_model)
    @ns_processed.response(404, 'Arquivo não encontrado', error_model)
    @ns_processed.response(500, 'Erro interno', error_model)
    @verify_token
    def get(self):
        """
        Busca um arquivo processado específico pelo ID
        
        Retorna os detalhes completos de um arquivo processado individual.
        """
        args = file_id_parser.parse_args()
        file_id = args['arquivo_id']

        if not file_id:
            logger.warning("Parâmetro obrigatório ausente: arquivo_id")
            return {"message": "O parâmetro arquivo_id é obrigatório"}, 400
        
        try:
            response, status_code = processed_service.get_by_id(file_id)

            if not response:
                logger.warning("Arquivo inexistente para o id: %s", file_id)
                return {"message": "Arquivo não encontrado"}, 404
            
            return response, status_code
        except Exception as e:
            logger.error(f"Erro ao buscar file: {str(e)}")
            return {"message": "Erro interno do servidor."}, 500

    @ns_processed.doc('delete_processed_file', security='Bearer')
    @ns_processed.expect(file_id_parser)
    @ns_processed.response(200, 'Arquivo deletado com sucesso')
    @ns_processed.response(400, 'ID não fornecido', error_model)
    @ns_processed.response(500, 'Erro ao deletar', error_model)
    @verify_token
    def delete(self):
        """
        Exclui um diretório de XMLs processados
        
        Remove permanentemente o diretório e todos os arquivos XML contidos nele.
        """
        args = file_id_parser.parse_args()
        directory_id = args['arquivo_id']

        if not directory_id:
            logger.warning("Parâmetro 'arquivo_id' ausente")
            return {"message": "'arquivo_id' é obrigatório!"}, 400

        logger.info("Solicitação de exclusão para arquivo_id: %s", directory_id)

        response, status_code = processed_service.delete_directory(directory_id=directory_id)

        if status_code != 200:
            logger.error("Erro ao deletar diretório: %s", response)

        logger.info("Diretório deletado: arquivo_id: %s", directory_id)
        return response, status_code


@ns_processed.route('/download')
class ProcessedFileDownload(Resource):
    @ns_processed.doc('download_processed_files', security='Bearer')
    @ns_processed.expect(download_processed_parser)
    @ns_processed.response(200, 'Download realizado com sucesso')
    @ns_processed.response(400, 'ID não fornecido', error_model)
    @ns_processed.response(404, 'Arquivo não encontrado', error_model)
    @ns_processed.response(500, 'Erro interno', error_model)
    @verify_token
    def post(self):
        """
        Faz download de todos os XMLs de um diretório como ZIP
        
        Compacta todos os arquivos XML do diretório especificado e retorna
        um arquivo ZIP para download.
        """
        args = download_processed_parser.parse_args()
        file_id = args['arquivo_id']

        logger.info("Solicitação de download para arquivo_id: %s", file_id)

        if not file_id:
            logger.warning("Parâmetro 'arquivo_id' ausente")
            return {"message": "'arquivo_id' é obrigatório!"}, 400

        response_message, status_code, zip_file_path = processed_service.download_all_xml_in_directory(
            file_id=file_id
        )

        if status_code != 200:
            logger.error("Erro no download: %s", response_message)
            return response_message, status_code

        logger.info("Download concluído: %s", zip_file_path)
        return send_file(zip_file_path, as_attachment=True)