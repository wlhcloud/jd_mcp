"""FastMCP 工具调用审计日志。"""

from __future__ import annotations

import time
from typing import Any

from fastmcp.server.middleware import Middleware, MiddlewareContext, CallNext
from mcp_server.logger import log


def _safe(value: Any, depth: int = 0) -> Any:
    """截断参数并隐藏 base64、密钥等敏感内容，避免日志污染和泄露。"""
    if depth > 3:
        return "<nested>"
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            key_text = str(key)
            if key_text.lower() in {"dataurl", "data_url", "content", "token", "api_key", "authorization"}:
                result[key_text] = "<redacted>"
            else:
                result[key_text] = _safe(item, depth + 1)
        return result
    if isinstance(value, (list, tuple)):
        return [_safe(item, depth + 1) for item in value[:10]]
    if isinstance(value, str) and len(value) > 500:
        return f"{value[:500]}...<truncated>"
    return value


class ToolLoggingMiddleware(Middleware):
    """记录每次 MCP 工具调用的名称、参数摘要、耗时和结果状态。"""

    async def on_call_tool(self, context: MiddlewareContext, call_next: CallNext):
        message = context.message
        tool_name = getattr(message, "name", "unknown")
        arguments = getattr(message, "arguments", None) or {}
        started = time.perf_counter()
        log.info("tool_start name={} args={}", tool_name, _safe(arguments))
        try:
            result = await call_next(context)
            elapsed_ms = (time.perf_counter() - started) * 1000
            log.info("tool_end name={} status=success elapsed_ms={:.1f}", tool_name, elapsed_ms)
            return result
        except Exception:
            elapsed_ms = (time.perf_counter() - started) * 1000
            log.exception("tool_end name={} status=error elapsed_ms={:.1f}", tool_name, elapsed_ms)
            raise
