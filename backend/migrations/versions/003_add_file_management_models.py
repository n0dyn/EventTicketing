"""Add file management models

Revision ID: 003_add_file_management_models
Revises: ff85fe3a7630_add_price_tiers_and_promo_codes
Create Date: 2025-08-20 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_add_file_management_models'
down_revision = 'ff85fe3a7630_add_price_tiers_and_promo_codes'
branch_labels = None
depends_on = None


def upgrade():
    # Create files table
    op.create_table('files',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('size', sa.BigInteger(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('file_type', sa.String(length=20), nullable=False),
        sa.Column('path', sa.String(length=500), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('variants', sa.Text(), nullable=True),
        sa.Column('uploaded_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['uploaded_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('path')
    )
    
    # Create indexes
    op.create_index(op.f('ix_files_filename'), 'files', ['filename'], unique=False)
    op.create_index(op.f('ix_files_category'), 'files', ['category'], unique=False)
    op.create_index(op.f('ix_files_uploaded_by_id'), 'files', ['uploaded_by_id'], unique=False)
    
    # Add media columns to users table
    op.add_column('users', sa.Column('profile_image_path', sa.String(length=500), nullable=True))
    
    # Add media columns to events table
    op.add_column('events', sa.Column('banner_image_path', sa.String(length=500), nullable=True))
    op.add_column('events', sa.Column('gallery_images', sa.Text(), nullable=True))


def downgrade():
    # Remove columns from events table
    op.drop_column('events', 'gallery_images')
    op.drop_column('events', 'banner_image_path')
    
    # Remove columns from users table
    op.drop_column('users', 'profile_image_path')
    
    # Drop indexes
    op.drop_index(op.f('ix_files_uploaded_by_id'), table_name='files')
    op.drop_index(op.f('ix_files_category'), table_name='files')
    op.drop_index(op.f('ix_files_filename'), table_name='files')
    
    # Drop files table
    op.drop_table('files')