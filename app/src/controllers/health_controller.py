from flask import Blueprint, jsonify
from src.models import db
from src.config.logging_config import logger
from typing import Tuple

health_bp = Blueprint("health_bp", __name__, url_prefix="/api")

@health_bp.route("/health", methods=["GET"])
def health_check() -> Tuple[dict, int]:
    """
    Endpoint de health check para monitoramento da aplicação.

    Verifica:
    - Status da aplicação
    - Conectividade com o banco de dados

    Returns:
        Tuple[dict, int]: Status de saúde da aplicação e código HTTP.
    """
    health_status = {
        "status": "healthy",
        "checks": {
            "application": "ok",
            "database": "unknown"
        }
    }

    # Verifica conectividade com o banco de dados
    try:
        db.session.execute(db.text("SELECT 1"))
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        logger.error(f"Health check falhou na verificação do banco de dados: {e}")
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = "error"
        return jsonify(health_status), 503

    return jsonify(health_status), 200
