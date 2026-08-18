from typing import Optional
from fastmcp import FastMCP, Context
from mcp_server.logger import log
from mcp_server.server_config import JD_TRAIN_BASE_URL, MCP_OCR_HTTP_TIMEOUT
from mcp_server.tools.common import request_json

GROUP_NAME = "ocr"


def register_train_tools(mcp: FastMCP):
    """注册 jd_train 的 OCR Pipeline 推理工具。"""

    @mcp.tool(name="jiandu_annotation_meanings_search")
    async def annotation_meanings_search(
        characters: list[str],
        project_id: int = 4,
        limit_per_character: int = 5,
        ctx: Context = None,
    ) -> dict:
        """批量查询普通汉字在人工素材标注中维护的简牍语境释义。

        返回结构：查询结果对象（data 字段）：
        - items: 标注释义数组，每条含 character（汉字）、meaning（简牍语境释义）、
          annotation_id（标注 ID）、image_id（图片来源 ID）、image_remark（图片备注）、
          project_id、source_type（固定 annotation）
        - meanings: 字典，键为汉字，值为该字释义字符串数组（每字最多 limit_per_character 条）

        Args:
            project_id: jd_train 项目 ID。
            characters: OCR 识别出的普通汉字列表；应先去重，不得传 rare_ 编码。
            limit_per_character: 每个汉字最多返回的不同释义数量，范围 1-20。
            ctx: MCP 运行上下文，由框架注入。
        """
        if not isinstance(characters, list):
            raise ValueError("characters 必须是汉字数组")
        normalized = []
        seen = set()
        for value in characters:
            character = str(value or "").strip()
            if len(character) != 1 or character in seen:
                continue
            seen.add(character)
            normalized.append(character)
        if len(normalized) > 100:
            raise ValueError("单次最多查询 100 个汉字")
        if not 1 <= int(limit_per_character) <= 20:
            raise ValueError("limit_per_character 必须在 1 到 20 之间")

        client = ctx.request_context.lifespan_context["http_client"]
        log.info(
            "annotation_meanings_search project_id=%s characters=%s",
            project_id,
            normalized,
        )
        headers = {}
        return await request_json(
            client,
            "POST",
            f"{JD_TRAIN_BASE_URL}/api/project/{project_id}/annotation-meanings/search",
            json={
                "characters": normalized,
                "limit_per_character": int(limit_per_character),
            },
            headers=headers,
        )

    @mcp.tool(name=f"{GROUP_NAME}_pipeline_infer")
    async def ocr_pipeline_infer(
        image_url: str,
        project_id: int = 4,
        filename: str = "image.jpg",
        include_crops: bool = False,
        ctx: Context = None,
    ) -> dict:
        """调用已发布 OCR Pipeline，对简牍图片执行检测、识别和候选融合。

        返回结构：OCR 推理结果对象：
        - success: 是否成功
        - project_id: 项目 ID
        - pipeline: 模型版本信息，含 version_id、version、detector_version_id、character_version_id、vector_version_id
        - image: 图片信息，含 width、height、result_url（可为 null）
        - detections: 检测框数组，每条含 index（从 1 起）、label/class_name（判定字或“□”残损）、
          class_id、confidence（判定置信度 0~1）、detector_confidence（检框置信度）、
          bbox（[x1,y1,x2,y2] 像素）、x/y/width/height（归一化 0~1）、source（判定来源）、
          is_low_confidence、candidates（融合 Top5，每项含 char/class_id/classifier_score/
          vector_similarity/description/structure_match_score/score/reason）、
          structure（{id,label,confidence}）、readable（{id,label,confidence}）、
          crop_url（字框图地址，include_crops 为 True 时返回）
        - total_count: 检测字总数
        - preliminary_reading: 按阅读顺序拼接的初读文本
        - duration_ms: 推理耗时（毫秒）

        Args:
            project_id: jd_train 项目 ID，默认 4。
            image_url: 图片可访问的 HTTP/HTTPS 地址；jd_train 将从该地址下载图片。
            filename: 原始图片文件名，用于识别图片格式，默认 image.jpg。
            include_crops: 是否在结果中返回字框裁剪图，默认 False。
            ctx: MCP 运行上下文，由框架注入。
        """
        client = ctx.request_context.lifespan_context["http_client"]
        payload = {
            "image_url": image_url,
            "filename": filename,
            "include_crops": include_crops,
        }
        url = f"{JD_TRAIN_BASE_URL}/api/project/{project_id}/ocr/detect"
        log.info(
            "ocr_pipeline_infer project_id=%s image_url=%s include_crops=%s",
            project_id,
            image_url,
            include_crops,
        )
        response = await client.post(
            url,
            json=payload,
            timeout=MCP_OCR_HTTP_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
