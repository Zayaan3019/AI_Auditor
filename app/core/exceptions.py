from __future__ import annotations

from fastapi import HTTPException as FastAPIHTTPException
from starlette import status


class HTTPException(FastAPIHTTPException):
    """Custom HTTP exception with consistent formatting."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(status_code=status_code, detail={"error": detail})


def bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def internal_error(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)
