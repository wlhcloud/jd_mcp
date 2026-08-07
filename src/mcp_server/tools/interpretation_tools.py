from typing import Optional

from fastmcp import Context, FastMCP

from mcp_server.logger import log
from mcp_server.server_config import JD_API_BASE_URL
from mcp_server.tools.common import request_json

GROUP_NAME = "jiandu_interpretation"


def register_interpretation_tools(mcp: FastMCP):
    """注册释文管理模块的智能体查询工具。"""

    @mcp.tool(name=f"{GROUP_NAME}_search")
    async def interpretation_search(
        preliminary_text: Optional[str] = None,
        slip_code: Optional[str] = None,
        slip_name: Optional[str] = None,
        era: Optional[str] = None,
        top_k: int = 5,
        ctx: Context = None,
    ) -> dict:
        """查询释文管理模块中已有的简牍释文。

        优先按简号精确匹配，其次按名称和 OCR 初步释文匹配。适用于释读、
        翻译、内容理解和考证，不适用于只要求识字或检测框的请求。

        返回结构：查询结果对象（包装层 {code, success, data, msg}），data 为释文记录数组，每条含：
        - id: 记录 ID
        - slip_code: 简牍编号
        - total_code: 总编号
        - slip_name: 简牍名称
        - era: 时代
        - interpretation: 已有释文内容
        - remark: 备注
        - match_type: 命中方式（slip_code / slip_name / preliminary_text 等）
        - source_type: 固定为 interpretation_management

        Args:
            preliminary_text: OCR 初步释文文本，用于模糊匹配。
            slip_code: 简牍编号，精确匹配优先。
            slip_name: 简牍名称。
            era: 时代。
            top_k: 返回记录数量，范围 1-20。
            ctx: MCP 运行上下文，由框架注入。
        """
        if not any(
            str(value or "").strip()
            for value in (preliminary_text, slip_code, slip_name)
        ):
            raise ValueError("preliminary_text、slip_code、slip_name 至少传一项")
        if not 1 <= int(top_k) <= 20:
            raise ValueError("top_k 必须在 1 到 20 之间")

        client = ctx.request_context.lifespan_context["http_client"]
        payload = {
            "preliminary_text": str(preliminary_text or "").strip(),
            "slip_code": str(slip_code or "").strip(),
            "slip_name": str(slip_name or "").strip(),
            "era": str(era or "").strip(),
            "top_k": int(top_k),
        }
        log.info(
            "interpretation_search slip_code=%s slip_name=%s top_k=%s",
            payload["slip_code"],
            payload["slip_name"],
            payload["top_k"],
        )
        return await request_json(
            client,
            "POST",
            f"{JD_API_BASE_URL}/mcp/jiandu/interpretations/search",
            json=payload,
        )
