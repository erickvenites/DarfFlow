from flask import Blueprint, render_template, request, jsonify, send_file
from src.service.SubmittedSpreadsheetsService import SubmittedSpreadsheetsService
from src.config.logging_config import logger
from src.utils.respond_error import respond_with_error
from src.models.database import EventSpreadsheet
from src import db
from src.middleware.auth import verify_token
from typing import List, Tuple, Optional

received_bp = Blueprint("received_bp", __name__, url_prefix='/api/spreadsheets')
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
    Endpoint para realizar o upload de uma spreadsheet.
    
    Valida os parâmetros necessários e processa o upload da spreadsheet.
    
    Returns:
        Tuple[dict, int]: Resposta em formato JSON com a message de status e o código de status HTTP.
    """
    try:
        company_id = request.args.get("company_id")
        event = request.args.get("event")

        if not company_id or not event:
            return respond_with_error("company_id e event são obrigatórios", 400)

        if "spreadsheet" not in request.files or request.files["spreadsheet"].filename == "":
            return respond_with_error("Nenhuma spreadsheet enviada ou selecionada", 400)

        file = request.files["spreadsheet"]
        response_message, status_code = received_service.process_upload(file, company_id, event)

        return jsonify(response_message), status_code

    except Exception as e:
        logger.error("Erro ao processar o upload: %s", str(e))
        return respond_with_error("Ocorreu um erro ao processar o upload", 500)

@received_bp.route("/download", methods=["POST"])
@verify_token
def download_spreadsheet() -> Optional[send_file]:
    """
    Endpoint para realizar o download de uma spreadsheet registrada.
    
    Valida o ID da spreadsheet e retorna o file solicitado.
    
    Returns:
        Optional[send_file]: Retorna o file para download, ou resposta de erro.
    """
    try:
        spreadsheet_id = request.args.get("spreadsheet_id")

        logger.info("Download solicitado para Planilha ID: %s", spreadsheet_id)

        if not spreadsheet_id:
            return respond_with_error("ID da spreadsheet é obrigatório!", 400)

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
def get_spreadsheets() -> Tuple[dict, int]:
    """
    Endpoint para buscar planilhas.

    Comportamento:
    - Se spreadsheet_id for fornecido: retorna uma spreadsheet específica
    - Se company_id, year e event forem fornecidos: retorna todas as planilhas que correspondem aos filtros

    Args:
        spreadsheet_id (str, optional): ID da spreadsheet a ser consultada.
        company_id (str, optional): Identificador da empresa a ser consultada.
        year (str, optional): Ano de referência.
        event (str, optional): Evento relacionado.

    Returns:
        Tuple[dict, int]: Resposta com os dados da(s) spreadsheet(s) ou erro.
    """
    spreadsheet_id = request.args.get("spreadsheet_id")

    # Se spreadsheet_id for fornecido, busca spreadsheet específica
    if spreadsheet_id:
        try:
            response, status_code = received_service.get_spreadsheet_by_id(spreadsheet_id)
            return jsonify(response), status_code
        except Exception as e:
            logger.error(f"Erro ao buscar spreadsheet por ID: {str(e)}")
            return respond_with_error("Erro interno do servidor.", 500)

    # Caso contrário, busca todas as planilhas com base nos filtros
    company_id = request.args.get("company_id")
    year = request.args.get("year")
    event = request.args.get("event")

    if not company_id or not year or not event:
        logger.warning("Parâmetros obrigatórios ausentes para busca geral.")
        return respond_with_error(
            "Forneça 'spreadsheet_id' para buscar uma spreadsheet específica, ou 'company_id', 'year' e 'event' para buscar múltiplas planilhas.",
            400
        )

    filters = [
        EventSpreadsheet.company_id == company_id.upper(),
        db.extract('year', EventSpreadsheet.received_date) == int(year),
        EventSpreadsheet.event == event
    ]

    try:
        spreadsheets = EventSpreadsheet.query.filter(*filters).all()

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

        return jsonify(spreadsheets_data), 200

    except Exception as e:
        logger.error(f"Erro ao buscar planilhas: {str(e)}")
        return respond_with_error("Erro interno do servidor.", 500)

@received_bp.route("/", methods=["DELETE"])
@verify_token
def delete_event() -> Tuple[dict, int]:
    """
    Endpoint para deletar uma spreadsheet e o event associado.
    
    Args:
        spreadsheet_id (str): ID da spreadsheet a ser deletada.
    
    Returns:
        Tuple[dict, int]: Resposta com a message de sucesso ou erro ao tentar deletar.
    """
    try:
        spreadsheet_id = request.args.get("spreadsheet_id")

        logger.info("Deletando spreadsheet com id: %s", spreadsheet_id)

        if not spreadsheet_id:
            return respond_with_error("ID do event é obrigatório!", 400)

        response_message, status_code = received_service.delete_event_and_associated_spreadsheet(spreadsheet_id)

        if status_code != 200:
            logger.error("Erro ao deletar event: %s", response_message)

        logger.info("Evento deletado com sucesso para a spreadsheet com ID: %s", spreadsheet_id)
        return jsonify(response_message), status_code

    except Exception as e:
        logger.error("Erro ao deletar event: %s", str(e))
        return respond_with_error("Ocorreu um erro ao deletar o event", 500)

@received_bp.route("/process", methods=["POST"])
@verify_token
def handle_process_spreadsheet() -> Tuple[dict, int]:
    """
    Endpoint para processar uma spreadsheet com base no ID e CNPJ fornecido.
    
    Args:
        spreadsheet_id (str): ID da spreadsheet a ser processada.
        cnpj (str): CNPJ associado à spreadsheet.
    
    Returns:
        Tuple[dict, int]: Resposta com a message de sucesso ou erro ao tentar processar a spreadsheet.
    """
    try:
        spreadsheet_id = request.args.get("spreadsheet_id")
        cnpj = request.args.get("cnpj")

        if not spreadsheet_id or not cnpj:
            return respond_with_error("ID da spreadsheet e CNPJ são obrigatórios", 400)

        response_message, status_code = received_service.process_spreadsheet(spreadsheet_id=spreadsheet_id, cnpj=cnpj)
        return jsonify(response_message), status_code

    except Exception as e:
        logger.error("Erro ao processar a spreadsheet: %s", str(e))
        return respond_with_error("Erro ao processar a spreadsheet", 500)
