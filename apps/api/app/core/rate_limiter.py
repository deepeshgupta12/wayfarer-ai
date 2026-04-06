"""
Rate limiter singleton using slowapi (Starlette-compatible wrapper for limits).

Usage in a route:
    from app.core.rate_limiter import limiter
    from fastapi import Request

    @router.post("/some-llm-endpoint")
    @limiter.limit("10/minute")
    def my_endpoint(request: Request, ...):
        ...

The SlowAPIMiddleware must be added to the FastAPI app (done in main.py).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
