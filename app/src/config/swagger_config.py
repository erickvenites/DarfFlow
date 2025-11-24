"""
Configuração do Swagger/OpenAPI para documentação da API
"""
from flask_restx import Api, fields
from flask import Blueprint

# Blueprint para a documentação
api_bp = Blueprint('api', __name__)

# Configuração da API com Swagger
api = Api(
    api_bp,
    version='1.0.0',
    title='API de Gestão de Eventos eSocial',
    description='''
    API para gerenciamento de planilhas, processamento de XMLs e assinatura digital de documentos do eSocial.
    
    ## Autenticação
    A maioria dos endpoints requer autenticação via token JWT.
    Use o header: `Authorization: Bearer <seu_token>`
    
    ## Fluxo Principal
    1. **Upload de Planilha**: Envie uma planilha Excel/CSV com os dados
    2. **Processamento**: Converta a planilha em arquivos XML
    3. **Assinatura**: Assine digitalmente os XMLs gerados
    4. **Upload de Assinados**: Faça upload dos XMLs assinados
    5. **Envio**: Envie os eventos para o eSocial
    ''',
    doc='/docs',
    authorizations={
        'Bearer': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization',
            'description': 'Token JWT no formato: Bearer <token>'
        }
    },
    security='Bearer'
)

# Namespaces (agrupamento de endpoints)
ns_health = api.namespace('health', description='Monitoramento de saúde da aplicação')
ns_spreadsheets = api.namespace('spreadsheets', description='Operações com planilhas submetidas')
ns_processed = api.namespace('processed-files', description='Gestão de XMLs processados')
ns_signed = api.namespace('signed', description='Gestão de XMLs assinados')
ns_batches = api.namespace('batches', description='Gestão de lotes para envio ao REINF')

# ============= MODELOS DE DADOS =============

# Modelos de resposta para Health Check
health_check_model = api.model('HealthCheck', {
    'status': fields.String(description='Status geral da aplicação', example='healthy'),
    'checks': fields.Nested(api.model('HealthChecks', {
        'application': fields.String(description='Status da aplicação', example='ok'),
        'database': fields.String(description='Status do banco de dados', example='ok')
    }))
})

# Modelos para Planilhas
spreadsheet_model = api.model('Spreadsheet', {
    'id': fields.String(description='ID único da planilha', example='123e4567-e89b-12d3-a456-426614174000'),
    'company_id': fields.String(description='ID da empresa', example='OM001'),
    'event': fields.String(description='Código do evento eSocial', example='4020'),
    'filename': fields.String(description='Nome do arquivo', example='folha_pagamento_jan_2024.xlsx'),
    'file_type': fields.String(description='Tipo do arquivo', example='xlsx'),
    'status': fields.String(description='Status do processamento', example='CONVERTIDO', enum=['RECEBIDO', 'CONVERTIDO', 'ASSINADO', 'ENVIADO', 'ERRO']),
    'path': fields.String(description='Caminho do arquivo no servidor'),
    'received_date': fields.DateTime(description='Data de recebimento', example='2024-01-15T10:30:00')
})

upload_response_model = api.model('UploadResponse', {
    'message': fields.String(description='Mensagem de status', example='Planilha recebida com sucesso'),
    'spreadsheet_id': fields.String(description='ID da planilha', example='123e4567-e89b-12d3-a456-426614174000')
})

# Modelos para Arquivos Processados
processed_file_model = api.model('ProcessedFile', {
    'id': fields.String(description='ID do arquivo processado'),
    'company_id': fields.String(description='ID da empresa'),
    'event': fields.String(description='Código do evento'),
    'year': fields.String(description='Ano de referência'),
    'path': fields.String(description='Caminho do diretório'),
    'created_at': fields.DateTime(description='Data de criação'),
    'xml_count': fields.Integer(description='Quantidade de XMLs no diretório')
})

# Modelos para Arquivos Assinados
signed_file_model = api.model('SignedFile', {
    'id': fields.String(description='ID do arquivo assinado'),
    'company_id': fields.String(description='ID da empresa'),
    'event': fields.String(description='Código do evento'),
    'year': fields.String(description='Ano de referência'),
    'filename': fields.String(description='Nome do arquivo ZIP'),
    'path': fields.String(description='Caminho do arquivo'),
    'uploaded_at': fields.DateTime(description='Data de upload')
})

signature_response_model = api.model('SignatureResponse', {
    'message': fields.String(description='Mensagem de status'),
    'total_xmls': fields.Integer(description='Total de XMLs para assinar'),
    'signed_xmls': fields.Integer(description='XMLs assinados com sucesso'),
    'xmls_with_error': fields.Integer(description='XMLs com erro'),
    'signed_directory': fields.String(description='Diretório dos XMLs assinados'),
    'spreadsheet_status': fields.String(description='Status atualizado da planilha'),
    'erros': fields.List(fields.String, description='Lista de erros, se houver')
})

send_events_response_model = api.model('SendEventsResponse', {
    'message': fields.String(description='Mensagem de status'),
    'response': fields.Raw(description='Resposta do processamento')
})

# Modelo de erro genérico
error_model = api.model('Error', {
    'message': fields.String(description='Mensagem de erro', example='Parâmetro obrigatório ausente')
})

# ============= PARSERS (para documentar parâmetros) =============

# Parser para upload de planilha
upload_parser = api.parser()
upload_parser.add_argument('company_id', type=str, required=True, location='args', help='ID da empresa (OM)')
upload_parser.add_argument('cnpj', type=str, required=True, location='args', help='CNPJ da empresa (14 dígitos)')
upload_parser.add_argument('event', type=str, required=True, location='args', help='Código do evento eSocial (ex: 4020)')
upload_parser.add_argument('spreadsheet', type='file', required=True, location='files', help='Arquivo da planilha (Excel ou CSV)')

# Parser para download de planilha
download_spreadsheet_parser = api.parser()
download_spreadsheet_parser.add_argument('spreadsheet_id', type=str, required=True, location='args', help='ID da planilha')

# Parser para buscar planilhas
get_spreadsheets_parser = api.parser()
get_spreadsheets_parser.add_argument('spreadsheet_id', type=str, required=False, location='args', help='ID específico da planilha')
get_spreadsheets_parser.add_argument('company_id', type=str, required=False, location='args', help='ID da empresa')
get_spreadsheets_parser.add_argument('year', type=str, required=False, location='args', help='Ano de referência')
get_spreadsheets_parser.add_argument('event', type=str, required=False, location='args', help='Código do evento')

# Parser para deletar planilha
delete_spreadsheet_parser = api.parser()
delete_spreadsheet_parser.add_argument('spreadsheet_id', type=str, required=True, location='args', help='ID da planilha')

# Parser para processar planilha
process_spreadsheet_parser = api.parser()
process_spreadsheet_parser.add_argument('spreadsheet_id', type=str, required=True, location='args', help='ID da planilha')
process_spreadsheet_parser.add_argument('cnpj', type=str, required=True, location='args', help='CNPJ da empresa')

# Parser para listar arquivos processados
list_processed_parser = api.parser()
list_processed_parser.add_argument('company_id', type=str, required=False, location='args', help='ID da empresa (opcional)')
list_processed_parser.add_argument('year', type=str, required=False, location='args', help='Ano de referência (opcional)')
list_processed_parser.add_argument('event', type=str, required=False, location='args', help='Código do evento (opcional)')

# Parser para buscar/deletar por ID
file_id_parser = api.parser()
file_id_parser.add_argument('arquivo_id', type=str, required=True, location='args', help='ID do arquivo')

# Parser para download de processados
download_processed_parser = api.parser()
download_processed_parser.add_argument('arquivo_id', type=str, required=True, location='args', help='ID do arquivo processado')

# Parser para upload de XMLs assinados
upload_signed_parser = api.parser()
upload_signed_parser.add_argument('company_id', type=str, required=True, location='args', help='ID da empresa')
upload_signed_parser.add_argument('event', type=str, required=True, location='args', help='Código do evento')
upload_signed_parser.add_argument('spreadsheet_id', type=str, required=True, location='args', help='ID da planilha')
upload_signed_parser.add_argument('file', type='file', required=True, location='files', help='Arquivo ZIP com XMLs assinados')

# Parser para listar arquivos assinados
list_signed_parser = api.parser()
list_signed_parser.add_argument('company_id', type=str, required=False, location='args', help='ID da empresa (opcional)')
list_signed_parser.add_argument('event', type=str, required=False, location='args', help='Código do evento (opcional)')
list_signed_parser.add_argument('year', type=str, required=False, location='args', help='Ano de referência (opcional)')

# Parser para assinar XMLs
sign_xml_parser = api.parser()
sign_xml_parser.add_argument('spreadsheet_id', type=str, required=True, location='args', help='ID da planilha')
sign_xml_parser.add_argument('event', type=str, required=True, location='args', help='Código do evento')
sign_xml_parser.add_argument('certificate_password', type=str, required=False, location='args', help='Senha do certificado (opcional)')

# Parser para enviar eventos
send_events_parser = api.parser()
send_events_parser.add_argument('company_id', type=str, required=True, location='args', help='ID da empresa')
send_events_parser.add_argument('event', type=str, required=True, location='args', help='Código do evento')
send_events_parser.add_argument('spreadsheet_id', type=str, required=True, location='args', help='ID da planilha')
send_events_parser.add_argument('cnpj', type=str, required=True, location='args', help='CNPJ da empresa')
send_events_parser.add_argument('year', type=str, required=True, location='args', help='Ano de referência')
# ============= LOTES (BATCHES) =============

# Modelos para Lotes
batch_model = api.model('Batch', {
    'id': fields.String(description='ID do lote'),
    'spreadsheet_id': fields.String(description='ID da planilha'),
    'company_id': fields.String(description='ID da empresa'),
    'event': fields.String(description='Código do evento'),
    'status': fields.String(description='Status do lote', enum=['Criado', 'Enviado', 'Processando', 'Processado', 'Erro']),
    'protocol_number': fields.String(description='Número de protocolo do REINF'),
    'batch_xml_path': fields.String(description='Caminho do XML do lote'),
    'xml_count': fields.Integer(description='Quantidade de XMLs no lote'),
    'created_date': fields.DateTime(description='Data de criação'),
    'sent_date': fields.DateTime(description='Data de envio')
})

batch_create_response_model = api.model('BatchCreateResponse', {
    'message': fields.String(description='Mensagem de status'),
    'total_batches': fields.Integer(description='Total de lotes criados'),
    'batches': fields.List(fields.Nested(api.model('BatchCreated', {
        'batch_id': fields.String(description='ID do lote'),
        'xml_count': fields.Integer(description='Quantidade de XMLs'),
        'batch_xml_path': fields.String(description='Caminho do XML do lote')
    })))
})

batch_send_response_model = api.model('BatchSendResponse', {
    'message': fields.String(description='Mensagem de status'),
    'protocol_number': fields.String(description='Número de protocolo'),
    'batch_id': fields.String(description='ID do lote'),
    'status': fields.String(description='Status atualizado')
})

batch_query_response_model = api.model('BatchQueryResponse', {
    'batch_id': fields.String(description='ID do lote'),
    'protocol_number': fields.String(description='Número de protocolo'),
    'batch_status': fields.String(description='Status do lote'),
    'reinf_response': fields.Raw(description='Resposta do REINF')
})

# Parsers para Lotes
create_batch_parser = api.parser()
create_batch_parser.add_argument('converted_spreadsheet_id', type=str, required=True, location='args', help='ID da planilha convertida')

batch_id_parser = api.parser()
batch_id_parser.add_argument('batch_id', type=str, required=True, location='args', help='ID do lote')

list_batches_parser = api.parser()
list_batches_parser.add_argument('converted_spreadsheet_id', type=str, required=False, location='args', help='ID da planilha convertida')

send_batch_parser = api.parser()
send_batch_parser.add_argument('batch_id', type=str, required=True, location='args', help='ID do lote')
send_batch_parser.add_argument('environment', type=str, required=False, location='args', help='Ambiente (producao ou homologacao)', default='homologacao')
