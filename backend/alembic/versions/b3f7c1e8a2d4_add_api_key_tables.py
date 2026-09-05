"""add_api_key_tables_and_extend_config_category

Revision ID: b3f7c1e8a2d4
Revises: a2140a39f67d
Create Date: 2026-09-05 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b3f7c1e8a2d4'
down_revision: Union[str, None] = 'a2140a39f67d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'api_key',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('key_encrypted', sa.Text(), nullable=False),
        sa.Column('key_prefix', sa.Text(), nullable=False),
        sa.Column('scope', sa.Text(), nullable=False, server_default='all_collector'),
        sa.Column('rate_limit', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('expires_days', sa.Integer(), nullable=True),
        sa.Column('expires_at', sa.Text(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_by', sa.Text(), nullable=False),
        sa.Column('total_calls', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('success_calls', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('fail_calls', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_used_at', sa.Text(), nullable=True),
        sa.Column('created_at', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.Text(), nullable=False),
        sa.CheckConstraint(
            "scope IN ('rss_only','webpage_only','all_collector')",
            name="ck_apikey_scope",
        ),
        sa.CheckConstraint("rate_limit >= 1 AND rate_limit <= 1000", name="ck_apikey_rate"),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_apikey_name', 'api_key', ['name'], unique=True)
    op.create_index('idx_apikey_prefix', 'api_key', ['key_prefix'])

    op.create_table(
        'api_key_call_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('api_key_id', sa.Integer(), nullable=False),
        sa.Column('api_key_mask', sa.Text(), nullable=False),
        sa.Column('endpoint', sa.Text(), nullable=False),
        sa.Column('method', sa.Text(), nullable=False),
        sa.Column('params_json', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('status_code', sa.Integer(), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('result_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('client_ip', sa.Text(), nullable=False, server_default=''),
        sa.Column('created_at', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_calllog_keyid', 'api_key_call_log', ['api_key_id', 'created_at'])
    op.create_index('idx_calllog_time', 'api_key_call_log', ['created_at'])

    op.drop_constraint('ck_config_category', 'system_config', type_='check')
    op.create_check_constraint(
        'ck_config_category',
        'system_config',
        "category IN ('collect_source','ai_service','pipeline_strategy','publish_rule','unified_platform','api_key_config')",
    )

    op.execute("INSERT OR IGNORE INTO system_config (config_key, config_value, category, effect_mode, version, updated_by, updated_at) VALUES "
               "('api_key_config.default_rate_limit', '100', 'api_key_config', 'immediate', 1, 'system', ''), "
               "('api_key_config.default_expires_days', '90', 'api_key_config', 'immediate', 1, 'system', ''), "
               "('api_key_config.max_concurrent', '5', 'api_key_config', 'immediate', 1, 'system', ''), "
               "('api_key_config.max_limit_per_request', '100', 'api_key_config', 'immediate', 1, 'system', '')")


def downgrade() -> None:
    op.execute("DELETE FROM system_config WHERE category = 'api_key_config'")

    op.drop_constraint('ck_config_category', 'system_config', type_='check')
    op.create_check_constraint(
        'ck_config_category',
        'system_config',
        "category IN ('collect_source','ai_service','pipeline_strategy','publish_rule')",
    )

    op.drop_index('idx_calllog_time', table_name='api_key_call_log')
    op.drop_index('idx_calllog_keyid', table_name='api_key_call_log')
    op.drop_table('api_key_call_log')

    op.drop_index('idx_apikey_prefix', table_name='api_key')
    op.drop_index('idx_apikey_name', table_name='api_key')
    op.drop_table('api_key')