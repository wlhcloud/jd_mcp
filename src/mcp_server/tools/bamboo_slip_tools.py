from typing import Optional

from fastmcp import Context, FastMCP

from mcp_server.logger import log
from mcp_server.server_config import JD_API_BASE_URL
from mcp_server.tools.common import request_json

GROUP_NAME = "jiandu_bamboo_slip"


def register_bamboo_slip_tools(mcp: FastMCP):
    """注册简牍本体管理的智能体查询工具。"""

    @mcp.tool(name=f"{GROUP_NAME}_search")
    async def bamboo_slip_search(
        slip_code: Optional[str] = None,
        excavation_number: Optional[str] = None,
        slip_name: Optional[str] = None,
        cid: Optional[str] = None,
        era: Optional[str] = None,
        script_type: Optional[str] = None,
        preliminary_text: Optional[str] = None,
        top_k: int = 5,
        ctx: Context = None,
    ) -> dict:
        """查询简牍本体身份、年代、形制、材质、保存状况、详情和图片。

        优先按简牍编号、出土号或藏品 ID 精确匹配，其次按名称和 OCR
        初步释文匹配。适用于释读、背景分析和考证，不适用于纯 OCR 请求。

        返回结构：查询结果对象（包装层 {code, success, data, msg}），data 为简牍本体记录数组，每条含：
        - id: 记录 ID
        - slip_name: 简牍名称
        - slip_code: 简牍编号
        - cid: 藏品 ID
        - excavation_number: 出土号
        - book_name: 书名
        - script_type: 书体
        - material_spec: 材质规格
        - era: 时代
        - preservation_status: 保存状态
        - basic_info: 基本信息
        - details: 详细信息
        - photo_url: 照片地址
        - match_type: 命中方式
        - source_type: 固定为 bamboo_slip_management

        Args:
            slip_code: 简牍编号，精确匹配优先。
            excavation_number: 出土号。
            slip_name: 简牍名称。
            cid: 藏品 ID。
            era: 时代。
            script_type: 书体。
            preliminary_text: OCR 初步释文文本，用于模糊匹配。
            top_k: 返回记录数量，范围 1-20。
            ctx: MCP 运行上下文，由框架注入。
        """
        if not any(
            str(value or "").strip()
            for value in (
                slip_code,
                excavation_number,
                slip_name,
                cid,
                preliminary_text,
            )
        ):
            raise ValueError(
                "slip_code、excavation_number、slip_name、cid、"
                "preliminary_text 至少传一项"
            )
        if not 1 <= int(top_k) <= 20:
            raise ValueError("top_k 必须在 1 到 20 之间")

        client = ctx.request_context.lifespan_context["http_client"]
        payload = {
            "slip_code": str(slip_code or "").strip(),
            "excavation_number": str(excavation_number or "").strip(),
            "slip_name": str(slip_name or "").strip(),
            "cid": str(cid or "").strip(),
            "era": str(era or "").strip(),
            "script_type": str(script_type or "").strip(),
            "preliminary_text": str(preliminary_text or "").strip(),
            "top_k": int(top_k),
        }
        log.info(
            "bamboo_slip_search slip_code=%s excavation_number=%s cid=%s top_k=%s",
            payload["slip_code"],
            payload["excavation_number"],
            payload["cid"],
            payload["top_k"],
        )
        return await request_json(
            client,
            "POST",
            f"{JD_API_BASE_URL}/mcp/jiandu/bamboo-slips/search",
            json=payload,
        )
