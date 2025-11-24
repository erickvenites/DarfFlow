"""
Serviço para gerenciamento de lotes de eventos EFD-REINF.

Este módulo implementa a criação, envio e consulta de lotes de eventos
seguindo o padrão exigido pela Receita Federal.
"""

import os
from typing import Tuple, Dict, Any, List
from datetime import datetime
from lxml import etree
from src import db
from src.models.database import Batch, SignedXmls, ConvertedSpreadsheet, BatchStatus, EventSpreadsheet
from src.config.logging_config import logger
from sqlalchemy.exc import SQLAlchemyError


class BatchService:
    """
    Serviço para gerenciamento de lotes EFD-REINF.

    Implementa operações de criação de lotes (agrupamento de até 50 XMLs),
    geração do XML do lote, e consulta de lotes.
    """

    MAX_XMLS_PER_BATCH = 50  # Limite do REINF

    def create_batches_from_converted(self, converted_spreadsheet_id: str) -> Tuple[Dict[str, Any], int]:
        """
        Cria lotes a partir de XMLs assinados de uma planilha convertida.

        Agrupa os XMLs assinados em lotes de até 50 arquivos cada.

        Args:
            converted_spreadsheet_id: ID da planilha convertida

        Returns:
            Tupla com (resposta, código HTTP)
        """
        try:
            # Busca a planilha convertida
            converted = ConvertedSpreadsheet.query.get(converted_spreadsheet_id)
            if not converted:
                return {"message": "Planilha convertida não encontrada"}, 404

            # Busca XMLs assinados que ainda não estão em lotes
            signed_xmls = SignedXmls.query.filter_by(
                converted_spreadsheet_id=converted_spreadsheet_id,
                batch_id=None
            ).all()

            if not signed_xmls:
                return {"message": "Nenhum XML assinado disponível para criar lotes"}, 404

            logger.info(f"Encontrados {len(signed_xmls)} XMLs assinados para criar lotes")

            # Agrupa em lotes de até 50
            batches_created = []
            for i in range(0, len(signed_xmls), self.MAX_XMLS_PER_BATCH):
                batch_xmls = signed_xmls[i:i + self.MAX_XMLS_PER_BATCH]

                # Cria o lote
                batch = Batch(
                    converted_spreadsheet_id=converted_spreadsheet_id,
                    status=BatchStatus.CRIADO
                )
                db.session.add(batch)
                db.session.flush()  # Garante que o ID do lote seja gerado

                # Associa XMLs ao lote
                for xml in batch_xmls:
                    xml.batch_id = batch.id

                # Gera o XML do lote
                batch_xml_content = self._generate_batch_xml(batch, batch_xmls, converted)

                # Salva o XML do lote no disco
                batch_dir = os.path.join(
                    os.path.dirname(converted.path),
                    "lotes"
                )
                os.makedirs(batch_dir, exist_ok=True)

                batch_filename = f"lote_{batch.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
                batch_xml_path = os.path.join(batch_dir, batch_filename)

                with open(batch_xml_path, 'w', encoding='utf-8') as f:
                    f.write(batch_xml_content)

                batch.batch_xml_path = batch_xml_path

                batches_created.append({
                    "batch_id": str(batch.id),
                    "xml_count": len(batch_xmls),
                    "batch_xml_path": batch_xml_path
                })

                logger.info(f"Lote {batch.id} criado com {len(batch_xmls)} XMLs")

            db.session.commit()

            return {
                "message": "Lotes criados com sucesso",
                "total_batches": len(batches_created),
                "batches": batches_created
            }, 201

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Erro ao criar lotes: {e}")
            return {"message": "Erro ao criar lotes no banco de dados"}, 500
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro inesperado ao criar lotes: {e}")
            return {"message": str(e)}, 500

    def _generate_batch_xml(self, batch: Batch, signed_xmls: List[SignedXmls], converted: ConvertedSpreadsheet) -> str:
        """
        Gera o XML do lote no formato EFD-REINF.

        Args:
            batch: Objeto do lote
            signed_xmls: Lista de XMLs assinados
            converted: Planilha convertida

        Returns:
            String com o conteúdo do XML do lote
        """
        # Namespace do envio de lote assíncrono
        ns = "http://www.reinf.esocial.gov.br/schemas/envioLoteEventosAssincrono/v1_00_00"

        # Cria elemento raiz
        root = etree.Element("{%s}Reinf" % ns, nsmap={None: ns})

        # Elemento envioLoteEventos
        envio_lote = etree.SubElement(root, "{%s}envioLoteEventos" % ns)

        # ideContribuinte
        ide_contrib = etree.SubElement(envio_lote, "{%s}ideContribuinte" % ns)

        # Extrai CNPJ da empresa (assumindo formato company_id)
        company_id = converted.file.company_id

        # tipo de inscrição: 1 = CNPJ, 2 = CPF
        tp_insc = etree.SubElement(ide_contrib, "{%s}tpInsc" % ns)
        tp_insc.text = "1"  # CNPJ

        nr_insc = etree.SubElement(ide_contrib, "{%s}nrInsc" % ns)
        # TODO: Aqui deveria buscar o CNPJ real da empresa
        # Por enquanto, usando placeholder
        nr_insc.text = "00000000000000"

        # eventos
        eventos = etree.SubElement(envio_lote, "{%s}eventos" % ns)

        # Adiciona cada XML assinado ao lote
        for signed_xml in signed_xmls:
            # Lê o conteúdo do XML assinado
            with open(signed_xml.path, 'r', encoding='utf-8') as f:
                signed_content = f.read()

            # Parse do XML assinado
            signed_root = etree.fromstring(signed_content.encode('utf-8'))

            # Cria elemento evento
            evento = etree.SubElement(eventos, "{%s}evento" % ns)
            evento.set("id", f"ID{os.path.basename(signed_xml.path).replace('.xml', '').replace('_signed', '')}")

            # Adiciona o XML assinado dentro do evento
            evento.append(signed_root)

        # Converte para string (minificado)
        batch_xml = etree.tostring(
            root,
            encoding='utf-8',
            xml_declaration=True,
            pretty_print=False
        ).decode('utf-8')

        return batch_xml

    def list_batches_by_converted(self, converted_spreadsheet_id: str) -> Tuple[Dict[str, Any], int]:
        """
        Lista todos os lotes de uma planilha convertida.

        Args:
            converted_spreadsheet_id: ID da planilha convertida

        Returns:
            Tupla com (resposta, código HTTP)
        """
        try:
            batches = Batch.query.filter_by(
                converted_spreadsheet_id=converted_spreadsheet_id
            ).order_by(Batch.created_date.desc()).all()

            if not batches:
                logger.info(f"Nenhum lote encontrado para converted_spreadsheet_id: {converted_spreadsheet_id}")
                return {"data": []}, 200

            result = {"data": [batch.to_dict() for batch in batches]}
            logger.info(f"Encontrados {len(batches)} lotes")
            return result, 200

        except SQLAlchemyError as e:
            logger.error(f"Erro ao listar lotes: {e}")
            return {"message": "Erro ao consultar banco de dados"}, 500

    def get_batch_by_id(self, batch_id: str) -> Tuple[Dict[str, Any], int]:
        """
        Busca um lote pelo ID.

        Args:
            batch_id: ID do lote

        Returns:
            Tupla com (resposta, código HTTP)
        """
        try:
            batch = Batch.query.get(batch_id)
            if not batch:
                return {"message": "Lote não encontrado"}, 404

            # Busca os XMLs do lote
            signed_xmls = SignedXmls.query.filter_by(batch_id=batch_id).all()

            batch_data = batch.to_dict()
            batch_data["xmls"] = [xml.to_dict() for xml in signed_xmls]

            return batch_data, 200

        except SQLAlchemyError as e:
            logger.error(f"Erro ao buscar lote: {e}")
            return {"message": "Erro ao consultar banco de dados"}, 500

    def delete_batch(self, batch_id: str) -> Tuple[Dict[str, Any], int]:
        """
        Deleta um lote e desassocia os XMLs.

        Args:
            batch_id: ID do lote

        Returns:
            Tupla com (resposta, código HTTP)
        """
        try:
            batch = Batch.query.get(batch_id)
            if not batch:
                return {"message": "Lote não encontrado"}, 404

            # Só permite deletar lotes que não foram enviados
            if batch.status != BatchStatus.CRIADO:
                return {"message": f"Não é possível deletar lote com status {batch.status.value}"}, 400

            # Desassocia XMLs do lote
            SignedXmls.query.filter_by(batch_id=batch_id).update({"batch_id": None})

            # Deleta arquivo XML do lote se existir
            if batch.batch_xml_path and os.path.exists(batch.batch_xml_path):
                os.remove(batch.batch_xml_path)

            # Deleta o lote
            db.session.delete(batch)
            db.session.commit()

            logger.info(f"Lote {batch_id} deletado com sucesso")
            return {"message": "Lote deletado com sucesso"}, 200

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Erro ao deletar lote: {e}")
            return {"message": "Erro ao deletar lote"}, 500
