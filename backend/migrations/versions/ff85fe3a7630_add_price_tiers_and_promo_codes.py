"""add_price_tiers_and_promo_codes

Revision ID: ff85fe3a7630
Revises: 001
Create Date: 2025-05-02 08:37:11.212676

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ff85fe3a7630'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to ticket_type table
    op.add_column('ticket_type', sa.Column('sale_start_date', sa.DateTime(), nullable=True))
    op.add_column('ticket_type', sa.Column('sale_end_date', sa.DateTime(), nullable=True))
    op.add_column('ticket_type', sa.Column('min_per_order', sa.Integer(), nullable=True, server_default='1'))
    op.add_column('ticket_type', sa.Column('max_per_order', sa.Integer(), nullable=True))
    op.add_column('ticket_type', sa.Column('visibility', sa.Boolean(), nullable=True, server_default='true'))
    op.add_column('ticket_type', sa.Column('sort_order', sa.Integer(), nullable=True, server_default='0'))
    
    # Add new columns to ticket table
    op.add_column('ticket', sa.Column('price_paid', sa.Float(), nullable=True, server_default='0.0'))
    op.add_column('ticket', sa.Column('promo_code_id', sa.String(), nullable=True))
    op.create_foreign_key(
        'fk_ticket_promo_code', 'ticket', 'promo_code', ['promo_code_id'], ['id']
    )
    
    # Create discount_type enum
    discount_type_enum = postgresql.ENUM('percentage', 'fixed', name='discount_type')
    discount_type_enum.create(op.get_bind())
    
    # Create price_tier table
    op.create_table('price_tier',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('ticket_type_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=False),
        sa.Column('quantity_available', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['ticket_type_id'], ['ticket_type.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_price_tier_id'), 'price_tier', ['id'], unique=False)
    
    # Create promo_code table
    op.create_table('promo_code',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('event_id', sa.String(), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('discount_type', sa.Enum('percentage', 'fixed', name='discount_type'), nullable=False, server_default='percentage'),
        sa.Column('discount_amount', sa.Float(), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=True),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('usage_limit', sa.Integer(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['event_id'], ['event.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id', 'code', name='uix_promo_code_event_code')
    )
    op.create_index(op.f('ix_promo_code_id'), 'promo_code', ['id'], unique=False)
    op.create_index(op.f('ix_promo_code_code'), 'promo_code', ['code'], unique=False)
    
    # Create promo_code_ticket_type association table
    op.create_table('promo_code_ticket_type',
        sa.Column('promo_code_id', sa.String(), nullable=False),
        sa.Column('ticket_type_id', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['promo_code_id'], ['promo_code.id'], ),
        sa.ForeignKeyConstraint(['ticket_type_id'], ['ticket_type.id'], ),
        sa.PrimaryKeyConstraint('promo_code_id', 'ticket_type_id')
    )


def downgrade() -> None:
    # Drop promo_code_ticket_type table
    op.drop_table('promo_code_ticket_type')
    
    # Drop promo_code table
    op.drop_index(op.f('ix_promo_code_code'), table_name='promo_code')
    op.drop_index(op.f('ix_promo_code_id'), table_name='promo_code')
    op.drop_table('promo_code')
    
    # Drop price_tier table
    op.drop_index(op.f('ix_price_tier_id'), table_name='price_tier')
    op.drop_table('price_tier')
    
    # Drop discount_type enum
    op.execute('DROP TYPE discount_type')
    
    # Drop foreign key constraint in ticket table
    op.drop_constraint('fk_ticket_promo_code', 'ticket', type_='foreignkey')
    
    # Drop columns from ticket table
    op.drop_column('ticket', 'promo_code_id')
    op.drop_column('ticket', 'price_paid')
    
    # Drop columns from ticket_type table
    op.drop_column('ticket_type', 'sort_order')
    op.drop_column('ticket_type', 'visibility')
    op.drop_column('ticket_type', 'max_per_order')
    op.drop_column('ticket_type', 'min_per_order')
    op.drop_column('ticket_type', 'sale_end_date')
    op.drop_column('ticket_type', 'sale_start_date') 