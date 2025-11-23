import os
import sys
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from src.models import db
from src.config.config import DevelopmentConfig, ProductionConfig, TestingConfig

# Carregar variáveis de ambiente do file .env
load_dotenv()

def validate_required_env_vars():
    """
    Valida se todas as variáveis de ambiente obrigatórias estão configuradas.
    Encerra a aplicação se alguma variável estiver faltando.
    """
    required_vars = [
        'DEV_DATABASE_URL',
        'SECRET_KEY',
        'ENDPOINT_URL',
        'CERTIFICATE_PATH'
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"ERRO: Variáveis de ambiente obrigatórias não configuradas: {', '.join(missing_vars)}")
        print("Por favor, configure todas as variáveis no file .env antes de iniciar a aplicação.")
        sys.exit(1)

# Valida variáveis de ambiente obrigatórias
validate_required_env_vars()

# Inicializa o aplicativo Flask
app = Flask(__name__)

# Configuração dinâmica baseada no ambiente
config_name = os.getenv('FLASK_ENV', 'development')
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}

# Carrega configurações apropriadas para o ambiente
app.config.from_object(config.get(config_name))

# Configuração segura de CORS
allowed_origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000').split(',')

CORS(app, resources={
    r"/api/*": {
        "origins": allowed_origins,
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "max_age": 600
    }
})

# Inicializa o banco de dados
db.init_app(app)

# Importa e registra a configuração do Swagger
from src.config.swagger_config import api_bp

# Importa os controllers do Swagger (necessário para registrar os endpoints)
import src.swagger_docs.health_controller_swagger
import src.swagger_docs.submitted_spreadsheets_controller_swagger
import src.swagger_docs.processed_files_controller_swagger
import src.swagger_docs.receiving_signed_xml_files_controller_swagger

# Registra o blueprint do Swagger
app.register_blueprint(api_bp, url_prefix='/api')

# Registra os Blueprints originais (manter para compatibilidade)
from src.controllers.submitted_spreadsheets_controller import received_bp
from src.controllers.processed_files_controller import processed_bp
from src.controllers.receiving_signed_xml_files_controller import signed_bp
from src.controllers.health_controller import health_bp

app.register_blueprint(received_bp)
app.register_blueprint(processed_bp)
app.register_blueprint(signed_bp)
app.register_blueprint(health_bp)