"""Separar numero y codigo de piso.

Revision ID: 202608120001
Revises: 202608110001
Create Date: 2026-08-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "202608120001"
down_revision = "202608110001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pisos", sa.Column("codigo", sa.String(length=40), nullable=True))
    op.execute("UPDATE pisos SET codigo = numero")

    op.add_column("pisos", sa.Column("numero_generado", sa.Integer(), nullable=True))
    op.execute(
        """
        WITH ordered AS (
            SELECT
                id,
                ROW_NUMBER() OVER (PARTITION BY torre_id ORDER BY created_at, numero, id)::integer AS floor_number
            FROM pisos
        )
        UPDATE pisos
        SET numero_generado = ordered.floor_number
        FROM ordered
        WHERE pisos.id = ordered.id
        """
    )
    op.execute("UPDATE pisos SET nombre_visible = substr(nombre_visible, 1, 20) WHERE length(nombre_visible) > 20")
    op.drop_column("pisos", "numero")
    op.alter_column("pisos", "numero_generado", new_column_name="numero", existing_type=sa.Integer())
    op.alter_column("pisos", "numero", existing_type=sa.Integer(), nullable=False)
    op.alter_column("pisos", "nombre_visible", existing_type=sa.String(length=180), type_=sa.String(length=20), nullable=False)
    op.create_check_constraint("ck_pisos_numero_positive", "pisos", "numero >= 1")
    op.create_unique_constraint("uq_pisos_torre_numero", "pisos", ["torre_id", "numero"])


def downgrade() -> None:
    op.drop_constraint("uq_pisos_torre_numero", "pisos", type_="unique")
    op.drop_constraint("ck_pisos_numero_positive", "pisos", type_="check")
    op.alter_column("pisos", "nombre_visible", existing_type=sa.String(length=20), type_=sa.String(length=180), nullable=False)
    op.add_column("pisos", sa.Column("numero_texto", sa.String(length=40), nullable=True))
    op.execute("UPDATE pisos SET numero_texto = COALESCE(NULLIF(codigo, ''), CAST(numero AS VARCHAR))")
    op.drop_column("pisos", "numero")
    op.alter_column("pisos", "numero_texto", new_column_name="numero", existing_type=sa.String(length=40))
    op.alter_column("pisos", "numero", existing_type=sa.String(length=40), nullable=False)
    op.drop_column("pisos", "codigo")
