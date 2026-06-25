"""Normalized HTTP route handler results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator, Optional, Union


@dataclass(frozen=True)
class HttpRouteResponse:
    mode: str  # "json" | "bytes" | "sse"
    status: int
    json_body: Any = None
    bytes_body: bytes = b""
    content_type: str = "application/json; charset=utf-8"
    filename: str = ""
    sse_body: Any = None

    @classmethod
    def json(cls, body: Any, status: int = 200) -> "HttpRouteResponse":
        return cls(mode="json", status=status, json_body=body)

    @classmethod
    def bytes(
        cls,
        data: bytes,
        content_type: str,
        status: int = 200,
        *,
        filename: str = "",
    ) -> "HttpRouteResponse":
        return cls(
            mode="bytes",
            status=status,
            bytes_body=data,
            content_type=content_type,
            filename=filename,
        )

    @classmethod
    def sse(
        cls,
        generator: Iterator[Union[str, bytes]],
        status: int = 200,
    ) -> "HttpRouteResponse":
        return cls(mode="sse", status=status, sse_body=generator)


def apply_route_response(handler: Any, response: HttpRouteResponse) -> None:
    if response.mode == "bytes":
        handler._bytes(response.bytes_body, response.content_type, response.status, response.filename)
    elif response.mode == "sse":
        handler._sse(response.sse_body, response.status)
    else:
        handler._json(response.json_body, response.status)
