"""
CursorPaginator — Cursor-based pagination for DRF.

Provides efficient pagination for large datasets by using a cursor
(offset) rather than page numbers. This avoids the O(n) cost of
OFFSET/LIMIT pagination on large tables.

Configuration in settings:
    DEFAULT_PAGINATION_CLASS: core.pagination.CursorPaginator
    PAGE_SIZE: 20
    MAX_PAGE_SIZE: 100
"""

from collections import OrderedDict
from typing import Any

from rest_framework.pagination import CursorPagination as DRFCursorPagination
from rest_framework.response import Response


class CursorPaginator(DRFCursorPagination):
    """
    Cursor-based paginator with a default page size of 20 and max of 100.

    Response format:
    {
        "next": "<cursor>",
        "previous": "<cursor>",
        "results": [...]
    }
    """

    page_size = 20
    max_page_size = 100
    page_size_query_param = "page_size"
    ordering = "-created_at"  # Default ordering for cursor pagination

    def get_paginated_response(self, data: Any) -> Response:
        """Return a standardized paginated response.

        NOTE: Signature matches DRF's GenericAPIView which calls
        self.paginator.get_paginated_response(data) where `data` is
        the already-serialized result list.
        """
        return Response(
            OrderedDict(
                [
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("results", data),
                ]
            )
        )
