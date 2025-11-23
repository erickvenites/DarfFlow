import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configurações base para todos os ambientes"""
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1000 * 1000  # Limite de 16 MB para uploads
    ENDPOINT_URL = os.getenv('ENDPOINT_URL')

class DevelopmentConfig(Config):
    """Configurações específicas para desenvolvimento"""
    SQLALCHEMY_DATABASE_URI = os.getenv('DEV_DATABASE_URL')
    DEBUG = True

class ProductionConfig(Config):
    """Configurações para o ambiente de produção"""
    SQLALCHEMY_DATABASE_URI = os.getenv('PROD_DATABASE_URL')
    DEBUG = False

class TestingConfig(Config):
    """Configurações para o ambiente de testes"""
    SQLALCHEMY_DATABASE_URI = os.getenv('TEST_DATABASE_URL')
    TESTING = True
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}
