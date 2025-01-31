import os
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from src.models import db
from src.config.config import DevelopmentConfig, ProductionConfig, TestingConfig

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Inicializa o aplicativo Flask
app = Flask(__name__)

# Configuração dinâmica baseada no ambiente
config_name = os.getenv('FLASK_ENV', 'development')  # 'development', 'production', ou 'testing'
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}

# Carrega configurações e banco de dados
app.config.from_object(config.get(config_name))
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DEV_DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1000 * 1000  # Limite de 16 MB para uploads

# Configuração do endpoint
app.config['ENDPOINT_URL'] = os.getenv('ENDPOINT_URL')

# Habilita o CORS
CORS(app)

# Inicializa o banco de dados
db.init_app(app)

# Registra os Blueprints
from src.controllers.submitted_spreadsheets_controller import received_bp
from src.controllers.processed_files_controller import processed_bp
from src.controllers.receiving_signed_xml_files_controller import signed_bp

app.register_blueprint(received_bp)
app.register_blueprint(processed_bp)
app.register_blueprint(signed_bp)
