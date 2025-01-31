from flask import Blueprint, render_template, request, jsonify, send_file
from src.service.SubmittedSpreadsheetsService import SubmittedSpreadsheetsService
from src.config.logging_config import logger
from src.utils.respond_error import respond_with_error
from src.models.database import EventSpreadsheet
from src import db
from src.middleware.auth import verify_token
from typing import List, Tuple, Optional

received_bp = Blueprint("received_bp", __name__, url_prefix='/api/planilhas')
received_service = SubmittedSpreadsheetsService()

def check_required_params(params: List[str]) -> bool:
    """
    Verifica se todos os parâmetros obrigatórios estão presentes na requisição.
    
    Args:
        params (List[str]): Lista de parâmetros obrigatórios.
    
    Returns:
        bool: True se todos os parâmetros estão presentes, caso contrário False.
    """
    for param in params:
        if not request.args.get(param):
            logger.warning("Parâmetro obrigatório ausente: %s", param)
            return False
    return True

@received_bp.route("/upload", methods=["POST"])
def upload_spreadsheet() -> Tuple[dict, int]:
    """
    Endpoint para realizar o upload de uma planilha.
    
    Valida os parâmetros necessários e processa o upload da planilha.
    
    Returns:
        Tuple[dict, int]: Resposta em formato JSON com a mensagem de status e o código de status HTTP.
    """
    try:
        om = request.args.get("om")
        event = request.args.get("evento")

        if not om or not event:
            return respond_with_error("OM e evento são obrigatórios", 400)

        if "planilha" not in request.files or request.files["planilha"].filename == "":
            return respond_with_error("Nenhuma planilha enviada ou selecionada", 400)

        file = request.files["planilha"]
        response_message, status_code = received_service.process_upload(file, om, event)

        return jsonify(response_message), status_code

    except Exception as e:
        logger.error("Erro ao processar o upload: %s", str(e))
        return respond_with_error("Ocorreu um erro ao processar o upload", 500)

@received_bp.route("/download", methods=["POST"])
@verify_token
def download_spreadsheet() -> Optional[send_file]:
    """
    Endpoint para realizar o download de uma planilha registrada.
    
    Valida o ID da planilha e retorna o arquivo solicitado.
    
    Returns:
        Optional[send_file]: Retorna o arquivo para download, ou resposta de erro.
    """
    try:
        spreadsheet_id = request.args.get("planilha_id")

        logger.info("Download solicitado para Planilha ID: %s", spreadsheet_id)

        if not spreadsheet_id:
            return respond_with_error("ID da planilha é obrigatório!", 400)

        response_message, status_code, file_path = received_service.download_file(spreadsheet_id)
        if status_code != 200:
            logger.error("Erro ao realizar download: %s", response_message)
            return jsonify(response_message), status_code

        logger.info("Download concluído com sucesso: %s", file_path)
        return send_file(file_path, as_attachment=True)

    except Exception as e:
        logger.error("Erro ao fazer o download: %s", str(e))
        return respond_with_error("Ocorreu um erro ao fazer o download", 500)

@received_bp.route("/", methods=["GET"])
@verify_token
def get_all_spreadsheets() -> Tuple[dict, int]:
    """
    Endpoint para buscar todas as planilhas cadastradas com base em parâmetros obrigatórios.
    
    Args:
        om (str): OM (Organização Militar) a ser consultada.
        year (str): Ano de referência.
        event (str): Evento relacionado.
    
    Returns:
        Tuple[dict, int]: Resposta com a lista das planilhas encontradas e o código de status HTTP.
    """
    om = request.args.get("om")
    year = request.args.get("ano")
    event = request.args.get("evento")

    if not om or not year or not event:
        logger.warning("Parâmetros obrigatórios ausentes: OM, ano e evento são necessários.")
        return respond_with_error("Os parâmetros 'om', 'ano' e 'evento' são obrigatórios.", 400)

    filters = [
        EventSpreadsheet.om == om.upper(),
        db.extract('year', EventSpreadsheet.data_recebimento) == int(year),
        EventSpreadsheet.evento == event
    ]

    try:
        spreadsheets = EventSpreadsheet.query.filter(*filters).all()

        spreadsheets_data = [
            {
                "id": str(spreadsheet.id),
                "om": spreadsheet.om,
                "evento": spreadsheet.evento,
                "nome_arquivo": spreadsheet.nome_arquivo,
                "tipo": spreadsheet.tipo,
                "status": spreadsheet.status.value,
                "caminho": spreadsheet.caminho,
                "data_recebimento": spreadsheet.data_recebimento.isoformat(),
            }
            for spreadsheet in spreadsheets
        ]

        return jsonify(spreadsheets_data), 200

    except Exception as e:
        logger.error(f"Erro ao buscar planilhas: {str(e)}")
        return respond_with_error("Erro interno do servidor.", 500)

@received_bp.route("/", methods=["GET"])
@verify_token
def get_by_id() -> Tuple[dict, int]:
    """
    Endpoint para buscar uma planilha específica pelo ID.
    
    Args:
        planilha_id (str): ID da planilha a ser consultada.
    
    Returns:
        Tuple[dict, int]: Resposta com os dados da planilha ou erro caso não encontrada.
    """
    spreadsheet_id = request.args.get("planilha_id")

    if not spreadsheet_id:
        return respond_with_error("O parâmetro planilha_id é obrigatório.", 400)

    try:
        response, status_code = received_service.get_spreadsheet_by_id(spreadsheet_id)

        return jsonify(response), status_code

    except Exception as e:
        logger.error(f"Erro ao buscar planilhas: {str(e)}")
        return respond_with_error("Erro interno do servidor.", 500)

@received_bp.route("/", methods=["DELETE"])
@verify_token
def delete_event() -> Tuple[dict, int]:
    """
    Endpoint para deletar uma planilha e o evento associado.
    
    Args:
        planilha_id (str): ID da planilha a ser deletada.
    
    Returns:
        Tuple[dict, int]: Resposta com a mensagem de sucesso ou erro ao tentar deletar.
    """
    try:
        spreadsheet_id = request.args.get("planilha_id")

        logger.info("Deletando planilha com id: %s", spreadsheet_id)

        if not spreadsheet_id:
            return respond_with_error("ID do evento é obrigatório!", 400)

        response_message, status_code = received_service.delete_event_and_associated_spreadsheet(spreadsheet_id)

        if status_code != 200:
            logger.error("Erro ao deletar evento: %s", response_message)

        logger.info("Evento deletado com sucesso para a planilha com ID: %s", spreadsheet_id)
        return jsonify(response_message), status_code

    except Exception as e:
        logger.error("Erro ao deletar evento: %s", str(e))
        return respond_with_error("Ocorreu um erro ao deletar o evento", 500)

@received_bp.route("/processar", methods=["POST"])
@verify_token
def handle_process_spreadsheet() -> Tuple[dict, int]:
    """
    Endpoint para processar uma planilha com base no ID e CNPJ fornecido.
    
    Args:
        planilha_id (str): ID da planilha a ser processada.
        cnpj (str): CNPJ associado à planilha.
    
    Returns:
        Tuple[dict, int]: Resposta com a mensagem de sucesso ou erro ao tentar processar a planilha.
    """
    try:
        spreadsheet_id = request.args.get("planilha_id")
        cnpj = request.args.get("cnpj")

        if not spreadsheet_id or not cnpj:
            return respond_with_error("ID da planilha e CNPJ são obrigatórios", 400)

        response_message, status_code = received_service.process_spreadsheet(spreadsheet_id=spreadsheet_id, cnpj=cnpj)
        return jsonify(response_message), status_code

    except Exception as e:
        logger.error("Erro ao processar a planilha: %s", str(e))
        return respond_with_error("Erro ao processar a planilha", 500)
