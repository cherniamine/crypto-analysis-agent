import logging, time
from contextvars import ContextVar
from uuid import uuid4

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
logger = logging.getLogger("crypto_agent")
if not logger.handlers:
    handler=logging.StreamHandler(); handler.setFormatter(logging.Formatter('%(message)s')); logger.addHandler(handler); logger.setLevel(logging.INFO)
def new_request_id():
    value=str(uuid4()); request_id_var.set(value); return value
def log_event(event, **fields):
    safe={"event":event,"request_id":request_id_var.get(),**fields}; logger.info(__import__("json").dumps(safe,default=str))
class Timer:
    def __enter__(self): self.started=time.perf_counter(); return self
    def __exit__(self,*args): self.duration_ms=round((time.perf_counter()-self.started)*1000,2)
