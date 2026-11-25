from app.agents.checkpoints import checkpoint_backend

def test_sqlite_checkpoint_round_trip(tmp_path):
    path=tmp_path/'checkpoints.db'
    with checkpoint_backend(f"sqlite:///{path}") as saver:
        saver.setup()
        config={"configurable":{"thread_id":"integration-thread","checkpoint_ns":""}}
        checkpoint={"v":1,"id":"checkpoint-1","ts":"2026-11-24T00:00:00Z","channel_values":{"question":"BTC"},"channel_versions":{},"versions_seen":{},"pending_sends":[]}
        saver.put(config,checkpoint,{}, {})
        assert saver.get_tuple(config) is not None
