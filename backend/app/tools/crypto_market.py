import httpx
from datetime import datetime, timezone
from app.core.config import get_settings
from app.core.reliability import request_with_retry
SETTINGS = get_settings()
async def market_data(symbols=None):
    s=SETTINGS; symbols=symbols or ["BTC","ETH","SOL"]
    if not s.freecryptoapi_api_key: return {"status":"unavailable","message":"FreeCryptoAPI key is not configured.","assets":[]}
    try:
        async with httpx.AsyncClient(timeout=12) as c:
            assets=[]
            for symbol in dict.fromkeys(symbols):
                r=await request_with_retry(lambda symbol=symbol: c.get("https://api.freecryptoapi.com/v1/getData",params={"symbol":symbol},headers={"Authorization":f"Bearer {s.freecryptoapi_api_key}"})); r.raise_for_status(); p=r.json()
                current=p.get("data",p) if isinstance(p,dict) else p
                if isinstance(p,dict) and isinstance(p.get("symbols"),list): current=p["symbols"]
                if isinstance(current,dict): current=current.get("data",[current]) if isinstance(current.get("data"),list) else [current]
                if isinstance(current,list): assets.extend(item for item in current if isinstance(item,dict) and (item.get("symbol") or item.get("price") is not None or item.get("last") is not None))
        return {"status":"ok","assets":assets,"source":"FreeCryptoAPI","retrieved_at":datetime.now(timezone.utc).isoformat()}
    except Exception as e: return {"status":"error","message":str(e),"assets":[]}
