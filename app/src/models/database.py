import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import func, Enum, Index
import enum
from src.models import db

# Enum para status do file
class FileStatus(enum.Enum):
    RECEBIDO = 'Recebido'
    CONVERTIDO = 'Convertido'
    ASSINADO = 'Assinado'
    ENVIADO = 'Enviado'


class EventSpreadsheet(db.Model):
    __tablename__ = "tb_spreadsheets"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = db.Column(db.String(50), nullable=False)  # Company identifier (CNPJ, code, etc)
    event = db.Column(db.String(255), nullable=False)  # EFD-Reinf Event Code Ex.: 4020, 2010, etc
    filename = db.Column(db.String(255), nullable=False)  # Spreadsheet filename
    file_type = db.Column(db.String(255), nullable=False)  # File format (xlsx, xml)
    status = db.Column(db.Enum(FileStatus), nullable=False)  # Status enum
    path = db.Column(db.String(255), nullable=False)  # File path
    received_date = db.Column(db.DateTime, nullable=False, default=func.now())  # Timestamp
    #updated_at = db.Column(db.DateTime, nullable=False, default=func.now(), onupdate=func.now())  # For tracking changes

    # Relationship
    spreadsheets = db.relationship('ConvertedSpreadsheet', backref='file', lazy='dynamic')

    def to_dict(self):
        return{
            "id":self.id,
            "company_id": self.company_id,
            "event": self.event,
            "filename": self.filename,
            "file_type": self.file_type,
            "status": self.status.name,
            "path": self.path,
            "received_date": self.received_date,
        }


class ConvertedSpreadsheet(db.Model):
    __tablename__ = "tb_converted_spreadsheets"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    spreadsheet_id = db.Column(UUID(as_uuid=True), db.ForeignKey('tb_spreadsheets.id'), nullable=False)  # Reference to converted spreadsheet
    path = db.Column(db.String(255), nullable=False)
    total_generated_xmls = db.Column(db.Integer, nullable=False)
    converted_date = db.Column(db.DateTime, nullable=False, default=func.now())

    # Relationship
    signed_files = db.relationship('SignedXmls', backref="converted", lazy='dynamic')

    def to_dict(self):
            spreadsheet_base = {
                "spreadsheet_id": self.file.id,
                "company_id": self.file.company_id,
                "event": self.file.event,
            }
            return {
                **spreadsheet_base,
                "id": self.id,
                "path": self.path,
                "total_generated_xmls": self.total_generated_xmls,
                "converted_date": self.converted_date
            }


class SignedXmls(db.Model):
    __tablename__ = "tb_signed_xmls"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    converted_spreadsheet_id = db.Column(UUID(as_uuid=True), db.ForeignKey('tb_converted_spreadsheets.id'), nullable=False)  # Reference to converted XML
    path = db.Column(db.String(255), nullable=False)
    signed_date = db.Column(db.DateTime, nullable=False, default=func.now())

    # Relationship
    sent_files = db.relationship('XmlsSent', backref="signed", lazy='dynamic')

    def to_dict(self):
        spreadsheet_base = {
            "spreadsheet_id": self.converted.file.id,
            "company_id": self.converted.file.company_id,
            "event": self.converted.file.event,
        }
        return {
            **spreadsheet_base,
            "id": self.id,
            "path": self.path,
            "signed_date": self.signed_date
        }


class XmlsSent(db.Model):
    __tablename__ = "tb_sent_xmls"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    signed_xml_id = db.Column(UUID(as_uuid=True), db.ForeignKey('tb_signed_xmls.id'), nullable=False)  # Reference to signed XML
    path = db.Column(db.String(255), nullable=False)
    send_status = db.Column(db.String(255), nullable=False)
    send_protocol=db.Column(db.String(255),nullable=False)
    sent_date = db.Column(db.DateTime, nullable=False, default=func.now())

    # Relationship
    responses = db.relationship('ShippingResponse', backref="sent", lazy='dynamic')
    
    def to_dict(self):
            spreadsheet_base = {
                "spreadsheet_id": self.signed.converted.file.id,
                "company_id": self.signed.converted.file.company_id,
                "event": self.signed.converted.file.event,
                "status": self.signed.converted.file.status.name
            }
            return {
                **spreadsheet_base,
                "sent_id": self.id,
                "path": self.path,
                "send_status": self.send_status.name,
                "sent_date": self.sent_date
            }

class ShippingResponse(db.Model):
    __tablename__ = "tb_shipping_response"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sent_id = db.Column(UUID(as_uuid=True), db.ForeignKey('tb_sent_xmls.id'), nullable=False)  # Reference to sent XML
    path = db.Column(db.String(255), nullable=False)
    response_date = db.Column(db.DateTime, nullable=False, default=func.now())

    def to_dict(self):
        spreadsheet_base = {
            "spreadsheet_id": self.sent.signed.converted.file.id,
            "company_id": self.sent.signed.converted.file.company_id,
            "event": self.sent.signed.converted.file.event,
            "status": self.sent.signed.converted.file.status.name
        }
        return {
            **spreadsheet_base,
            "response_id": self.id,
            "path": self.path,
            "response_date": self.response_date
        }

# Index definitions
Index('ix_spreadsheet_id_converted', ConvertedSpreadsheet.spreadsheet_id)
Index('ix_converted_id_signed', SignedXmls.converted_spreadsheet_id)
Index('ix_signed_id_sent', XmlsSent.signed_xml_id)
Index('ix_sent_id_response', ShippingResponse.sent_id)
