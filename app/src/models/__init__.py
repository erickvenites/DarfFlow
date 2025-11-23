from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Importar os modelos para que o SQLAlchemy os reconheça
from src.models.database import (
    EventSpreadsheet,
    ConvertedSpreadsheet,
    SignedXmls,
    XmlsSent,
    ShippingResponse,
    FileStatus
)