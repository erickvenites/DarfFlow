"""Complete PT to EN translation - tables and columns

Revision ID: c4d9e8f32b56
Revises: b3f8c9d21a45
Create Date: 2025-01-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4d9e8f32b56'
down_revision = 'b3f8c9d21a45'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Traduz completamente o banco de dados de PT para EN:
    - Renomeia tabelas
    - Renomeia colunas
    - Atualiza foreign keys e índices
    """

    # 1. Renomear tabelas
    op.rename_table('tb_planilhas', 'tb_spreadsheets')
    op.rename_table('tb_planilhas_convertidas', 'tb_converted_spreadsheets')
    op.rename_table('tb_xmls_assinados', 'tb_signed_xmls')
    op.rename_table('tb_xmls_enviados', 'tb_sent_xmls')
    op.rename_table('tb_resposta_envio', 'tb_shipping_response')

    # 2. Renomear colunas em tb_spreadsheets (antiga tb_planilhas)
    op.alter_column('tb_spreadsheets', 'empresa_id',
                    new_column_name='company_id',
                    existing_type=sa.String(length=50),
                    existing_nullable=False)

    op.alter_column('tb_spreadsheets', 'evento',
                    new_column_name='event',
                    existing_type=sa.String(length=255),
                    existing_nullable=False)

    op.alter_column('tb_spreadsheets', 'nome_arquivo',
                    new_column_name='filename',
                    existing_type=sa.String(length=255),
                    existing_nullable=False)

    op.alter_column('tb_spreadsheets', 'tipo',
                    new_column_name='file_type',
                    existing_type=sa.String(length=255),
                    existing_nullable=False)

    op.alter_column('tb_spreadsheets', 'caminho',
                    new_column_name='path',
                    existing_type=sa.String(length=255),
                    existing_nullable=False)

    op.alter_column('tb_spreadsheets', 'data_recebimento',
                    new_column_name='received_date',
                    existing_type=sa.DateTime(),
                    existing_nullable=False)

    # 3. Renomear colunas em tb_converted_spreadsheets
    op.alter_column('tb_converted_spreadsheets', 'planilha_id',
                    new_column_name='spreadsheet_id',
                    existing_type=sa.UUID(),
                    existing_nullable=False)

    op.alter_column('tb_converted_spreadsheets', 'caminho',
                    new_column_name='path',
                    existing_type=sa.String(length=255),
                    existing_nullable=False)

    op.alter_column('tb_converted_spreadsheets', 'total_xmls_gerados',
                    new_column_name='total_generated_xmls',
                    existing_type=sa.Integer(),
                    existing_nullable=False)

    op.alter_column('tb_converted_spreadsheets', 'data_conversao',
                    new_column_name='converted_date',
                    existing_type=sa.DateTime(),
                    existing_nullable=False)

    # 4. Renomear colunas em tb_signed_xmls
    op.alter_column('tb_signed_xmls', 'planilha_convertida_id',
                    new_column_name='converted_spreadsheet_id',
                    existing_type=sa.UUID(),
                    existing_nullable=False)

    op.alter_column('tb_signed_xmls', 'caminho',
                    new_column_name='path',
                    existing_type=sa.String(length=255),
                    existing_nullable=False)

    op.alter_column('tb_signed_xmls', 'data_assinatura',
                    new_column_name='signed_date',
                    existing_type=sa.DateTime(),
                    existing_nullable=False)

    # 5. Renomear colunas em tb_sent_xmls
    op.alter_column('tb_sent_xmls', 'id_xml_assinado',
                    new_column_name='signed_xml_id',
                    existing_type=sa.UUID(),
                    existing_nullable=False)

    op.alter_column('tb_sent_xmls', 'caminho',
                    new_column_name='path',
                    existing_type=sa.String(length=255),
                    existing_nullable=False)

    op.alter_column('tb_sent_xmls', 'status_envio',
                    new_column_name='send_status',
                    existing_type=sa.String(length=255),
                    existing_nullable=False)

    op.alter_column('tb_sent_xmls', 'protocolo_envio',
                    new_column_name='send_protocol',
                    existing_type=sa.String(length=255),
                    existing_nullable=False)

    op.alter_column('tb_sent_xmls', 'data_envio',
                    new_column_name='sent_date',
                    existing_type=sa.DateTime(),
                    existing_nullable=False)

    # 6. Renomear colunas em tb_shipping_response
    op.alter_column('tb_shipping_response', 'enviado_id',
                    new_column_name='sent_id',
                    existing_type=sa.UUID(),
                    existing_nullable=False)

    op.alter_column('tb_shipping_response', 'caminho',
                    new_column_name='path',
                    existing_type=sa.String(length=255),
                    existing_nullable=False)

    op.alter_column('tb_shipping_response', 'data_resposta',
                    new_column_name='response_date',
                    existing_type=sa.DateTime(),
                    existing_nullable=False)

    # 7. Renomear índices
    op.drop_index('ix_planilha_id_convertida', table_name='tb_converted_spreadsheets')
    op.drop_index('ix_convertido_id_assinado', table_name='tb_signed_xmls')
    op.drop_index('ix_assinado_id_enviado', table_name='tb_sent_xmls')
    op.drop_index('ix_enviado_id_resposta', table_name='tb_shipping_response')

    op.create_index('ix_spreadsheet_id_converted', 'tb_converted_spreadsheets', ['spreadsheet_id'])
    op.create_index('ix_converted_id_signed', 'tb_signed_xmls', ['converted_spreadsheet_id'])
    op.create_index('ix_signed_id_sent', 'tb_sent_xmls', ['signed_xml_id'])
    op.create_index('ix_sent_id_response', 'tb_shipping_response', ['sent_id'])


def downgrade() -> None:
    """
    Reverte todas as traduções de EN para PT
    """

    # Reverter índices
    op.drop_index('ix_spreadsheet_id_converted', table_name='tb_converted_spreadsheets')
    op.drop_index('ix_converted_id_signed', table_name='tb_signed_xmls')
    op.drop_index('ix_signed_id_sent', table_name='tb_sent_xmls')
    op.drop_index('ix_sent_id_response', table_name='tb_shipping_response')

    op.create_index('ix_planilha_id_convertida', 'tb_converted_spreadsheets', ['spreadsheet_id'])
    op.create_index('ix_convertido_id_assinado', 'tb_signed_xmls', ['converted_spreadsheet_id'])
    op.create_index('ix_assinado_id_enviado', 'tb_sent_xmls', ['signed_xml_id'])
    op.create_index('ix_enviado_id_resposta', 'tb_shipping_response', ['sent_id'])

    # Reverter colunas em tb_shipping_response
    op.alter_column('tb_shipping_response', 'sent_id', new_column_name='enviado_id')
    op.alter_column('tb_shipping_response', 'path', new_column_name='caminho')
    op.alter_column('tb_shipping_response', 'response_date', new_column_name='data_resposta')

    # Reverter colunas em tb_sent_xmls
    op.alter_column('tb_sent_xmls', 'signed_xml_id', new_column_name='id_xml_assinado')
    op.alter_column('tb_sent_xmls', 'path', new_column_name='caminho')
    op.alter_column('tb_sent_xmls', 'send_status', new_column_name='status_envio')
    op.alter_column('tb_sent_xmls', 'send_protocol', new_column_name='protocolo_envio')
    op.alter_column('tb_sent_xmls', 'sent_date', new_column_name='data_envio')

    # Reverter colunas em tb_signed_xmls
    op.alter_column('tb_signed_xmls', 'converted_spreadsheet_id', new_column_name='planilha_convertida_id')
    op.alter_column('tb_signed_xmls', 'path', new_column_name='caminho')
    op.alter_column('tb_signed_xmls', 'signed_date', new_column_name='data_assinatura')

    # Reverter colunas em tb_converted_spreadsheets
    op.alter_column('tb_converted_spreadsheets', 'spreadsheet_id', new_column_name='planilha_id')
    op.alter_column('tb_converted_spreadsheets', 'path', new_column_name='caminho')
    op.alter_column('tb_converted_spreadsheets', 'total_generated_xmls', new_column_name='total_xmls_gerados')
    op.alter_column('tb_converted_spreadsheets', 'converted_date', new_column_name='data_conversao')

    # Reverter colunas em tb_spreadsheets
    op.alter_column('tb_spreadsheets', 'company_id', new_column_name='empresa_id')
    op.alter_column('tb_spreadsheets', 'event', new_column_name='evento')
    op.alter_column('tb_spreadsheets', 'filename', new_column_name='nome_arquivo')
    op.alter_column('tb_spreadsheets', 'file_type', new_column_name='tipo')
    op.alter_column('tb_spreadsheets', 'path', new_column_name='caminho')
    op.alter_column('tb_spreadsheets', 'received_date', new_column_name='data_recebimento')

    # Reverter nomes de tabelas
    op.rename_table('tb_spreadsheets', 'tb_planilhas')
    op.rename_table('tb_converted_spreadsheets', 'tb_planilhas_convertidas')
    op.rename_table('tb_signed_xmls', 'tb_xmls_assinados')
    op.rename_table('tb_sent_xmls', 'tb_xmls_enviados')
    op.rename_table('tb_shipping_response', 'tb_resposta_envio')
