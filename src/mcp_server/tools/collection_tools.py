"""藏品系统关键字检索工具：查询藏品与数字资产数据（jd 平台 fullText 接口）。"""

from __future__ import annotations

from fastmcp import FastMCP, Context

from mcp_server.logger import log
from mcp_server.server_config import (
    JD_API_BASE_URL,
    MCP_COLLECTION_HTTP_TIMEOUT,
)
from mcp_server.tools.common import request_json

GROUP_NAME = "collection"
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 50
COLLECTION_PROXY_PATH = "/mcp/collection/fulltext-search"


def _public_items(data: dict) -> list[dict]:
    """仅保留回答所需的公开字段，隐藏内部业务 ID 等细节。"""
    items = data.get("list") or []
    if not isinstance(items, list):
        return []
    public = []
    for item in items:
        if not isinstance(item, dict):
            continue
        public.append(
            {
                "title": item.get("title") or "",
                "content": item.get("content") or "",  # 命中关键字带 <em> 高亮标签
                "busName": item.get("busName") or "",
                "busAppName": item.get("busAppName") or "",
                "type": item.get("type") or "",
                "busDetailUrl": item.get("busDetailUrl") or "",
                "imgUrl": item.get("imgUrl") or "",
                "filePath": item.get("filePath") or "",
            }
        )
    return public


def register_collection_tools(mcp: FastMCP) -> None:
    @mcp.tool(name=f"{GROUP_NAME}_search")
    async def collection_search(
        keyword: str,
        page: int = 1,
        size: int = DEFAULT_PAGE_SIZE,
        ctx: Context = None,
    ) -> dict:
        """按关键字检索藏品系统的藏品与数字资产（全文匹配标题和正文，返回分页命中结果）。

        Args:
            keyword: 检索关键字（匹配标题与正文，正文命中会带 <em> 高亮标签）。
            page: 页码，从 1 开始，默认 1。
            size: 每页条数，范围 1-50，默认 10。
            ctx: MCP 运行上下文，由框架注入，不需要调用方传入。
        """
        page = max(1, int(page or 1))
        size = max(1, min(int(size or DEFAULT_PAGE_SIZE), MAX_PAGE_SIZE))
        client = ctx.request_context.lifespan_context["http_client"]
        log.info(
            "collection_search keyword={} page={} size={}", keyword[:80], page, size
        )
        # 藏品旧系统的协议、连接和超时策略由 jd_api 统一适配；MCP 不再重复直连。
        # 这保证 Agent 查询与浏览器检索经过完全相同的后端入口。
        url = f"{JD_API_BASE_URL.rstrip('/')}{COLLECTION_PROXY_PATH}"
        response = await request_json(
            client,
            "POST",
            url,
            json={"keyword": keyword, "page": page, "size": size},
            timeout=MCP_COLLECTION_HTTP_TIMEOUT,
        )
        result = response.get("data") if isinstance(response, dict) else None
        if not isinstance(result, dict):
            return {
                "keyword": keyword,
                "page": page,
                "size": size,
                "total": 0,
                "pageTotal": 0,
                "hasMore": False,
                "items": [],
            }
        total = int(result.get("total") or 0)
        page_total = int(result.get("pageTotal") or 0)
        return {
            "keyword": keyword,
            "page": int(result.get("page") or page),
            "size": int(result.get("size") or size),
            "total": total,
            "pageTotal": page_total,
            "hasMore": page < page_total,
            "items": _public_items(result),
        }
