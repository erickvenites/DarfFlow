"""
Serviço de envio e consulta de lotes ao EFD-REINF.

Este módulo implementa a comunicação com a API REST do EFD-REINF
para envio de lotes e consulta de protocolos.
"""

import os
import requests
from typing import Tuple, Dict, Any
from datetime import datetime
from src import db
from src.models.database import Batch, BatchStatus
from src.config.logging_config import logger
from sqlalchemy.exc import SQLAlchemyError


class ReinfSendService:
    """
    Serviço para envio e consulta de lotes no EFD-REINF.

    Implementa comunicação com a API REST do REINF usando certificado digital.
    """

    # URLs da API REINF
    URLS = {
        "producao": {
            "envio": "https://reinf.receita.economia.gov.br/recepcao/lotes",
            "consulta": "https://reinf.receita.economia.gov.br/consulta/lotes/{protocolo}"
        },
        "homologacao": {
            "envio": "https://pre-reinf.receita.economia.gov.br/recepcao/lotes",
            "consulta": "https://pre-reinf.receita.economia.gov.br/consulta/lotes/{protocolo}"
        }
    }

    def __init__(self, environment: str = "homologacao"):
        """
        Inicializa o serviço.

        Args:
            environment: Ambiente (producao ou homologacao)
        """
        self.environment = environment
        self.certificate_path = os.getenv('CERTIFICATE_PATH')
        self.certificate_password = os.getenv('CERTIFICATE_PASSWORD', '')

        if not self.certificate_path:
            raise ValueError("CERTIFICATE_PATH não configurado no ambiente")

        if not os.path.exists(self.certificate_path):
            raise FileNotFoundError(f"Certificado não encontrado: {self.certificate_path}")

    def send_batch(self, batch_id: str) -> Tuple[Dict[str, Any], int]:
        """
        Envia um lote para o EFD-REINF.

        Args:
            batch_id: ID do lote a ser enviado

        Returns:
            Tupla com (resposta, código HTTP)
        """
        try:
            # Busca o lote
            batch = Batch.query.get(batch_id)
            if not batch:
                return {"message": "Lote não encontrado"}, 404

            # Verifica status
            if batch.status != BatchStatus.CRIADO:
                return {
                    "message": f"Lote deve estar no status CRIADO. Status atual: {batch.status.value}"
                }, 400

            # Verifica se o XML do lote existe
            if not batch.batch_xml_path or not os.path.exists(batch.batch_xml_path):
                return {"message": "Arquivo XML do lote não encontrado"}, 404

            # Lê o conteúdo do lote
            with open(batch.batch_xml_path, 'r', encoding='utf-8') as f:
                batch_xml = f.read()

            logger.info(f"Enviando lote {batch_id} para o REINF ({self.environment})")

            # URL de envio
            url = self.URLS[self.environment]["envio"]

            # Headers
            headers = {
                'Content-Type': 'application/xml; charset=utf-8'
            }

            # Faz a requisição com certificado digital
            # Para .pem, passa o arquivo diretamente
            # Para .pfx, precisa converter ou usar biblioteca específica
            if self.certificate_path.endswith('.pem'):
                cert = self.certificate_path
            else:
                # Se for .pfx, vai precisar de tratamento especial
                cert = (self.certificate_path, None)

            response = requests.post(
                url,
                data=batch_xml.encode('utf-8'),
                headers=headers,
                cert=cert,
                timeout=30,
                verify=True  # Verifica certificado SSL do servidor
            )

            logger.info(f"Resposta do REINF: Status {response.status_code}")
            logger.debug(f"Corpo da resposta: {response.text}")

            # Processa resposta
            if response.status_code == 200 or response.status_code == 201:
                # Sucesso - extrai número de protocolo da resposta
                # A resposta pode vir em XML ou JSON dependendo da API
                try:
                    response_data = response.json()
                    protocol_number = response_data.get('numeroProtocolo') or response_data.get('protocolo')
                except:
                    # Se não for JSON, pode ser XML
                    protocol_number = self._extract_protocol_from_xml(response.text)

                if protocol_number:
                    batch.protocol_number = protocol_number
                    batch.status = BatchStatus.ENVIADO
                    batch.sent_date = datetime.now()
                    db.session.commit()

                    logger.info(f"Lote {batch_id} enviado com sucesso. Protocolo: {protocol_number}")

                    return {
                        "message": "Lote enviado com sucesso",
                        "protocol_number": protocol_number,
                        "batch_id": str(batch_id),
                        "status": batch.status.value
                    }, 200
                else:
                    logger.warning(f"Protocolo não encontrado na resposta: {response.text}")
                    return {
                        "message": "Lote enviado mas protocolo não identificado",
                        "response": response.text
                    }, 200

            elif response.status_code == 422:
                # Erro de validação
                batch.status = BatchStatus.ERRO
                db.session.commit()

                return {
                    "message": "Erro de validação no lote",
                    "details": response.text,
                    "status_code": response.status_code
                }, 422

            else:
                # Outros erros
                batch.status = BatchStatus.ERRO
                db.session.commit()

                return {
                    "message": "Erro ao enviar lote",
                    "details": response.text,
                    "status_code": response.status_code
                }, response.status_code

        except requests.exceptions.SSLError as e:
            logger.error(f"Erro SSL ao enviar lote: {e}")
            return {"message": "Erro de certificado SSL", "details": str(e)}, 500

        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de conexão ao enviar lote: {e}")
            return {"message": "Erro de conexão com o REINF", "details": str(e)}, 500

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Erro ao atualizar lote: {e}")
            return {"message": "Erro ao atualizar status do lote"}, 500

        except Exception as e:
            logger.error(f"Erro inesperado ao enviar lote: {e}")
            return {"message": str(e)}, 500

    def query_batch_status(self, batch_id: str) -> Tuple[Dict[str, Any], int]:
        """
        Consulta o status de processamento de um lote pelo protocolo.

        Args:
            batch_id: ID do lote

        Returns:
            Tupla com (resposta, código HTTP)
        """
        try:
            # Busca o lote
            batch = Batch.query.get(batch_id)
            if not batch:
                return {"message": "Lote não encontrado"}, 404

            # Verifica se tem protocolo
            if not batch.protocol_number:
                return {"message": "Lote ainda não possui número de protocolo"}, 400

            logger.info(f"Consultando status do lote {batch_id}, protocolo: {batch.protocol_number}")

            # URL de consulta
            url = self.URLS[self.environment]["consulta"].format(protocolo=batch.protocol_number)

            # Headers
            headers = {
                'Accept': 'application/json'
            }

            # Certificado
            if self.certificate_path.endswith('.pem'):
                cert = self.certificate_path
            else:
                cert = (self.certificate_path, None)

            # Faz a requisição
            response = requests.get(
                url,
                headers=headers,
                cert=cert,
                timeout=30,
                verify=True
            )

            logger.info(f"Resposta da consulta: Status {response.status_code}")

            if response.status_code == 200:
                try:
                    result = response.json()

                    # Atualiza status do lote baseado na resposta
                    status_resposta = result.get('status') or result.get('situacao')

                    if status_resposta == 'PROCESSADO':
                        batch.status = BatchStatus.PROCESSADO
                        db.session.commit()
                    elif status_resposta == 'PROCESSANDO':
                        batch.status = BatchStatus.PROCESSANDO
                        db.session.commit()
                    elif status_resposta == 'ERRO':
                        batch.status = BatchStatus.ERRO
                        db.session.commit()

                    return {
                        "batch_id": str(batch_id),
                        "protocol_number": batch.protocol_number,
                        "batch_status": batch.status.value,
                        "reinf_response": result
                    }, 200

                except ValueError:
                    return {
                        "message": "Resposta do REINF não é JSON válido",
                        "response": response.text
                    }, 200

            else:
                return {
                    "message": "Erro ao consultar status",
                    "status_code": response.status_code,
                    "details": response.text
                }, response.status_code

        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao consultar status: {e}")
            return {"message": "Erro de conexão com o REINF", "details": str(e)}, 500

        except Exception as e:
            logger.error(f"Erro inesperado ao consultar status: {e}")
            return {"message": str(e)}, 500

    def _extract_protocol_from_xml(self, xml_response: str) -> str:
        """
        Extrai o número de protocolo de uma resposta XML.

        Args:
            xml_response: Resposta em XML

        Returns:
            Número de protocolo ou None
        """
        try:
            from lxml import etree

            root = etree.fromstring(xml_response.encode('utf-8'))

            # Tenta encontrar o protocolo em diferentes formatos
            # Procura por elementos comuns
            protocol_tags = ['numeroProtocolo', 'protocolo', 'nrProtocolo', 'protocoloEnvio']

            for tag in protocol_tags:
                # Busca sem namespace
                element = root.find(f".//{tag}")
                if element is not None and element.text:
                    return element.text

                # Busca com namespace
                for ns in root.nsmap.values():
                    if ns:
                        element = root.find(f".//{{{ns}}}{tag}")
                        if element is not None and element.text:
                            return element.text

            return None

        except Exception as e:
            logger.error(f"Erro ao extrair protocolo do XML: {e}")
            return None
