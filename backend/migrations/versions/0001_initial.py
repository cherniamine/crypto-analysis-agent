"""create conversation tables"""
from alembic import op
import sqlalchemy as sa
revision="0001_initial"; down_revision=None; branch_labels=None; depends_on=None
def upgrade():
    op.create_table("conversations",sa.Column("id",sa.String(36),primary_key=True),sa.Column("title",sa.String(200),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False))
    op.create_table("messages",sa.Column("id",sa.Integer,primary_key=True),sa.Column("conversation_id",sa.String(36),sa.ForeignKey("conversations.id",ondelete="CASCADE"),nullable=False),sa.Column("role",sa.String(20),nullable=False),sa.Column("content",sa.Text,nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_messages_conversation_id","messages",["conversation_id"])
def downgrade():
    op.drop_index("ix_messages_conversation_id",table_name="messages"); op.drop_table("messages"); op.drop_table("conversations")
