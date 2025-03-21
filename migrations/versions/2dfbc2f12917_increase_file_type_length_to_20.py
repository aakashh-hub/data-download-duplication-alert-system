"""Increase file_type length to 20

Revision ID: 2dfbc2f12917
Revises: c47c1ad3ac3f
Create Date: 2025-03-09 21:18:45.365505

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '2dfbc2f12917'
down_revision = 'c47c1ad3ac3f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('file_record', schema=None) as batch_op:
        batch_op.alter_column('file_type',
               existing_type=mysql.VARCHAR(length=10),
               type_=sa.String(length=20),
               existing_nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('file_record', schema=None) as batch_op:
        batch_op.alter_column('file_type',
               existing_type=sa.String(length=20),
               type_=mysql.VARCHAR(length=10),
               existing_nullable=False)

    # ### end Alembic commands ###
