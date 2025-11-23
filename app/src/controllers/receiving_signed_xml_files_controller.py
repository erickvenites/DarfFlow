import os
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from src.config.logging_config import logger
from src.utils.file_handler import allowed_file_zip
from src.utils.respond_error import respond_with_error
from src.service.ReceivingSignedXmlFilesService import ReceivingSignedXmlFilesService
from src.service.XmlSignatureService import XmlSignatureService
from src.middleware.auth import verify_token
from typing import Tuple, Dict

# Inicializa os serviços
signed_bp = Blueprint("signed_bp", __name__, url_prefix="/api/signed")
signed_service = ReceivingSignedXmlFilesService()
signature_service = XmlSignatureService()


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
    Faz o upload de um file ZIP contendo arquivos XMLs assinados.

    Args:
        None

    Returns:
        dict: Mensagem de erro ou sucesso.
        int: Código HTTP associado à resposta.
    """
    try:
        company_id = request.args.get("company_id").upper()
        event = request.args.get("event")
        spreadsheet_id = request.args.get("spreadsheet_id")  # ID da spreadsheet passada pelo front
        logger.info(
            "Recebendo zip com arquivos XMLs assinados da company_id: %s, Evento: %s",
            company_id,
            event,
        )

        # Validação dos parâmetros
        if not validate_parameters([company_id, event, spreadsheet_id]) or "file" not in request.files:
            logger.warning(
                "Parâmetros obrigatórios ausentes: company_id: %s, Evento: %s, Planilha ID: %s", company_id, event, spreadsheet_id
            )
            return respond_with_error("company_id, event, file e ID da spreadsheet são obrigatórios", 400)

        directory = request.files["file"]

        # Verificação se o file foi selecionado
        if directory.filename == "":
            logger.warning("Nenhum file foi selecionado")
            return respond_with_error("Nenhum file foi selecionado", 400)

        # Validação da extensão do file
        if not allowed_file_zip(directory.filename):
            logger.warning("Extensão do file não permitida: %s", directory.filename)
            return respond_with_error("Arquivo não permitido", 400)

        # Chamada ao serviço para salvar o file ZIP
        response, status_code = signed_service.save_signed_xml(
            company_id=company_id, event=event, year=str(datetime.now().year), zip_file=directory, spreadsheet_id=spreadsheet_id
        )

        return jsonify(response), status_code  # Retorna com o status_code adequado

    except Exception as e:
        logger.error("Erro inesperado ao salvar o diretório de arquivos assinados: %s", str(e))
        return respond_with_error("Ocorreu um erro ao receber os arquivos", 500)


@signed_bp.route("/list", methods=["GET"])
@verify_token
def get_all() -> Tuple[dict, int]:
    """
    Lista todos os arquivos assinados para uma combinação específica de OM, event e year.

    Args:
        None

    Returns:
        dict: Lista de arquivos assinados.
        int: Código HTTP associado à resposta.
    """
    try:
        company_id = request.args.get("company_id").upper()
        event = request.args.get("event")
        year = request.args.get("year")

        if not validate_parameters([company_id, event, year]):
            return respond_with_error("OM, event e year são obrigatórios", 400)

        # Chama o método de listagem de arquivos ZIP
        response, status_code = signed_service.list_all(company_id=company_id, event=event, year=year)  # Agora recebendo o status_code
        return jsonify(response), status_code  # Retorna com o status_code apropriado

    except Exception as e:
        logger.error("Erro ao listar diretórios: %s", str(e))
        return respond_with_error("Erro ao listar diretórios", 500)


@signed_bp.route("", methods=["GET"])
@verify_token
def get_by_id() -> Tuple[dict, int]:
    """
    Busca um file assinado pelo seu ID.

    Args:
        None

    Returns:
        dict: Detalhes do file signed.
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
        logger.error(f"Erro ao buscar file: {str(e)}")
        return jsonify({"message": "Erro interno do servidor."}), 500


@signed_bp.route('/send', methods=['POST'])
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
        company_id = request.args.get("company_id").upper()
        event = request.args.get("event")
        spreadsheet_id = request.args.get("spreadsheet_id")
        cnpj = request.args.get("cnpj")
        year = request.args.get("year")
        certificate_path = os.getenv("CERTIFICATE_PATH")

        if not certificate_path:
            logger.error("CERTIFICATE_PATH não configurado no ambiente")
            return jsonify({"message": "Erro de configuração: certificado não encontrado"}), 500

        response = signed_service.process_xml_and_save_response(
            spreadsheet_id=spreadsheet_id,
            cnpj=cnpj,
            company_id=company_id,
            event=event,
            year=year,
            certificate_path=certificate_path,
        )

        if response:
            return jsonify({"message": "Lote processado com sucesso", "response": response}), 200
        else:
            return jsonify({"message": "Falha ao processar o lote"}), 500

    except Exception as e:
        return jsonify({"message": "Erro no processamento do lote", "error": str(e)}), 500


@signed_bp.route("/sign", methods=["POST"])
@verify_token
def sign_xml_files() -> Tuple[dict, int]:
    """
    Assina os arquivos XMLs processados de uma spreadsheet sem necessidade de download.

    Esta rota busca os XMLs gerados a partir de uma spreadsheet processada,
    assina cada um deles digitalmente usando o certificado configurado,
    e salva os XMLs assinados.

    Query Parameters:
        spreadsheet_id (str): ID da spreadsheet que contém os XMLs a serem assinados
        event (str): Código do event (ex: '4020')
        certificate_password (str, optional): Senha do certificado (se não estiver no .env)

    Returns:
        Tuple[dict, int]: Resposta JSON com resultado da assinatura e código HTTP
    """
    try:
        from src.models.database import EventSpreadsheet, ConvertedSpreadsheet, FileStatus
        from src import db
        import glob

        # Validação dos parâmetros
        spreadsheet_id = request.args.get("spreadsheet_id")
        event = request.args.get("event")
        certificate_password = request.args.get("certificate_password")

        if not spreadsheet_id or not event:
            return respond_with_error(
                "Parâmetros 'spreadsheet_id' e 'event' são obrigatórios",
                400
            )

        logger.info(f"Iniciando assinatura de XMLs para spreadsheet {spreadsheet_id}")

        # Busca a spreadsheet
        spreadsheet = EventSpreadsheet.query.get(spreadsheet_id)
        if not spreadsheet:
            return respond_with_error("Planilha não encontrada", 404)

        # Verifica se a spreadsheet foi convertida
        if spreadsheet.status != FileStatus.CONVERTIDO:
            return respond_with_error(
                f"Planilha deve estar no status CONVERTIDO. Status atual: {spreadsheet.status.value}",
                400
            )

        # Busca os XMLs convertidos
        converted = ConvertedSpreadsheet.query.filter_by(spreadsheet_id=spreadsheet_id).first()
        if not converted:
            return respond_with_error("Nenhum XML convertido encontrado para esta spreadsheet", 404)

        # Busca todos os arquivos XML no diretório da spreadsheet convertida
        xml_dir = converted.path
        if not os.path.exists(xml_dir):
            return respond_with_error(f"Diretório de XMLs não encontrado: {xml_dir}", 404)

        xml_files = glob.glob(os.path.join(xml_dir, "*.xml"))
        if not xml_files:
            return respond_with_error("Nenhum file XML encontrado no diretório", 404)

        logger.info(f"Encontrados {len(xml_files)} file(s) XML para assinar")

        # Diretório para salvar XMLs assinados
        signed_dir = os.path.join(xml_dir, "assinados")
        os.makedirs(signed_dir, exist_ok=True)

        # Assina cada XML
        signed_count = 0
        errors = []

        for xml_file in xml_files:
            try:
                # Lê o conteúdo do XML
                with open(xml_file, 'r', encoding='utf-8') as f:
                    xml_content = f.read()

                # Assina o XML
                signed_xml = signature_service.sign_xml(
                    xml_content=xml_content,
                    event_type=event,
                    password=certificate_password
                )

                # Salva o XML assinado
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

        # Atualiza status da spreadsheet se todos os XMLs foram assinados
        if signed_count == len(xml_files):
            spreadsheet.status = FileStatus.ASSINADO
            db.session.commit()
            logger.info(f"Status da spreadsheet atualizado para ASSINADO")

        # Prepara resposta
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

        return jsonify(response), status_code

    except Exception as e:
        logger.error(f"Erro ao assinar XMLs: {str(e)}")
        return respond_with_error(f"Erro ao assinar XMLs: {str(e)}", 500)


@signed_bp.route("", methods=["DELETE"])
@verify_token
def delete_zip_file() -> Tuple[dict, int]:
    """
    Exclui um file ZIP de arquivos assinados com base no ID fornecido.

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
        logger.error("Erro ao deletar o file: %s", str(e))
        return respond_with_error("Erro ao deletar o file", 500)
