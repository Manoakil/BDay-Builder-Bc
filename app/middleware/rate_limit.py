from typing import List, Optional
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
from time import time

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self, app, 
        calls: int = 100, 
        period: int = 60, 
        exclude_routes: Optional[List[str]] = None
    ):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.client_requests = defaultdict(list)
        self.exclude_routes = exclude_routes or []

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.exclude_routes or request.url.path.startswith("/docs") or request.url.path.startswith("/openapi.json"):
            response = await call_next(request)
            return response

        client_ip = request.client.host
        current_time = time()

        # Filter out requests older than the period
        self.client_requests[client_ip] = [
            t for t in self.client_requests[client_ip] if t > current_time - self.period
        ]

        if len(self.client_requests[client_ip]) >= self.calls:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")

        self.client_requests[client_ip].append(current_time)

        response = await call_next(request)
        return response

