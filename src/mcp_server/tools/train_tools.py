from typing import Optional
from fastmcp import FastMCP, Context
from mcp_server.server_config import JD_TRAIN_BASE_URL, JD_TRAIN_API_KEY
from mcp_server.tools.common import request_json

GROUP_NAME = "ocr"


def register_train_tools(mcp: FastMCP):
    """注册 jd_train 的 OCR Pipeline 推理工具。"""

    @mcp.tool(name=f"{GROUP_NAME}_pipeline_infer")
    async def ocr_pipeline_infer(
        project_id: int,
        image_url: str,
        filename: str = "image.jpg",
        include_crops: bool = False,
        ctx: Context = None,
    ) -> dict:
        """调用已发布 OCR Pipeline，对简牍图片执行检测、识别和候选融合。

        Args:
            project_id: jd_train 项目 ID，默认 4。
            image_url: 图片可访问的 HTTP/HTTPS 地址；jd_train 将从该地址下载图片。
            filename: 原始图片文件名，用于识别图片格式，默认 image.jpg。
            include_crops: 是否在结果中返回字框裁剪图，默认 False。
            ctx: MCP 运行上下文，由框架注入。

        Returns:
            检测框、每个字框的 crop_url、单字识别、可读性、结构和向量候选等 OCR 结果。
        """
        client = ctx.request_context.lifespan_context["http_client"]
        payload = {
            "image_url": image_url,
            "filename": filename,
            "include_crops": include_crops,
        }
        response = await client.post(
            f"{JD_TRAIN_BASE_URL}/api/project/{project_id}/ocr/detect",
            json=payload,
            headers={"X-API-Key": JD_TRAIN_API_KEY},
        )
        response.raise_for_status()
        return response.json()
