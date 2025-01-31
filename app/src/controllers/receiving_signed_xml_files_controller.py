import os
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from src.config.logging_config import logger
from src.utils.file_handler import allowed_file_zip
from src.utils.respond_error import respond_with_error
from src.service.ReceivingSignedXmlFilesService import ReceivingSignedXmlFilesService
from src.middleware.auth import verify_token
from typing import Tuple, Dict

# Inicializa o serviço de arquivos XMLs assinados
signed_bp = Blueprint("signed_bp", __name__, url_prefix="/api/assinados")
signed_service = ReceivingSignedXmlFilesService()


def validate_parameters(params) -> bool:
    """
    Valida se todos os parâmetros estão presentes na requisição.

    Args:
        params (list): Lista de parâmetros a serem validados.

    Returns:
        bool: True se todos os parâmetros estiverem presentes, False caso contrário.
    """
    return all(params)


@signed_bp.route("/upload", methods=["POST"])
@verify_token
def upload_signed_xmls() -> Tuple[dict, int]:
    """
    Faz o upload de um arquivo ZIP contendo arquivos XMLs assinados.

    Args:
        None

    Returns:
        dict: Mensagem de erro ou sucesso.
        int: Código HTTP associado à resposta.
    """
    try:
        om = request.args.get("om").upper()
        event = request.args.get("evento")
        spreadsheet_id = request.args.get("planilha_id")  # ID da planilha passada pelo front
        logger.info(
            "Recebendo zip com arquivos XMLs assinados da OM: %s, Evento: %s",
            om,
            event,
        )

        # Validação dos parâmetros
        if not validate_parameters([om, event, spreadsheet_id]) or "arquivo" not in request.files:
            logger.warning(
                "Parâmetros obrigatórios ausentes: OM: %s, Evento: %s, Planilha ID: %s", om, event, spreadsheet_id
            )
            return respond_with_error("OM, evento, arquivo e ID da planilha são obrigatórios", 400)

        directory = request.files["arquivo"]

        # Verificação se o arquivo foi selecionado
        if directory.filename == "":
            logger.warning("Nenhum arquivo foi selecionado")
            return respond_with_error("Nenhum arquivo foi selecionado", 400)

        # Validação da extensão do arquivo
        if not allowed_file_zip(directory.filename):
            logger.warning("Extensão do arquivo não permitida: %s", directory.filename)
            return respond_with_error("Arquivo não permitido", 400)

        # Chamada ao serviço para salvar o arquivo ZIP
        response, status_code = signed_service.save_signed_xml(
            om=om, event=event, year=str(datetime.now().year), zip_file=directory, spreadsheet_id=spreadsheet_id
        )

        return jsonify(response), status_code  # Retorna com o status_code adequado

    except Exception as e:
        logger.error("Erro inesperado ao salvar o diretório de arquivos assinados: %s", str(e))
        return respond_with_error("Ocorreu um erro ao receber os arquivos", 500)


@signed_bp.route("/listar", methods=["GET"])
@verify_token
def get_all() -> Tuple[dict, int]:
    """
    Lista todos os arquivos assinados para uma combinação específica de OM, evento e ano.

    Args:
        None

    Returns:
        dict: Lista de arquivos assinados.
        int: Código HTTP associado à resposta.
    """
    try:
        om = request.args.get("om").upper()
        event = request.args.get("evento")
        year = request.args.get("ano")

        if not validate_parameters([om, event, year]):
            return respond_with_error("OM, evento e ano são obrigatórios", 400)

        # Chama o método de listagem de arquivos ZIP
        response, status_code = signed_service.list_all(om=om, event=event, year=year)  # Agora recebendo o status_code
        return jsonify(response), status_code  # Retorna com o status_code apropriado

    except Exception as e:
        logger.error("Erro ao listar diretórios: %s", str(e))
        return respond_with_error("Erro ao listar diretórios", 500)


@signed_bp.route("", methods=["GET"])
@verify_token
def get_by_id() -> Tuple[dict, int]:
    """
    Busca um arquivo assinado pelo seu ID.

    Args:
        None

    Returns:
        dict: Detalhes do arquivo assinado.
        int: Código HTTP associado à resposta.
    """
    file_id = request.args.get("arquivo_id")

    if not file_id:
        logger.warning("Parâmetro obrigatório ausente: arquivo_id")
        return jsonify({"message": "O parâmetro arquivo_id é obrigatório"}), 400
    
    try:
        # Chama o método list_by_id do serviço
        response, status_code = signed_service.list_by_id(file_id)

        if not response:
            logger.warning("Arquivo inexistente para o id: %s", file_id)
            return jsonify({"message": "Arquivo não encontrado"}), 404
        
        return jsonify(response), status_code
    except Exception as e:
        logger.error(f"Erro ao buscar arquivo: {str(e)}")
        return jsonify({"message": "Erro interno do servidor."}), 500


@signed_bp.route('/enviar', methods=['POST'])
@verify_token
def send_events_async() -> Tuple[dict, int]:
    """
    Processa e envia eventos assinados de forma assíncrona.

    Args:
        None

    Returns:
        dict: Mensagem de sucesso ou falha.
        int: Código HTTP associado à resposta.
    """
    try:
        # Outros parâmetros necessários para o processamento
        om = request.args.get("om").upper()
        event = request.args.get("evento")
        spreadsheet_id = request.args.get("planilha_id")
        cnpj = request.args.get("cnpj")
        year = request.args.get("ano")
        certificate_path = "docs/certificate2.pem"

        response = signed_service.process_xml_and_save_response(
            spreadsheet_id=spreadsheet_id,
            cnpj=cnpj,
            om=om,
            event=event,
            year=year,
            certificate_path=certificate_path,
        )

        if response:
            return jsonify({"mensagem": "Lote processado com sucesso", "resposta": response}), 200
        else:
            return jsonify({"mensagem": "Falha ao processar o lote"}), 500

    except Exception as e:
        return jsonify({"mensagem": "Erro no processamento do lote", "erro": str(e)}), 500


@signed_bp.route("", methods=["DELETE"])
@verify_token
def delete_zip_file() -> Tuple[dict, int]:
    """
    Exclui um arquivo ZIP de arquivos assinados com base no ID fornecido.

    Args:
        None

    Returns:
        dict: Mensagem de sucesso ou erro.
        int: Código HTTP associado à resposta.
    """
    try:
        file_id = request.args.get("arquivo_id")

        if not validate_parameters([file_id]):
            logger.warning("Parâmetro obrigatório ausente: arquivo_id")
            return respond_with_error("file_id é obrigatório", 400)

        response, status_code = signed_service.delete(file_id)
        return jsonify(response), status_code

    except Exception as e:
        logger.error("Erro ao deletar o arquivo: %s", str(e))
        return respond_with_error("Erro ao deletar o arquivo", 500)
