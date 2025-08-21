"""add user roles and order models

Revision ID: 001
Revises: 
Create Date: 2023-06-12 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types
    user_role = postgresql.ENUM('admin', 'organizer', 'attendee', name='userrole')
    user_role.create(op.get_bind())
    
    order_status = postgresql.ENUM('pending', 'processing', 'completed', 'cancelled', 'refunded', name='orderstatus')
    order_status.create(op.get_bind())
    
    payment_method = postgresql.ENUM('credit_card', 'paypal', 'bank_transfer', 'other', name='paymentmethod')
    payment_method.create(op.get_bind())
    
    # Add role column to user table
    op.add_column('user', sa.Column('role', sa.Enum('admin', 'organizer', 'attendee', name='userrole'), nullable=False, server_default='attendee'))
    
    # Create order table
    op.create_table(
        'order',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('total_amount', sa.Float(), nullable=False, default=0.0),
        sa.Column('status', sa.Enum('pending', 'processing', 'completed', 'cancelled', 'refunded', name='orderstatus'), nullable=False, server_default='pending'),
        sa.Column('payment_method', sa.Enum('credit_card', 'paypal', 'bank_transfer', 'other', name='paymentmethod'), nullable=True),
        sa.Column('payment_id', sa.String(), nullable=True),
        sa.Column('transaction_id', sa.String(), nullable=True, unique=True),
        sa.Column('billing_address', sa.String(), nullable=True),
        sa.Column('billing_city', sa.String(), nullable=True),
        sa.Column('billing_country', sa.String(), nullable=True),
        sa.Column('billing_postal_code', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_order_id'), 'order', ['id'], unique=False)
    
    # Create cart table
    op.create_table(
        'cart',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_cart_id'), 'cart', ['id'], unique=False)
    
    # Create cart_item table
    op.create_table(
        'cart_item',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('cart_id', sa.String(), nullable=False),
        sa.Column('ticket_type_id', sa.String(), nullable=False),
        sa.Column('order_id', sa.String(), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False, default=1),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['cart_id'], ['cart.id'], ),
        sa.ForeignKeyConstraint(['ticket_type_id'], ['ticket_type.id'], ),
        sa.ForeignKeyConstraint(['order_id'], ['order.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cart_item_id'), 'cart_item', ['id'], unique=False)
    
    # Create attendee table
    op.create_table(
        'attendee',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('first_name', sa.String(), nullable=False),
        sa.Column('last_name', sa.String(), nullable=False),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('company', sa.String(), nullable=True),
        sa.Column('job_title', sa.String(), nullable=True),
        sa.Column('is_guest', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_attendee_id'), 'attendee', ['id'], unique=False)
    op.create_index(op.f('ix_attendee_email'), 'attendee', ['email'], unique=False)
    
    # Create event_attendee table
    op.create_table(
        'event_attendee',
        sa.Column('event_id', sa.String(), nullable=False),
        sa.Column('attendee_id', sa.String(), nullable=False),
        sa.Column('checked_in', sa.Boolean(), nullable=False, default=False),
        sa.Column('checked_in_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['event_id'], ['event.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['attendee_id'], ['attendee.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('event_id', 'attendee_id')
    )
    
    # Add order_id and attendee_id to ticket
    op.add_column('ticket', sa.Column('order_id', sa.String(), nullable=True))
    op.add_column('ticket', sa.Column('attendee_id', sa.String(), nullable=True))
    
    # Add foreign key constraints for ticket table
    op.create_foreign_key('fk_ticket_order_id', 'ticket', 'order', ['order_id'], ['id'])
    op.create_foreign_key('fk_ticket_attendee_id', 'ticket', 'attendee', ['attendee_id'], ['id'])
    

def downgrade():
    # Drop foreign key constraints for ticket table
    op.drop_constraint('fk_ticket_order_id', 'ticket', type_='foreignkey')
    op.drop_constraint('fk_ticket_attendee_id', 'ticket', type_='foreignkey')
    
    # Remove columns from ticket
    op.drop_column('ticket', 'order_id')
    op.drop_column('ticket', 'attendee_id')
    
    # Drop event_attendee table
    op.drop_table('event_attendee')
    
    # Drop attendee table and indexes
    op.drop_index(op.f('ix_attendee_email'), table_name='attendee')
    op.drop_index(op.f('ix_attendee_id'), table_name='attendee')
    op.drop_table('attendee')
    
    # Drop cart_item table and index
    op.drop_index(op.f('ix_cart_item_id'), table_name='cart_item')
    op.drop_table('cart_item')
    
    # Drop cart table and index
    op.drop_index(op.f('ix_cart_id'), table_name='cart')
    op.drop_table('cart')
    
    # Drop order table and index
    op.drop_index(op.f('ix_order_id'), table_name='order')
    op.drop_table('order')
    
    # Remove role column from user table
    op.drop_column('user', 'role')
    
    # Drop enum types
    op.execute('DROP TYPE userrole')
    op.execute('DROP TYPE orderstatus')
    op.execute('DROP TYPE paymentmethod') 