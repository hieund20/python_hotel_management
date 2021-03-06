"""Initial migration.

Revision ID: 8e82975bda04
Revises: e85c7a4834bd
Create Date: 2022-01-04 19:35:49.504889

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '8e82975bda04'
down_revision = 'e85c7a4834bd'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('rental_voucher', sa.Column('booking_date', sa.DateTime(), nullable=True))
    op.drop_column('rental_voucher', 'start_date')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('rental_voucher', sa.Column('start_date', mysql.DATETIME(), nullable=True))
    op.drop_column('rental_voucher', 'booking_date')
    # ### end Alembic commands ###
