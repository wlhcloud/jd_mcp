import time

import httpx
from mcp_server.logger import log
from mcp_server.server_config import MCP_API_KEY


def headers():
    return {"Authorization": f"Bearer {MCP_API_KEY}"} if MCP_API_KEY else {}


async def request_json(client: httpx.AsyncClient, method: str, url: str, **kwargs):
    started = time.perf_counter()
    log.info("http_request_start method=%s url=%s", method, url)
    try:
        response = await client.request(method, url, headers=headers(), **kwargs)
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.raise_for_status()
        data = response.json()
        log.info("http_request_end method=%s url=%s status=%s elapsed_ms=%.1f", method, url, response.status_code, elapsed_ms)
        return data
    except Exception:
        elapsed_ms = (time.perf_counter() - started) * 1000
        log.exception("http_request_error method=%s url=%s elapsed_ms=%.1f", method, url, elapsed_ms)
        raise
