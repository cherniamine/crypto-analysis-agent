from app.database.repository import ConversationRepository
def test_conversation_persists(tmp_path):
    r=ConversationRepository(f"sqlite:///{tmp_path/'test.db'}"); cid=r.create("Test"); r.add_message(cid,"user","hello"); assert r.messages(cid)[0]["content"]=="hello"
