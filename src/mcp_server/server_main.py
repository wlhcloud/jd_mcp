import logging

from fastmcp import FastMCP
from mcp_server.http_base import mcp_lifespan
from mcp_server.tool_logging import ToolLoggingMiddleware
from mcp_server.server_config import MCP_HOST, MCP_PORT, MCP_PATH
from mcp_server.tools.literature_tools import register_literature_tools
from mcp_server.tools.media_tools import register_media_tools
from mcp_server.tools.train_tools import register_train_tools

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

mcp = FastMCP(
    name="简牍业务 MCP 中台",
    instructions="统一调用简牍文献、字图向量和 OCR Pipeline 服务。",
    version="1.0.0",
    lifespan=mcp_lifespan,
    middleware=[ToolLoggingMiddleware()],
)

register_literature_tools(mcp)
register_media_tools(mcp)
register_train_tools(mcp)


def main():
    mcp.run(transport="streamable-http", host=MCP_HOST, port=MCP_PORT, path=MCP_PATH)
