"""
Controller de Lotes com documentação Swagger
"""
from flask import request
from flask_restx import Resource
from src.service.BatchService import BatchService
from src.service.ReinfSendService import ReinfSendService
from src.config.logging_config import logger
from src.middleware.auth import verify_token
from src.config.swagger_config import (
    ns_batches,
    batch_model,
    batch_create_response_model,
    batch_send_response_model,
    batch_query_response_model,
    error_model,
    create_batch_parser,
    batch_id_parser,
    list_batches_parser,
    send_batch_parser
)

batch_service = BatchService()


@ns_batches.route('/create')
class BatchCreate(Resource):
    @ns_batches.doc('create_batches', security='Bearer')
    @ns_batches.expect(create_batch_parser)
    @ns_batches.response(201, 'Lotes criados com sucesso', batch_create_response_model)
    @ns_batches.response(400, 'Parâmetros inválidos', error_model)
    @ns_batches.response(404, 'Planilha não encontrada', error_model)
    @ns_batches.response(500, 'Erro interno', error_model)
    @verify_token
    def post(self):
        """
        Cria lotes a partir de XMLs assinados

        Agrupa os XMLs assinados de uma planilha convertida em lotes de até 50 arquivos.
        Gera o XML do lote no formato EFD-REINF para envio posterior.
        """
        try:
            args = create_batch_parser.parse_args()
            converted_spreadsheet_id = args['converted_spreadsheet_id']

            if not converted_spreadsheet_id:
                return {"message": "converted_spreadsheet_id é obrigatório"}, 400

            logger.info(f"Criando lotes para converted_spreadsheet_id: {converted_spreadsheet_id}")

            response, status_code = batch_service.create_batches_from_converted(converted_spreadsheet_id)
            return response, status_code

        except Exception as e:
            logger.error(f"Erro ao criar lotes: {str(e)}")
            return {"message": f"Erro ao criar lotes: {str(e)}"}, 500


@ns_batches.route('/list')
class BatchList(Resource):
    @ns_batches.doc('list_batches')
    @ns_batches.expect(list_batches_parser)
    @ns_batches.response(200, 'Lotes listados com sucesso', [batch_model])
    @ns_batches.response(500, 'Erro interno', error_model)
    def get(self):
        """
        Lista lotes de uma planilha convertida

        Retorna todos os lotes criados para uma planilha convertida específica.
        """
        try:
            args = list_batches_parser.parse_args()
            converted_spreadsheet_id = args.get('converted_spreadsheet_id')

            if not converted_spreadsheet_id:
                return {"message": "converted_spreadsheet_id é obrigatório"}, 400

            response, status_code = batch_service.list_batches_by_converted(converted_spreadsheet_id)
            return response, status_code

        except Exception as e:
            logger.error(f"Erro ao listar lotes: {str(e)}")
            return {"message": f"Erro ao listar lotes: {str(e)}"}, 500


@ns_batches.route('')
class BatchDetail(Resource):
    @ns_batches.doc('get_batch')
    @ns_batches.expect(batch_id_parser)
    @ns_batches.response(200, 'Lote encontrado', batch_model)
    @ns_batches.response(404, 'Lote não encontrado', error_model)
    @ns_batches.response(500, 'Erro interno', error_model)
    def get(self):
        """
        Busca um lote pelo ID

        Retorna os detalhes de um lote específico, incluindo a lista de XMLs.
        """
        try:
            args = batch_id_parser.parse_args()
            batch_id = args['batch_id']

            if not batch_id:
                return {"message": "batch_id é obrigatório"}, 400

            response, status_code = batch_service.get_batch_by_id(batch_id)
            return response, status_code

        except Exception as e:
            logger.error(f"Erro ao buscar lote: {str(e)}")
            return {"message": f"Erro ao buscar lote: {str(e)}"}, 500

    @ns_batches.doc('delete_batch', security='Bearer')
    @ns_batches.expect(batch_id_parser)
    @ns_batches.response(200, 'Lote deletado com sucesso')
    @ns_batches.response(400, 'Status inválido para deleção', error_model)
    @ns_batches.response(404, 'Lote não encontrado', error_model)
    @ns_batches.response(500, 'Erro ao deletar', error_model)
    @verify_token
    def delete(self):
        """
        Deleta um lote

        Remove um lote e desassocia os XMLs. Só permite deletar lotes com status CRIADO.
        """
        try:
            args = batch_id_parser.parse_args()
            batch_id = args['batch_id']

            if not batch_id:
                return {"message": "batch_id é obrigatório"}, 400

            response, status_code = batch_service.delete_batch(batch_id)
            return response, status_code

        except Exception as e:
            logger.error(f"Erro ao deletar lote: {str(e)}")
            return {"message": f"Erro ao deletar lote: {str(e)}"}, 500


@ns_batches.route('/send')
class BatchSend(Resource):
    @ns_batches.doc('send_batch', security='Bearer')
    @ns_batches.expect(send_batch_parser)
    @ns_batches.response(200, 'Lote enviado com sucesso', batch_send_response_model)
    @ns_batches.response(400, 'Parâmetros inválidos ou status incorreto', error_model)
    @ns_batches.response(404, 'Lote não encontrado', error_model)
    @ns_batches.response(422, 'Erro de validação no REINF', error_model)
    @ns_batches.response(500, 'Erro ao enviar', error_model)
    @verify_token
    def post(self):
        """
        Envia um lote para o EFD-REINF

        Envia o lote para a API REST do EFD-REINF usando certificado digital.
        Retorna o número de protocolo para consulta posterior.

        Ambientes disponíveis:
        - homologacao (padrão): https://pre-reinf.receita.economia.gov.br
        - producao: https://reinf.receita.economia.gov.br

        Requer certificado digital configurado em CERTIFICATE_PATH.
        """
        try:
            args = send_batch_parser.parse_args()
            batch_id = args['batch_id']
            environment = args.get('environment', 'homologacao')

            if not batch_id:
                return {"message": "batch_id é obrigatório"}, 400

            if environment not in ['producao', 'homologacao']:
                return {"message": "Ambiente deve ser 'producao' ou 'homologacao'"}, 400

            logger.info(f"Enviando lote {batch_id} para o REINF ({environment})")

            # Cria serviço de envio
            send_service = ReinfSendService(environment=environment)

            # Envia o lote
            response, status_code = send_service.send_batch(batch_id)
            return response, status_code

        except ValueError as e:
            logger.error(f"Erro de configuração: {str(e)}")
            return {"message": str(e)}, 500
        except FileNotFoundError as e:
            logger.error(f"Certificado não encontrado: {str(e)}")
            return {"message": str(e)}, 500
        except Exception as e:
            logger.error(f"Erro ao enviar lote: {str(e)}")
            return {"message": f"Erro ao enviar lote: {str(e)}"}, 500


@ns_batches.route('/query')
class BatchQuery(Resource):
    @ns_batches.doc('query_batch_status', security='Bearer')
    @ns_batches.expect(batch_id_parser)
    @ns_batches.response(200, 'Status consultado com sucesso', batch_query_response_model)
    @ns_batches.response(400, 'Lote sem protocolo', error_model)
    @ns_batches.response(404, 'Lote não encontrado', error_model)
    @ns_batches.response(500, 'Erro ao consultar', error_model)
    @verify_token
    def get(self):
        """
        Consulta o status de processamento de um lote

        Consulta o status de um lote no EFD-REINF usando o número de protocolo.
        Atualiza automaticamente o status do lote no banco de dados.

        O lote deve ter sido enviado previamente e possuir um número de protocolo.
        """
        try:
            args = batch_id_parser.parse_args()
            batch_id = args['batch_id']

            if not batch_id:
                return {"message": "batch_id é obrigatório"}, 400

            logger.info(f"Consultando status do lote {batch_id}")

            # Usa homologação por padrão para consultas
            # TODO: Armazenar o ambiente usado no envio no banco
            send_service = ReinfSendService(environment='homologacao')

            response, status_code = send_service.query_batch_status(batch_id)
            return response, status_code

        except Exception as e:
            logger.error(f"Erro ao consultar status: {str(e)}")
            return {"message": f"Erro ao consultar status: {str(e)}"}, 500
