import httpx
from datetime import datetime, timezone
from app.core.config import get_settings
from app.core.reliability import request_with_retry
SETTINGS = get_settings()

def normalize_news_response(data):
    raw_articles=data.get("articles",[]) if isinstance(data,dict) else []
    arts=[]; seen=set()
    for a in raw_articles:
        source=(a.get("source") or {}).get("name") if isinstance(a,dict) else None
        url=a.get("url") if isinstance(a,dict) else None
        title=a.get("title") if isinstance(a,dict) else None
        published=a.get("publishedAt") if isinstance(a,dict) else None
        key=url or title
        if not key or key in seen or not title or not source or not published: continue
        seen.add(key); arts.append({"title":title,"source":source,"url":url,"published_at":published,"description":a.get("description")})
    return arts, len(raw_articles)

async def crypto_news(query="cryptocurrency market"):
    key=SETTINGS.newsapi_api_key
    if not key: return {"status":"unavailable","message":"NewsAPI key is not configured.","articles":[],"api_articles_received":0,"normalized_articles":0,"query":query}
    try:
        async with httpx.AsyncClient(timeout=12) as c: r=await request_with_retry(lambda: c.get("https://newsapi.org/v2/everything",params={"q":query,"language":"en","sortBy":"publishedAt","pageSize":8,"apiKey":key})); r.raise_for_status(); data=r.json()
        arts, raw_count=normalize_news_response(data)
        status="ok" if arts else "empty" if raw_count == 0 else "normalized_empty"
        return {"status":status,"articles":arts,"source":"NewsAPI","retrieved_at":datetime.now(timezone.utc).isoformat(),"api_articles_received":raw_count,"normalized_articles":len(arts),"query":query}
    except Exception as e: return {"status":"error","message":str(e),"articles":[],"api_articles_received":0,"normalized_articles":0,"query":query}
