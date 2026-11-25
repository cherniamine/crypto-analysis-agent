from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from pathlib import Path
from app.core.config import get_settings
from app.database.models import Base
def normalized_url(url: str) -> str:
    return url.replace("postgresql://","postgresql+psycopg://",1) if url.startswith("postgresql://") else url.replace("postgres://","postgresql+psycopg://",1)
def create_database(url: str | None = None):
    value=normalized_url(url or get_settings().database_url); kwargs={"connect_args":{"check_same_thread":False}} if value.startswith("sqlite") else {"pool_pre_ping":True}
    if value.startswith("sqlite:///"):
        Path(value.removeprefix("sqlite:///")).parent.mkdir(parents=True,exist_ok=True)
    engine=create_engine(value,**kwargs); return engine,sessionmaker(bind=engine,autoflush=False,expire_on_commit=False)
engine,SessionLocal=create_database()
def init_database(): Base.metadata.create_all(engine)
def database_health():
    try:
        with engine.connect() as connection: connection.execute(text("SELECT 1"))
        return "reachable"
    except Exception: return "unavailable"
