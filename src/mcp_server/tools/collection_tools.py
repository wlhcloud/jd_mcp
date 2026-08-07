"""藏品系统关键字检索工具：查询藏品与数字资产数据（jd 平台 fullText 接口）。"""

from __future__ import annotations

from typing import Optional
from math import ceil
from urllib.parse import quote

from fastmcp import FastMCP, Context

from mcp_server.logger import log
from mcp_server.server_config import COLLECTION_SEARCH_URL
from mcp_server.tools.common import request_json

GROUP_NAME = "collection"


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


async def _fetch_all_by_app(
    client, keyword: str, bus_app_name: str, max_pages: int = 200
) -> list[dict]:
    """接口不支持按 busAppName 服务端过滤：拉取全量后本地按业务应用名过滤。"""
    items_all: list[dict] = []
    page_no = 1
    while page_no <= max_pages:
        url = (
            f"{COLLECTION_SEARCH_URL}/platform/fullTextController.do?getSearchData"
            f"&keyword={quote(keyword)}&page={page_no}&size=50"
        )
        result = await request_json(client, "GET", url)
        if not isinstance(result, dict):
            break
        items = result.get("list") or []
        items_all.extend(items)
        page_total = int(result.get("pageTotal") or 0)
        if page_no >= page_total or not items:
            break
        page_no += 1
    return [it for it in items_all if (it.get("busAppName") or "") == bus_app_name]


def register_collection_tools(mcp: FastMCP) -> None:
    @mcp.tool(name=f"{GROUP_NAME}_search")
    async def collection_search(
        keyword: str,
        bus_app_name: Optional[str] = None,
        page: int = 1,
        size: int = 10,
        ctx: Context = None,
    ) -> dict:
        """按关键字检索藏品系统的藏品与数字资产（全文匹配标题和正文，返回分页命中结果）。

        返回结构：分页检索结果对象：
        - keyword: 本次检索关键字
        - bus_app_name: 传入的业务应用名过滤值（未过滤时为 null）
        - page / size: 当前页码 / 每页条数
        - total: 命中总数（无结果时为 0）
        - pageTotal: 总页数（无结果时为 0）
        - hasMore: 是否还有下一页
        - items: 命中列表（无结果时为空数组），每条包含：
            - title: 标题
            - content: 正文内容（原文格式，含换行符等；个别返回中命中词可能带 <em> 高亮标签，去除标签即原文）
            - busName: 业务名称（如“文件资源”“资源使用”）
            - busAppName: 业务应用名，区分数据来源（如“藏品管理”“数字资产”）
            - type: 记录类型，字符串 “0”=数据、“1”=文件
            - busDetailUrl: 详情查看地址（可能为空字符串）
            - imgUrl: 图片地址（可能为空字符串）
            - filePath: 文件路径（type 为 “1” 的文件记录可能包含，type 为 “0” 的记录通常为空）

        Args:
            keyword: 检索关键字（匹配标题与正文，正文命中会带 <em> 高亮标签）。
            bus_app_name: 可选，按业务应用名过滤（如“藏品管理”“数字资产”）；
                接口不支持服务端过滤，传入时会拉取全量后本地过滤。
            page: 页码，从 1 开始，默认 1。
            size: 每页条数，范围 1-50，默认 10。
            ctx: MCP 运行上下文，由框架注入，不需要调用方传入。
        """
        client = ctx.request_context.lifespan_context["http_client"]
        size = max(1, min(int(size or 10), 50))
        page = max(1, int(page or 1))
        log.info(
            "collection_search keyword=%s bus_app_name=%s page=%s size=%s",
            keyword[:80],
            bus_app_name,
            page,
            size,
        )
        if bus_app_name:
            filtered = await _fetch_all_by_app(client, keyword, bus_app_name)
            total = len(filtered)
            page_total = ceil(total / size) if total else 0
            start = (page - 1) * size
            items_page = filtered[start : start + size]
            return {
                "keyword": keyword,
                "bus_app_name": bus_app_name,
                "page": page,
                "size": size,
                "total": total,
                "pageTotal": page_total,
                "hasMore": page < page_total,
                "items": _public_items({"list": items_page}),
            }
        # jeecg 的 controller.do 用 ?methodName 路由：getSearchData 必须不带等号，
        # 因此手拼 URL（httpx params 会把空值编码成 getSearchData= 导致路由失败）。
        url = (
            f"{COLLECTION_SEARCH_URL}?getSearchData"
            f"&keyword={quote(keyword)}&page={page}&size={size}"
        )
        result = await request_json(client, "GET", url)
        if not isinstance(result, dict):
            return {"keyword": keyword, "total": 0, "items": []}
        total = int(result.get("total") or 0)
        page_total = int(result.get("pageTotal") or 0)
        return {
            "keyword": keyword,
            "page": page,
            "size": size,
            "total": total,
            "pageTotal": page_total,
            "hasMore": page < page_total,
            "items": _public_items(result),
        }
