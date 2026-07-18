from __future__ import annotations

import secrets
import string
from typing import Any

from agents import Span, Trace, TracingProcessor

from backend.database import write_log


ALPHANUM = string.ascii_lowercase + string.digits
TRACE_RANDOM_LENGTH = 32


def _sanitize_tag(tag: str) -> str:
    cleaned = "".join(
        char for char in tag.strip().lower().replace("0", "o")
        if char in ALPHANUM
    )
    return cleaned or "trader"


def make_trace_id(tag: str) -> str:
    """Create an Agents SDK trace id with a trader tag embedded."""

    embedded_tag = f"{_sanitize_tag(tag)}0"
    if len(embedded_tag) >= TRACE_RANDOM_LENGTH:
        embedded_tag = f"{embedded_tag[: TRACE_RANDOM_LENGTH - 1]}0"

    pad_len = TRACE_RANDOM_LENGTH - len(embedded_tag)
    suffix = "".join(secrets.choice(ALPHANUM) for _ in range(pad_len))
    return f"trace_{embedded_tag}{suffix}"


class LogTracer(TracingProcessor):
    """Write Agents SDK trace and span lifecycle events to account logs."""

    def _extract_name(self, trace_or_span: Trace | Span[Any]) -> str | None:
        trace_id = getattr(trace_or_span, "trace_id", "")
        if not trace_id.startswith("trace_"):
            return None

        tagged_part = trace_id.removeprefix("trace_")
        if "0" not in tagged_part:
            return None

        name = tagged_part.split("0", 1)[0].strip()
        return name or None

    def _write(self, name: str | None, log_type: str, message: str) -> None:
        if not name:
            return

        try:
            write_log(name, log_type, message)
        except Exception:
            pass

    def on_trace_start(self, trace: Trace) -> None:
        name = self._extract_name(trace)
        self._write(name, "trace", f"Trace started: {trace.name}")

    def on_trace_end(self, trace: Trace) -> None:
        name = self._extract_name(trace)
        self._write(name, "trace", f"Trace ended: {trace.name}")

    def on_span_start(self, span: Span[Any]) -> None:
        self._write_span(span, "Span started")

    def on_span_end(self, span: Span[Any]) -> None:
        self._write_span(span, "Span ended")

    def _write_span(self, span: Span[Any], prefix: str) -> None:
        name = self._extract_name(span)
        span_data = getattr(span, "span_data", None)
        span_type = getattr(span_data, "type", None) or "span"

        details = [prefix, f"type={span_type}"]

        function_name = getattr(span_data, "name", None)
        if function_name:
            details.append(f"function={function_name}")

        server_name = self._server_name(span_data)
        if server_name:
            details.append(f"server={server_name}")

        error = getattr(span, "error", None)
        if error:
            details.append(f"error={self._format_error(error)}")

        self._write(name, span_type, " ".join(details))

    def _server_name(self, span_data: Any) -> str | None:
        server_name = getattr(span_data, "server", None)
        if server_name:
            return str(server_name)

        mcp_data = getattr(span_data, "mcp_data", None)
        if isinstance(mcp_data, dict) and mcp_data.get("server"):
            return str(mcp_data["server"])

        return None

    def _format_error(self, error: Any) -> str:
        if isinstance(error, dict):
            message = error.get("message")
            data = error.get("data")
            if data:
                return f"{message} data={data}"
            if message:
                return str(message)
        return str(error)

    def force_flush(self) -> None:
        pass

    def shutdown(self) -> None:
        pass
