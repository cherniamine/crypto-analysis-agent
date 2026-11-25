"""Optional LangGraph checkpoint backends, separate from application messages."""
def checkpoint_backend(database_url: str):
    if database_url.startswith("sqlite:"):
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
        except ImportError as exc: raise RuntimeError("Install langgraph-checkpoint-sqlite to enable SQLite LangGraph checkpoints") from exc
        return SqliteSaver.from_conn_string(database_url.replace("sqlite:///", ""))
    if database_url.startswith(("postgresql:","postgres:")):
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
        except ImportError as exc: raise RuntimeError("Install langgraph-checkpoint-postgres to enable PostgreSQL LangGraph checkpoints") from exc
        return PostgresSaver.from_conn_string(database_url)
    raise ValueError("Unsupported checkpoint database URL")
