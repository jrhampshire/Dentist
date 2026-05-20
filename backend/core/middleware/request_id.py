"""
RequestIDMiddleware — Generates a unique UUID for each request.

Attaches X-Request-ID header to the response for distributed tracing
and correlation with logs.
"""

import logging
import uuid
from typing import Callable

from django.http.request import HttpRequest
from django.http.response import HttpResponse

logger = logging.getLogger(__name__)


class RequestIDMiddleware:
    """
    Middleware that generates a unique request ID for tracing.

    - If the client sends an X-Request-ID header, it is reused.
    - Otherwise, a new UUID4 is generated.
    - The ID is attached to the request object and the response header.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Use client-provided ID or generate a new one
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.request_id = request_id  # type: ignore[attr-defined]

        response = self.get_response(request)
        response["X-Request-ID"] = request_id

        return response
