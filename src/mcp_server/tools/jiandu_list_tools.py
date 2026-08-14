from typing import Annotated, Literal, Optional

from fastmcp import Context, FastMCP
from pydantic import Field

from mcp_server.logger import log
from mcp_server.server_config import JD_API_BASE_URL
from mcp_server.tools.common import request_json

BAMBOO_SLIP_GROUP = "jiandu_bamboo_slip"
INTERPRETATION_GROUP = "jiandu_interpretation"
DIGITAL_ASSET_GROUP = "jiandu_digital_asset"
RARE_CHARACTER_GROUP = "jiandu_rare_character"

QUERY_OPTION_FIELDS = {
    "era": "era",
    "script_type": "scriptType",
    "material_spec": "materialSpec",
    "preservation_status": "preservationStatus",
    "batch_code": "batchCode",
    "chapter_code": "chapterCode",
    "section_code": "sectionCode",
    "secret_level": "secretLevel",
    "status": "status",
}


def _list_payload(page: int, size: int, **filters: Optional[str]) -> dict:
    """Build a domain list request; no advanced-query expression is exposed."""
    if page < 1:
        raise ValueError("page 必须大于 0")
    if not 1 <= size <= 50:
        raise ValueError("size 必须在 1 到 50 之间")
    payload = {"current": page, "size": size}
    for key, raw in filters.items():
        value = str(raw or "").strip()
        if value:
            payload[key] = value
    return payload


def _completed_query(result: dict) -> dict:
    """Mark a list response as terminal so an agent does not search for alternatives."""
    return {
        "query_status": "completed",
        "retry_allowed": False,
        "instruction": "本次结构化查询已完成；空 records 也是最终有效结果，不得修改条件或重试。",
        **result,
    }


def register_jiandu_list_tools(mcp: FastMCP):
    """注册简牍本体、释文、数字资产和生僻字的结构化查询工具。"""

    @mcp.tool(
        name=f"{RARE_CHARACTER_GROUP}_list",
        title="生僻字列表查询",
        tags={RARE_CHARACTER_GROUP, "jiandu_data_query"},
    )
    async def rare_character_list(
        char_code: Annotated[Optional[str], Field(description="生僻字编号，精确匹配，例如 SPZ001。")]=None,
        pinyin: Annotated[Optional[str], Field(description="拼音关键字，模糊匹配。")]=None,
        stroke_order: Annotated[Optional[str], Field(description="笔顺关键字，模糊匹配。")]=None,
        structure: Annotated[Optional[str], Field(description="字形结构关键字，模糊匹配。")]=None,
        stroke_count: Annotated[Optional[str], Field(description="笔画数，精确匹配。")]=None,
        page: Annotated[int, Field(description="页码，从 1 开始。", ge=1)] = 1,
        size: Annotated[int, Field(description="每页条数，范围 1-50。", ge=1, le=50)] = 10,
        ctx: Context = None,
    ) -> dict:
        """分页检索生僻字列表，可组合编号、拼音、笔顺、结构和笔画数条件。

        返回编码、拼音、笔顺、结构、笔画数、备注及图片在线地址。
        如果用户明确给出生僻字编号并只需单条详情，优先调用
        jiandu_rare_character_detail。
        """
        payload = _list_payload(
            page, size, charCode=char_code, charPinyin=pinyin,
            charStrokeOrder=stroke_order, charStructure=structure,
            charStrokeCount=stroke_count,
        )
        log.info("rare_character_list page=%s size=%s filters=%s", page, size, len(payload) - 2)
        client = ctx.request_context.lifespan_context["http_client"]
        result = await request_json(
            client, "POST", f"{JD_API_BASE_URL}/mcp/jiandu/rare-characters/list", json=payload
        )
        return _completed_query(result)

    @mcp.tool(
        name=f"{RARE_CHARACTER_GROUP}_detail",
        title="按编号查询生僻字详情",
        tags={RARE_CHARACTER_GROUP, "jiandu_data_query"},
    )
    async def rare_character_detail(
        char_code: Annotated[str, Field(description="生僻字编号，精确匹配，例如 SPZ001。", min_length=1)],
        ctx: Context = None,
    ) -> dict:
        """根据生僻字编号精确查询单条详情和图片在线地址，不做模糊匹配。"""
        code = str(char_code or "").strip()
        if not code:
            raise ValueError("char_code 不能为空")
        log.info("rare_character_detail char_code=%s", code)
        client = ctx.request_context.lifespan_context["http_client"]
        result = await request_json(
            client,
            "GET",
            f"{JD_API_BASE_URL}/mcp/jiandu/rare-characters/detail",
            params={"charCode": code},
        )
        return {"query_status": "completed", "retry_allowed": False, **result}

    @mcp.tool(
        name="jiandu_query_options",
        title="简牍查询可选值",
        tags={"jiandu_data_query", "query_metadata"},
    )
    async def query_options(
        module: Annotated[
            Literal["bamboo_slip", "interpretation", "digital_asset"],
            Field(description="查询模块：简牍本体、简牍释文或数字资产。"),
        ],
        field: Annotated[
            Optional[Literal[
                "era", "script_type", "material_spec", "preservation_status",
                "batch_code", "chapter_code", "section_code",
                "secret_level", "status",
            ]],
            Field(description="字典字段；不传时返回该模块全部动态选项。"),
        ] = None,
        keyword: Annotated[
            Optional[str],
            Field(description="可选，按字典键或显示名称过滤可选值。"),
        ] = None,
        ctx: Context = None,
    ) -> dict:
        """查询列表筛选字段当前有效的动态字典值。

        当不确定年代、书体、材质、保存状态、批次、章节、密级或资产状态
        的合法取值时，先调用本工具，再把返回的 value 或 label 传给列表工具。
        """
        payload = {"module": module}
        if field:
            payload["field"] = QUERY_OPTION_FIELDS[field]
        if str(keyword or "").strip():
            payload["keyword"] = str(keyword).strip()
        client = ctx.request_context.lifespan_context["http_client"]
        return await request_json(
            client,
            "POST",
            f"{JD_API_BASE_URL}/mcp/jiandu/query-options",
            json=payload,
        )

    @mcp.tool(
        name=f"{BAMBOO_SLIP_GROUP}_list",
        title="简牍本体列表查询",
        tags={BAMBOO_SLIP_GROUP, "jiandu_data_query"},
    )
    async def bamboo_slip_list(
        slip_code: Annotated[Optional[str], Field(description="简牍编号，精确匹配。")]=None,
        slip_name: Annotated[Optional[str], Field(description="简牍名称，模糊匹配。")]=None,
        excavation_number: Annotated[Optional[str], Field(description="出版号，精确匹配；API 字段为 excavationNumber。")]=None,
        book_name: Annotated[Optional[str], Field(description="所属书名，模糊匹配。")]=None,
        script_type: Annotated[Optional[str], Field(description="形制类型字典键或显示名称（如简、牍、觚、检），不是隶书等书体；不确定时先调用 jiandu_query_options。")]=None,
        material_spec: Annotated[Optional[str], Field(description="材质规格字典键或显示名称；不确定时先调用 jiandu_query_options。")]=None,
        era: Annotated[Optional[str], Field(description="年代字典键或显示名称（如西汉）；不确定时先调用 jiandu_query_options。")]=None,
        preservation_status: Annotated[Optional[str], Field(description="保存状况字典键或显示名称；不确定时先调用 jiandu_query_options。")]=None,
        basic_info: Annotated[Optional[str], Field(description="基本信息关键字，模糊匹配。")]=None,
        details: Annotated[Optional[str], Field(description="详细信息关键字，模糊匹配。")]=None,
        page: Annotated[int, Field(description="页码，从 1 开始。", ge=1)] = 1,
        size: Annotated[int, Field(description="每页条数，范围 1-50。", ge=1, le=50)] = 10,
        ctx: Context = None,
    ) -> dict:
        """按结构化条件查询简牍本体列表并分页。

        用于“列出、筛选、统计前先查记录”等确定性数据查询。无需图片，
        也不用于根据 OCR 文本寻找最可能本体；后者应使用
        jiandu_bamboo_slip_search。所有非空条件按 AND 组合。每条记录同时返回
        字典键与中文标签（如 scriptType/scriptTypeLabel），并返回
        primaryImageUrl 和 attachments 在线资源，禁止自行拼接附件地址。

        Args:
            slip_code: 简牍编号，精确匹配。
            slip_name: 简牍名称，模糊匹配。
            excavation_number: 出版号，精确匹配。
            book_name: 所属书名，模糊匹配。
            script_type: 形制类型字典键或显示名称，不表示书体。
            material_spec: 材质规格字典键或显示名称。
            era: 年代字典键或显示名称。
            preservation_status: 保存状况字典键或显示名称。
            basic_info: 基本信息关键字，模糊匹配。
            details: 详细信息关键字，模糊匹配。
            page: 页码，从 1 开始。
            size: 每页条数，范围 1-50。
            ctx: MCP 运行上下文，由框架注入。
        """
        payload = _list_payload(
            page, size, slipCode=slip_code, slipName=slip_name,
            excavationNumber=excavation_number, bookName=book_name,
            scriptType=script_type, materialSpec=material_spec, era=era,
            preservationStatus=preservation_status, basicInfo=basic_info,
            details=details,
        )
        log.info("bamboo_slip_list page=%s size=%s filters=%s", page, size, len(payload) - 2)
        client = ctx.request_context.lifespan_context["http_client"]
        result = await request_json(client, "POST", f"{JD_API_BASE_URL}/mcp/jiandu/bamboo-slips/list", json=payload)
        return _completed_query(result)

    @mcp.tool(
        name=f"{INTERPRETATION_GROUP}_list",
        title="简牍释文列表查询",
        tags={INTERPRETATION_GROUP, "jiandu_data_query"},
    )
    async def interpretation_list(
        slip_code: Annotated[Optional[str], Field(description="简牍编号，精确匹配。")]=None,
        total_code: Annotated[Optional[str], Field(description="释文总编号，精确匹配。")]=None,
        slip_name: Annotated[Optional[str], Field(description="简牍名称，模糊匹配。")]=None,
        era: Annotated[Optional[str], Field(description="年代字典键或显示名称；不确定时先调用 jiandu_query_options。")]=None,
        batch_code: Annotated[Optional[str], Field(description="批次字典键或显示名称；不确定时先调用 jiandu_query_options。")]=None,
        chapter_code: Annotated[Optional[str], Field(description="章节字典键或显示名称；不确定时先调用 jiandu_query_options。")]=None,
        section_code: Annotated[Optional[str], Field(description="小节字典键或显示名称；不确定时先调用 jiandu_query_options。")]=None,
        interpretation_content: Annotated[Optional[str], Field(description="释文内容关键字，模糊匹配。")]=None,
        remark: Annotated[Optional[str], Field(description="备注关键字，模糊匹配。")]=None,
        page: Annotated[int, Field(description="页码，从 1 开始。", ge=1)] = 1,
        size: Annotated[int, Field(description="每页条数，范围 1-50。", ge=1, le=50)] = 10,
        ctx: Context = None,
    ) -> dict:
        """按结构化条件查询简牍释文记录并分页。

        用于查询某简号的全部释文或按时代、批次、章节等组合筛选。
        若只需根据 OCR 初步文本召回少量候选，应使用
        jiandu_interpretation_search。所有非空条件按 AND 组合。

        Args:
            slip_code: 简牍编号，精确匹配。
            total_code: 释文总编号，精确匹配。
            slip_name: 简牍名称，模糊匹配。
            era: 年代字典键或显示名称。
            batch_code: 批次字典键或显示名称。
            chapter_code: 章节字典键或显示名称。
            section_code: 小节字典键或显示名称。
            interpretation_content: 释文内容关键字，模糊匹配。
            remark: 备注关键字，模糊匹配。
            page: 页码，从 1 开始。
            size: 每页条数，范围 1-50。
            ctx: MCP 运行上下文，由框架注入。
        """
        payload = _list_payload(
            page, size, slipCode=slip_code, totalCode=total_code,
            slipName=slip_name, era=era, batchCode=batch_code,
            chapterCode=chapter_code, sectionCode=section_code,
            interpretationContent=interpretation_content, remark=remark,
        )
        log.info("interpretation_list page=%s size=%s filters=%s", page, size, len(payload) - 2)
        client = ctx.request_context.lifespan_context["http_client"]
        result = await request_json(client, "POST", f"{JD_API_BASE_URL}/mcp/jiandu/interpretations/list", json=payload)
        return _completed_query(result)

    @mcp.tool(
        name=f"{DIGITAL_ASSET_GROUP}_list",
        title="数字资产列表查询",
        tags={DIGITAL_ASSET_GROUP, "jiandu_data_query"},
    )
    async def digital_asset_list(
        assets_no: Annotated[Optional[str], Field(description="数字资产编号，精确匹配。")]=None,
        assets_name: Annotated[Optional[str], Field(description="数字资产名称，模糊匹配。")]=None,
        secret_level: Annotated[Optional[str], Field(description="密级字典键或显示名称；不确定时先调用 jiandu_query_options。")]=None,
        author: Annotated[Optional[str], Field(description="作者名称，模糊匹配。")]=None,
        handlemen: Annotated[Optional[str], Field(description="经手人名称，模糊匹配；字段名沿用业务接口 handlemen。")]=None,
        characters: Annotated[Optional[str], Field(description="资产文字内容关键字，模糊匹配。")]=None,
        status: Annotated[Optional[str], Field(description="资产状态字典键或显示名称；不确定时先调用 jiandu_query_options。")]=None,
        page: Annotated[int, Field(description="页码，从 1 开始。", ge=1)] = 1,
        size: Annotated[int, Field(description="每页条数，范围 1-50。", ge=1, le=50)] = 10,
        ctx: Context = None,
    ) -> dict:
        """按编号、名称、密级、作者、经手人、文字或状态查询数字资产。

        用于精确的结构化资产筛选和分页；宽泛的跨字段关键词召回应使用
        collection_search。所有非空条件按 AND 组合。每条记录同时返回
        secretLevelLabel、statusLabel 中文标签；realpath 保留原始附件路径，
        address 返回已拼接 FILE_ACCESS_NET_PREFIX 的在线地址，禁止自行拼接。

        Args:
            assets_no: 数字资产编号，精确匹配。
            assets_name: 数字资产名称，模糊匹配。
            secret_level: 密级字典键或显示名称。
            author: 作者名称，模糊匹配。
            handlemen: 经手人名称，字段名沿用业务接口 handlemen。
            characters: 资产文字内容关键字，模糊匹配。
            status: 资产状态字典键或显示名称。
            page: 页码，从 1 开始。
            size: 每页条数，范围 1-50。
            ctx: MCP 运行上下文，由框架注入。
        """
        payload = _list_payload(
            page, size, assetsNo=assets_no, assetsName=assets_name,
            secretLevel=secret_level, author=author, handlemen=handlemen,
            characters=characters, status=status,
        )
        log.info("digital_asset_list page=%s size=%s filters=%s", page, size, len(payload) - 2)
        client = ctx.request_context.lifespan_context["http_client"]
        result = await request_json(client, "POST", f"{JD_API_BASE_URL}/mcp/jiandu/digital-assets/list", json=payload)
        return _completed_query(result)
