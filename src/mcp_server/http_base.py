from contextlib import asynccontextmanager
import httpx
from fastmcp import FastMCP
from mcp_server.server_config import MCP_HTTP_TIMEOUT


@asynccontextmanager
async def mcp_lifespan(server: FastMCP):
    """创建共享 HTTP 连接池，并在 MCP 服务关闭时释放。"""
    client = httpx.AsyncClient(
        timeout=MCP_HTTP_TIMEOUT,
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
    )
    yield {"http_client": client}
    await client.aclose()
