import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import func, Enum, Index
import enum
from src import db

# Enum para status do arquivo
class FileStatus(enum.Enum):
    RECEBIDO = 'Recebido'
    CONVERTIDO = 'Convertido'
    ASSINADO = 'Assinado'
    ENVIADO = 'Enviado'


class EventSpreadsheet(db.Model):
    __tablename__ = "tb_planilhas"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    om = db.Column(db.String(50), nullable=False)  # Organização Militar Ex.: (DADM)
    evento = db.Column(db.String(255), nullable=False)  # Nome do Evento Ex.: 4020...
    nome_arquivo = db.Column(db.String(255), nullable=False)  # Nome da planilha
    tipo = db.Column(db.String(255), nullable=False)  # Formato do arquivo (xlsx, xml)
    status = db.Column(db.Enum(FileStatus), nullable=False)  # Enum para status
    caminho = db.Column(db.String(255), nullable=False)  # Caminho da planilha
    data_recebimento = db.Column(db.DateTime, nullable=False, default=func.now())  # timestamps
    #updated_at = db.Column(db.DateTime, nullable=False, default=func.now(), onupdate=func.now())  # Para rastrear alterações

    # Relacionamento
    planilhas = db.relationship('ConvertedSpreadsheet', backref='arquivo', lazy='dynamic')

    def to_dict(self):
        return{
            "id":self.id,
            "om": self.om,
            "evento": self.evento,
            "nome_arquivo": self.nome_arquivo,
            "tipo": self.tipo,
            "status": self.status.name,
            "caminho": self.caminho,
            "data_recebimento": self.data_recebimento,
        }


class ConvertedSpreadsheet(db.Model):
    __tablename__ = "tb_planilhas_convertidas"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    planilha_id = db.Column(UUID(as_uuid=True), db.ForeignKey('tb_planilhas.id'), nullable=False)  # Referência à planilha convertida
    caminho = db.Column(db.String(255), nullable=False)
    total_xmls_gerados = db.Column(db.Integer, nullable=False)
    data_conversao = db.Column(db.DateTime, nullable=False, default=func.now())
    
    # Relacionamento
    assinados = db.relationship('SignedXmls', backref='convertido', lazy='dynamic')

    def to_dict(self):
            planilha_base = {
                "planilha_id": self.arquivo.id,
                "om": self.arquivo.om,
                "evento": self.arquivo.evento,
            }
            return {
                **planilha_base,
                "id": self.id,
                "caminho": self.caminho,
                "total_xmls_gerados": self.total_xmls_gerados,
                "data_conversao": self.data_conversao
            }


class SignedXmls(db.Model):
    __tablename__ = "tb_xmls_assinados"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    planilha_convertida_id = db.Column(UUID(as_uuid=True), db.ForeignKey('tb_planilhas_convertidas.id'), nullable=False)  # Referência ao XML convertido
    caminho = db.Column(db.String(255), nullable=False)
    data_assinatura = db.Column(db.DateTime, nullable=False, default=func.now())

    # Relacionamento
    enviados = db.relationship('XmlsSent', backref='assinado', lazy='dynamic')

    def to_dict(self):
        planilha_base = {
            "planilha_id": self.convertido.arquivo.id,
            "om": self.convertido.arquivo.om,
            "evento": self.convertido.arquivo.evento,
        }
        return {
            **planilha_base,
            "id": self.id,
            "caminho": self.caminho,
            "data_assinatura": self.data_assinatura
        }


class XmlsSent(db.Model):
    __tablename__ = "tb_xmls_enviados"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_xml_assinado = db.Column(UUID(as_uuid=True), db.ForeignKey('tb_xmls_assinados.id'), nullable=False)  # Referência ao XML assinado
    caminho = db.Column(db.String(255), nullable=False)
    status_envio = db.Column(db.String(255), nullable=False)
    protocolo_envio=db.Column(db.String(255),nullable=False)
    data_envio = db.Column(db.DateTime, nullable=False, default=func.now())

    # Relacionamento
    respostas = db.relationship('ShippingResponse', backref='enviado', lazy='dynamic')
    
    def to_dict(self):
            planilha_base = {
                "planilha_id": self.assinado.convertido.arquivo.id,
                "om": self.assinado.convertido.arquivo.om,
                "evento": self.assinado.convertido.arquivo.evento,
                "status": self.assinado.convertido.arquivo.status.name
            }
            return {
                **planilha_base,
                "sent_id": self.id,
                "caminho": self.caminho,
                "status_envio": self.status_envio.name,
                "data_envio": self.data_envio
            }

class ShippingResponse(db.Model):
    __tablename__ = "tb_resposta_envio"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    enviado_id = db.Column(UUID(as_uuid=True), db.ForeignKey('tb_xmls_enviados.id'), nullable=False)  # Referência ao XML enviado
    caminho = db.Column(db.String(255), nullable=False)
    data_resposta = db.Column(db.DateTime, nullable=False, default=func.now())

    def to_dict(self):
        planilha_base = {
            "planilha_id": self.enviado.assinado.convertido.arquivo.id,
            "om": self.enviado.assinado.convertido.arquivo.om,
            "evento": self.enviado.assinado.convertido.arquivo.evento,
            "status": self.enviado.assinado.convertido.arquivo.status.name
        }
        return {
            **planilha_base,
            "response_id": self.id,
            "caminho": self.caminho,
            "data_resposta": self.data_resposta
        }

# Definição dos índices
Index('ix_planilha_id_convertida', ConvertedSpreadsheet.planilha_id)
Index('ix_convertido_id_assinado', SignedXmls.planilha_convertida_id)
Index('ix_assinado_id_enviado', XmlsSent.id_xml_assinado)
Index('ix_enviado_id_resposta', ShippingResponse.enviado_id)
