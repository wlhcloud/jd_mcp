from contextlib import asynccontextmanager
import httpx
from fastmcp import FastMCP
from mcp_server.logger import log
from mcp_server.server_config import MCP_HTTP_TIMEOUT


@asynccontextmanager
async def mcp_lifespan(server: FastMCP):
    """创建共享 HTTP 连接池，并在 MCP 服务关闭时释放。"""
    log.info("mcp_lifespan 创建 HTTP 连接池 timeout={}s", MCP_HTTP_TIMEOUT)
    client = httpx.AsyncClient(
        timeout=MCP_HTTP_TIMEOUT,
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
        # 禁用环境变量代理（WSL 常设 http_proxy=127.0.0.1:7890），
        # 内部服务与外部业务接口均需直连，避免走代理出口被目标拒绝。
        trust_env=False,
    )
    yield {"http_client": client}
    log.info("mcp_lifespan 关闭 HTTP 连接池")
    await client.aclose()
