"""
Serviço de assinatura digital de XMLs para EFD-Reinf.

Este módulo implementa a assinatura digital de arquivos XML seguindo o padrão
exigido pela Receita Federal para eventos do EFD-Reinf.
"""

import os
from lxml import etree
from signxml import XMLSigner, methods
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.backends import default_backend
from src.config.logging_config import logger
from typing import Tuple, Optional


class XmlSignatureService:
    """
    Serviço para assinatura digital de XMLs EFD-Reinf.

    Implementa assinatura conforme padrão XML-DSig exigido pela Receita Federal.
    """

    # Mapeamento de eventos para suas tags XML
    EVENT_TAGS = {
        '1000': 'evtInfoContri',
        '1070': 'evtTabProcesso',
        '2010': 'evtServTom',
        '2020': 'evtServPrest',
        '2030': 'evtAssocDespRec',
        '2040': 'evtAssocDespRecPJ',
        '2050': 'evtComProd',
        '2055': 'evtAquis',
        '2060': 'evtCPRB',
        '2098': 'evtReabreEvPer',
        '2099': 'evtFechaEvPer',
        '3010': 'evtEspDesportivo',
        '4010': 'evtInfoContriPF',
        '4020': 'evtRetPJ',
        '4040': 'evtBenefNId',
        '4080': 'evtInfoMV',
        '4099': 'evtFechaEvPer',
        '9000': 'evtExclusao',
        '9001': 'evtTotal',
        '9005': 'evtRetornoMensal',
        '9011': 'evtTotalDCTF',
        '9015': 'evtRetornoTotal'
    }

    def __init__(self):
        """Inicializa o serviço de assinatura."""
        self.certificate_path = os.getenv('CERTIFICATE_PATH')
        self.certificate_password = os.getenv('CERTIFICATE_PASSWORD', '')

    def load_certificate(self, certificate_path: Optional[str] = None,
                        password: Optional[str] = None) -> Tuple[bytes, bytes]:
        """
        Carrega o certificado digital e a chave privada.

        Args:
            certificate_path: Caminho do certificado (.pfx ou .pem)
            password: Senha do certificado

        Returns:
            Tupla contendo (chave_privada, certificado)

        Raises:
            FileNotFoundError: Se o certificado não for encontrado
            ValueError: Se o formato do certificado for inválido
        """
        cert_path = certificate_path or self.certificate_path
        cert_password = password or self.certificate_password

        if not cert_path or not os.path.exists(cert_path):
            raise FileNotFoundError(f"Certificado não encontrado: {cert_path}")

        try:
            # Se for file .pfx (PKCS#12)
            if cert_path.endswith('.pfx') or cert_path.endswith('.p12'):
                with open(cert_path, 'rb') as f:
                    pfx_data = f.read()

                private_key, certificate, _ = pkcs12.load_key_and_certificates(
                    pfx_data,
                    cert_password.encode() if cert_password else None,
                    backend=default_backend()
                )

                # Serializa chave privada para PEM
                key_pem = private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )

                # Serializa certificado para PEM
                cert_pem = certificate.public_bytes(serialization.Encoding.PEM)

                return key_pem, cert_pem

            # Se for file .pem
            elif cert_path.endswith('.pem'):
                with open(cert_path, 'rb') as f:
                    pem_data = f.read()

                # Assume que o file PEM contém tanto chave quanto certificado
                return pem_data, pem_data

            else:
                raise ValueError(f"Formato de certificado não suportado: {cert_path}")

        except Exception as e:
            logger.error(f"Erro ao carregar certificado: {e}")
            raise

    def detect_event_type(self, xml_content: str) -> Optional[str]:
        """
        Detecta o tipo de event no XML.

        Args:
            xml_content: Conteúdo XML como string

        Returns:
            Código do event (ex: '4020') ou None se não detectado
        """
        try:
            root = etree.fromstring(xml_content.encode('utf-8'))

            # Procura por tags de event conhecidas
            for event_code, event_tag in self.EVENT_TAGS.items():
                if root.find(f".//{event_tag}") is not None:
                    return event_code

            logger.warning("Tipo de event não detectado no XML")
            return None

        except Exception as e:
            logger.error(f"Erro ao detectar tipo de event: {e}")
            return None

    def sign_xml(self, xml_content: str, event_type: Optional[str] = None,
                 certificate_path: Optional[str] = None,
                 password: Optional[str] = None) -> str:
        """
        Assina um XML seguindo o padrão EFD-Reinf.

        Args:
            xml_content: Conteúdo XML a ser assinado
            event_type: Código do event (ex: '4020'). Se None, tenta detectar.
            certificate_path: Caminho do certificado (usa env var se None)
            password: Senha do certificado (usa env var se None)

        Returns:
            XML assinado como string

        Raises:
            ValueError: Se o event não for detectado ou for inválido
            Exception: Erros durante o processo de assinatura
        """
        try:
            # Detecta tipo de event se não fornecido
            if not event_type:
                event_type = self.detect_event_type(xml_content)
                if not event_type:
                    raise ValueError("Não foi possível detectar o tipo de event no XML")

            # Valida tipo de event
            if event_type not in self.EVENT_TAGS:
                raise ValueError(f"Tipo de event inválido: {event_type}")

            event_tag = self.EVENT_TAGS[event_type]
            logger.info(f"Assinando XML do event {event_type} ({event_tag})")

            # Carrega certificado e chave privada
            private_key_pem, cert_pem = self.load_certificate(certificate_path, password)

            # Parse do XML
            root = etree.fromstring(xml_content.encode('utf-8'))

            # Extrai o namespace real do XML
            # O namespace está no elemento raiz <Reinf>
            namespace = root.nsmap.get(None)  # None = default namespace

            # Tenta encontrar o elemento do event
            # Se houver namespace, usa busca com namespace
            if namespace:
                # Busca com namespace
                event_element = root.find(f".//{{{namespace}}}{event_tag}")
                logger.info(f"Buscando elemento {event_tag} com namespace: {namespace}")
            else:
                # Busca sem namespace (fallback)
                event_element = root.find(f".//{event_tag}")
                logger.info(f"Buscando elemento {event_tag} sem namespace")

            if event_element is None:
                raise ValueError(f"Elemento {event_tag} não encontrado no XML")

            # Garante que o elemento tenha um ID para referência
            if 'Id' not in event_element.attrib and 'id' not in event_element.attrib:
                # Gera ID baseado no tipo de event
                event_id = f"ID{event_type}{os.urandom(8).hex()}"
                event_element.set('Id', event_id)

            # Configura o assinador
            signer = XMLSigner(
                method=methods.enveloped,
                signature_algorithm="rsa-sha256",
                digest_algorithm="sha256",
                c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
            )

            # Assina o elemento do event
            signed_root = signer.sign(
                root,
                key=private_key_pem,
                cert=cert_pem,
                reference_uri=f"#{event_element.get('Id') or event_element.get('id')}"
            )

            # Converte para string com declaração XML (minificado)
            # pretty_print=False para evitar alterações no arquivo após assinatura
            signed_xml_bytes = etree.tostring(
                signed_root,
                encoding='utf-8',
                xml_declaration=True,
                pretty_print=False
            )

            # Decodifica bytes para string
            signed_xml = signed_xml_bytes.decode('utf-8')

            logger.info(f"XML do event {event_type} assinado com sucesso")
            return signed_xml

        except Exception as e:
            logger.error(f"Erro ao assinar XML: {e}")
            raise

    def verify_signature(self, signed_xml: str) -> bool:
        """
        Verifica se um XML está corretamente signed.

        Args:
            signed_xml: XML assinado como string

        Returns:
            True se a assinatura for válida, False caso contrário
        """
        try:
            from signxml import XMLVerifier

            root = etree.fromstring(signed_xml.encode('utf-8'))

            # Verifica se há assinatura
            signature = root.find(".//{http://www.w3.org/2000/09/xmldsig#}Signature")
            if signature is None:
                logger.warning("Nenhuma assinatura encontrada no XML")
                return False

            verifier = XMLVerifier()
            verified_data = verifier.verify(root)

            logger.info("Assinatura XML verificada com sucesso")
            return True

        except Exception as e:
            logger.error(f"Erro ao verificar assinatura: {e}")
            return False
