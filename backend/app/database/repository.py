from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import delete, select
from app.database.models import Conversation, Message
from app.database.session import SessionLocal, init_database

class ConversationRepository:
    def __init__(self, url=None, session_factory=None):
        if session_factory is None:
            from app.database.session import create_database
            engine, session_factory=create_database(url)
            from app.database.models import Base
            Base.metadata.create_all(engine)
        self.Session=session_factory
        if session_factory is SessionLocal: init_database()
    def create(self,title="New analysis"):
        cid=str(uuid4()); now=datetime.now(timezone.utc)
        with self.Session.begin() as db: db.add(Conversation(id=cid,title=title,updated_at=now))
        return cid
    def ensure(self,cid):
        if not cid: return self.create()
        with self.Session() as db: return cid if db.get(Conversation,cid) else self.create()
    def add_message(self,cid,role,content):
        now=datetime.now(timezone.utc)
        with self.Session.begin() as db:
            db.add(Message(conversation_id=cid,role=role,content=content,created_at=now)); item=db.get(Conversation,cid)
            if item: item.updated_at=now
    def list(self):
        with self.Session() as db: return [{"id":x.id,"title":x.title,"updated_at":x.updated_at} for x in db.scalars(select(Conversation).order_by(Conversation.updated_at.desc())).all()]
    def messages(self,cid):
        with self.Session() as db: return [{"role":x.role,"content":x.content,"created_at":x.created_at} for x in db.scalars(select(Message).where(Message.conversation_id==cid).order_by(Message.id)).all()]
    def delete(self,cid):
        with self.Session.begin() as db: db.execute(delete(Message).where(Message.conversation_id==cid)); db.execute(delete(Conversation).where(Conversation.id==cid))
