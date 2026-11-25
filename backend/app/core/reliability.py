import asyncio
from collections.abc import Awaitable, Callable
import httpx

RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}

async def request_with_retry(operation: Callable[[], Awaitable[httpx.Response]], attempts: int = 3) -> httpx.Response:
    for attempt in range(attempts):
        try:
            response = await operation()
            if response.status_code not in RETRYABLE_STATUS or attempt == attempts - 1:
                return response
        except (httpx.TimeoutException, httpx.NetworkError):
            if attempt == attempts - 1: raise
        await asyncio.sleep(0.25 * (2 ** attempt))
    raise RuntimeError("request retry policy exhausted")
