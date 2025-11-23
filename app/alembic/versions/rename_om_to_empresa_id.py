"""Rename om to empresa_id for generalization

Revision ID: b3f8c9d21a45
Revises: a7b9c425f60f
Create Date: 2025-01-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3f8c9d21a45'
down_revision = 'a7b9c425f60f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Renomeia a coluna 'om' para 'empresa_id' na tabela tb_planilhas.

    Esta alteração generaliza a API, removendo a referência específica à
    Organização Militar (Marinha) e tornando-a utilizável por qualquer empresa.
    """
    # Renomeia a coluna om para empresa_id
    op.alter_column('tb_planilhas', 'om',
                    new_column_name='empresa_id',
                    existing_type=sa.String(length=50),
                    existing_nullable=False)


def downgrade() -> None:
    """
    Reverte a renomeação, restaurando a coluna 'empresa_id' para 'om'.
    """
    # Reverte a renomeação
    op.alter_column('tb_planilhas', 'empresa_id',
                    new_column_name='om',
                    existing_type=sa.String(length=50),
                    existing_nullable=False)
