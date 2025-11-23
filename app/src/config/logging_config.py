import os
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime

class LoggingConfig:
    """Configurações para o logging"""
    LOG_DIRECTORY = "logs"
    BACKUP_COUNT = 3

def setup_logging():
    # Cria o diretório 'logs' se não existir
    os.makedirs(LoggingConfig.LOG_DIRECTORY, exist_ok=True)

    # Define o formato do nome do file de log com data e hora
    current_time = datetime.now().strftime("%d-%m-%y-%Hh%Mm")
    log_filename = os.path.join(LoggingConfig.LOG_DIRECTORY, f"XML-log-{current_time}.log")

    # Configura o logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Cria um TimedRotatingFileHandler que cria um novo file de log diariamente
    handler = TimedRotatingFileHandler(
        log_filename,
        when="D",  # Roda a cada dia
        interval=1,  # Intervalo de 1 dia
        backupCount=LoggingConfig.BACKUP_COUNT,  # Mantém os últimos 3 arquivos de log
    )

    # Define o formato do log
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    # Adiciona o handler ao logger
    logger.addHandler(handler)

    # Adiciona um console handler para exibir os logs no console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

logger = setup_logging()
