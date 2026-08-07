import time

import httpx
from mcp_server.logger import log
from mcp_server.server_config import MCP_API_KEY


def headers():
    return {"Authorization": f"Bearer {MCP_API_KEY}"} if MCP_API_KEY else {}


async def request_json(client: httpx.AsyncClient, method: str, url: str, **kwargs):
    started = time.perf_counter()
    log.info("http_request_start method={} url={}", method, url)
    try:
        request_headers = headers()
        request_headers.update(kwargs.pop("headers", {}) or {})
        response = await client.request(
            method, url, headers=request_headers, **kwargs
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.raise_for_status()
        data = response.json()
        log.info("http_request_end method={} url={} status={} elapsed_ms={:.1f}", method, url, response.status_code, elapsed_ms)
        return data
    except Exception:
        elapsed_ms = (time.perf_counter() - started) * 1000
        log.exception("http_request_error method={} url={} elapsed_ms={:.1f}", method, url, elapsed_ms)
        raise
