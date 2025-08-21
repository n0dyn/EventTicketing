"""add_payment_models

Revision ID: d0a611e6758a
Revises: ff85fe3a7630
Create Date: 2025-06-10 16:19:01.557095

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'd0a611e6758a'
down_revision = 'ff85fe3a7630'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create payment_status enum
    payment_status_enum = postgresql.ENUM(
        'pending', 'succeeded', 'failed', 'canceled', 'refunded', 'partially_refunded',
        name='payment_status'
    )
    payment_status_enum.create(op.get_bind())
    
    # Create payment table
    op.create_table('payment',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('order_id', sa.String(), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),  # Amount in cents
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('status', sa.Enum('pending', 'succeeded', 'failed', 'canceled', 'refunded', 'partially_refunded', name='payment_status'), nullable=False, server_default='pending'),
        sa.Column('stripe_payment_intent_id', sa.String(), nullable=True),
        sa.Column('stripe_customer_id', sa.String(), nullable=True),
        sa.Column('payment_method_id', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['order_id'], ['order.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payment_id'), 'payment', ['id'], unique=False)
    op.create_index(op.f('ix_payment_stripe_payment_intent_id'), 'payment', ['stripe_payment_intent_id'], unique=False)
    op.create_index(op.f('ix_payment_status'), 'payment', ['status'], unique=False)
    
    # Create refund table
    op.create_table('refund',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('payment_id', sa.String(), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),  # Amount in cents
        sa.Column('reason', sa.String(), nullable=True),
        sa.Column('stripe_refund_id', sa.String(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'succeeded', 'failed', 'canceled', 'refunded', 'partially_refunded', name='payment_status'), nullable=False, server_default='pending'),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['payment_id'], ['payment.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_refund_id'), 'refund', ['id'], unique=False)
    op.create_index(op.f('ix_refund_stripe_refund_id'), 'refund', ['stripe_refund_id'], unique=False)
    
    # Create payment_webhook table
    op.create_table('payment_webhook',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('stripe_event_id', sa.String(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('processed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('processing_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stripe_event_id', name='uix_payment_webhook_stripe_event_id')
    )
    op.create_index(op.f('ix_payment_webhook_id'), 'payment_webhook', ['id'], unique=False)
    op.create_index(op.f('ix_payment_webhook_event_type'), 'payment_webhook', ['event_type'], unique=False)
    op.create_index(op.f('ix_payment_webhook_processed'), 'payment_webhook', ['processed'], unique=False)
    
    # Create payment_attempt table
    op.create_table('payment_attempt',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('payment_id', sa.String(), nullable=False),
        sa.Column('stripe_payment_intent_id', sa.String(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'succeeded', 'failed', 'canceled', 'refunded', 'partially_refunded', name='payment_status'), nullable=False),
        sa.Column('failure_reason', sa.String(), nullable=True),
        sa.Column('failure_code', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['payment_id'], ['payment.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payment_attempt_id'), 'payment_attempt', ['id'], unique=False)
    op.create_index(op.f('ix_payment_attempt_status'), 'payment_attempt', ['status'], unique=False)


def downgrade() -> None:
    # Drop payment_attempt table
    op.drop_index(op.f('ix_payment_attempt_status'), table_name='payment_attempt')
    op.drop_index(op.f('ix_payment_attempt_id'), table_name='payment_attempt')
    op.drop_table('payment_attempt')
    
    # Drop payment_webhook table
    op.drop_index(op.f('ix_payment_webhook_processed'), table_name='payment_webhook')
    op.drop_index(op.f('ix_payment_webhook_event_type'), table_name='payment_webhook')
    op.drop_index(op.f('ix_payment_webhook_id'), table_name='payment_webhook')
    op.drop_table('payment_webhook')
    
    # Drop refund table
    op.drop_index(op.f('ix_refund_stripe_refund_id'), table_name='refund')
    op.drop_index(op.f('ix_refund_id'), table_name='refund')
    op.drop_table('refund')
    
    # Drop payment table
    op.drop_index(op.f('ix_payment_status'), table_name='payment')
    op.drop_index(op.f('ix_payment_stripe_payment_intent_id'), table_name='payment')
    op.drop_index(op.f('ix_payment_id'), table_name='payment')
    op.drop_table('payment')
    
    # Drop payment_status enum
    op.execute('DROP TYPE payment_status') 