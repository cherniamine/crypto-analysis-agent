"""Genuine FastAPI restart validation for application conversation persistence.

This deliberately tests application messages separately from LangGraph checkpoints.
It uses the real backend and configured LLM, so it may incur local model latency.
"""
import argparse, os, subprocess, sys, time
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]; BACKEND=ROOT/'backend'
def wait_for(url, timeout=20):
    deadline=time.time()+timeout
    while time.time()<deadline:
        try:
            if httpx.get(url,timeout=2).status_code < 500: return True
        except Exception: pass
        time.sleep(.5)
    return False
def start(env):
    return subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000'],cwd=BACKEND,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--message',default='Hello, give a brief educational overview.'); args=parser.parse_args()
    env=os.environ.copy(); env['PYTHONPATH']=str(BACKEND); env['DATABASE_URL']=f"sqlite:///{(ROOT/'phase8-http-persistence.db').resolve()}"
    first=start(env); thread=None
    try:
        if not wait_for('http://127.0.0.1:8000/health'): raise RuntimeError('backend did not become healthy')
        one=httpx.post('http://127.0.0.1:8000/api/chat',json={'message':args.message},timeout=120).json(); thread=one['thread_id']
        two=httpx.post('http://127.0.0.1:8000/api/chat',json={'message':'What about Ethereum?','thread_id':thread},timeout=120).json()
        first_count=len(httpx.get(f'http://127.0.0.1:8000/api/conversations/{thread}').json()['messages'])
        first.terminate(); first.wait(timeout=10)
        second=start(env)
        try:
            if not wait_for('http://127.0.0.1:8000/health'): raise RuntimeError('backend did not restart')
            history=httpx.get(f'http://127.0.0.1:8000/api/conversations/{thread}',timeout=15).json()['messages']
            print({'repository_persistence':'passed' if len(history)==first_count==4 else 'failed','thread_id_present':bool(thread),'messages_after_restart':len(history),'follow_up_same_thread':two['thread_id']==thread,'checkpoint_persistence':'not_tested_by_http_script'})
        finally: second.terminate(); second.wait(timeout=10)
    finally:
        if first.poll() is None: first.kill()
if __name__=='__main__': main()
