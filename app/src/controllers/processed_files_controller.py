from flask import Blueprint, render_template, request, jsonify, send_file
from src.service.ProcessedFilesService import ProcessedFilesService
from src.config.logging_config import logger
from src.utils.respond_error import respond_with_error
from src.middleware.auth import verify_token
from typing import Tuple

# Instancia o serviço de arquivos processados
processed_service = ProcessedFilesService()

# Define o blueprint com prefixo de URL para os endpoints de arquivos processados
processed_bp = Blueprint("processed_bp", __name__, url_prefix='/api/arquivos-processados')


@processed_bp.route("/download", methods=["POST"])
@verify_token
def download() -> Tuple[dict, int]:
    """
    Permite o download de todos os arquivos XML de um diretório específico, 
    com base no ID do arquivo enviado na requisição.

    Args:
        None

    Returns:
        dict: Mensagem de erro ou sucesso.
        int: Código HTTP associado à resposta.
    """
    file_id = request.args.get("arquivo_id")  # Captura o arquivo_id

    logger.info("Solicitação de download para arquivo_id: %s", file_id)

    if not file_id:
        logger.warning("Parâmetro 'arquivo_id' ausente")
        return respond_with_error("'arquivo_id' é obrigatório!", 400)

    # Chama o serviço para download com base no arquivo_id
    response_message, status_code, zip_file_path = processed_service.download_all_xml_in_directory(
        file_id=file_id
    )

    if status_code != 200:
        logger.error("Erro no download: %s", response_message)
        return jsonify(response_message), status_code

    logger.info("Download concluído: %s", zip_file_path)
    return send_file(zip_file_path, as_attachment=True)


@processed_bp.route("/listar", methods=["GET"])
@verify_token
def list_all() -> Tuple[dict, int]:
    """
    Lista os diretórios disponíveis para uma combinação específica de OM, ano e evento.

    Args:
        None

    Returns:
        dict: Lista de diretórios disponíveis.
        int: Código HTTP associado à resposta.
    """
    om = request.args.get("om").upper()
    year = request.args.get("ano")
    event = request.args.get("evento")

    if not om or not year or not event:
        logger.warning(
            "Parâmetros obrigatórios ausentes: OM: %s, Ano: %s, Evento: %s",
            om,
            year,
            event,
        )
        return respond_with_error("OM, ano e evento são obrigatórios", 400)

    response, status_code = processed_service.list_all(
        om=om, year=year, event=event
    )

    logger.info(
        "Diretórios listados: OM: %s, Ano: %s, Código do Evento: %s, Resposta: %s",
        om,
        year,
        event,
        response,
    )
    return jsonify(response), status_code


@processed_bp.route("", methods=["GET"])
@verify_token
def list_by_id() -> Tuple[dict, int]:
    """
    Busca um arquivo processado específico pelo ID.

    Args:
        None

    Returns:
        dict: Detalhes do arquivo processado.
        int: Código HTTP associado à resposta.
    """
    file_id = request.args.get("arquivo_id")

    if not file_id:
        logger.warning("Parâmetro obrigatório ausente: arquivo_id")
        return jsonify({"message": "O parâmetro arquivo_id é obrigatório"}), 400
    
    try:
        # Chama o método get_by_id do processed_service
        response, status_code = processed_service.get_by_id(file_id)

        if not response:
            logger.warning("Arquivo inexistente para o id: %s", file_id)
            return jsonify({"message": "Arquivo não encontrado"}), 404
        
        return jsonify(response), status_code
    except Exception as e:
        logger.error(f"Erro ao buscar arquivo: {str(e)}")
        return jsonify({"message": "Erro interno do servidor."}), 500


@processed_bp.route("", methods=["DELETE"])
@verify_token
def delete() -> Tuple[dict, int]:
    """
    Exclui um diretório de XMLs processados com base no ID do diretório.

    Args:
        None

    Returns:
        dict: Mensagem de sucesso ou erro.
        int: Código HTTP associado à resposta.
    """
    directory_id = request.args.get("arquivo_id")  # Captura o arquivo_id

    if not directory_id:
        logger.warning("Parâmetro 'arquivo_id' ausente")
        return respond_with_error("'arquivo_id' é obrigatório!", 400)

    logger.info("Solicitação de exclusão para arquivo_id: %s", directory_id)

    # Chama o serviço para deletar com base no arquivo_id
    response, status_code = processed_service.delete_directory(directory_id=directory_id)

    if status_code != 200:
        logger.error("Erro ao deletar diretório: %s", response)

    logger.info("Diretório deletado: arquivo_id: %s, Resposta: %s", directory_id, response)
    return jsonify(response), status_code
