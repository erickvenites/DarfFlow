from flask import jsonify
from src.config.logging_config import logger

def respond_with_error(message, status_code):
    """Retorna uma resposta JSON de erro.""" 
    logger.error(message)
    return jsonify({"message": message}), status_code