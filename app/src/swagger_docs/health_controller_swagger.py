"""
Controller de Health Check com documentação Swagger
"""
from flask import jsonify
from flask_restx import Resource
from src.models import db
from src.config.logging_config import logger
from src.config.swagger_config import ns_health, health_check_model, error_model

@ns_health.route('/health')
class HealthCheck(Resource):
    @ns_health.doc('health_check')
    @ns_health.response(200, 'Aplicação saudável', health_check_model)
    @ns_health.response(503, 'Serviço indisponível', error_model)
    def get(self):
        """
        Verifica o status de saúde da aplicação
        
        Retorna o status da aplicação e da conexão com o banco de dados.
        Útil para monitoramento e health checks de infraestrutura.
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
            return health_status, 503

        return health_status, 200