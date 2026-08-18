from typing import Optional

from fastmcp import Context, FastMCP

from mcp_server.logger import log
from mcp_server.server_config import JD_TRAIN_BASE_URL, MCP_MEDIA_HTTP_TIMEOUT

GROUP_NAME = "media"


def register_media_tools(mcp: FastMCP):
    """注册图片字形检索工具；MCP 负责串联 jd_train 和 jd_media。"""

    @mcp.tool(name=f"{GROUP_NAME}_rare_character_search")
    async def rare_character_search(
        project_id: int,
        image_url: str,
        top_k: int = 5,
        min_similarity: Optional[float] = None,
        ctx: Context = None,
    ) -> dict:
        """使用指定项目的单字模型检索生僻字候选。

        返回结构：检索结果对象（data 字段）：
        - scope: 固定 rare_char
        - project_id: 项目 ID
        - character_version_id: 单字模型版本 ID
        - vector_version: 向量版本标识（character:版本ID:版本号）
        - items: 候选数组，每条含 img_id（字图 ID）、source（图片地址）、attach_name（附件名）、
          business_id（业务 ID）、description（释义/描述）、project_id、char（对应字符）、
          structure_id/structure_name（结构信息）、readable（可读性）、annotation_id（标注 ID）、
          vector_version、metadata（扩展元数据）、similarity（字形相似度 0~1）

        Args:
            project_id: 提供单字 embedding 模型的 jd_train 项目 ID。
            image_url: 待检索字图可访问的 HTTP/HTTPS 地址。
            top_k: 返回候选数量，默认 5。
            min_similarity: 可选余弦相似度下限，仅用于候选筛选，不是认字置信度。
            ctx: MCP 运行上下文，由框架注入。
        """
        if not isinstance(image_url, str) or not image_url.startswith(
            ("http://", "https://")
        ):
            raise ValueError("image_url 必须是可访问的 HTTP/HTTPS 地址")
        client = ctx.request_context.lifespan_context["http_client"]
        url = f"{JD_TRAIN_BASE_URL}/api/project/{project_id}/rare-characters/search"
        log.info(
            "rare_character_search project_id=%s image_url=%s top_k=%s",
            project_id,
            image_url,
            top_k,
        )
        response = await client.post(
            url,
            json={
                "image_url": image_url,
                "top_k": top_k,
                "min_similarity": min_similarity,
            },
            timeout=MCP_MEDIA_HTTP_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()

    @mcp.tool(name=f"{GROUP_NAME}_low_frequency_search")
    async def low_frequency_search(
        project_id: int,
        image_url: str,
        top_k: int = 5,
        min_similarity: Optional[float] = None,
        ctx: Context = None,
    ) -> dict:
        """使用指定项目的单字模型检索低频字候选。

        返回结构：检索结果对象（data 字段）：
        - scope: 固定 low_frequency
        - project_id: 项目 ID
        - character_version_id: 单字模型版本 ID
        - vector_version: 向量版本标识（character:版本ID:版本号）
        - items: 候选数组，每条含 img_id（字图 ID）、source（图片地址）、attach_name（附件名）、
          business_id（业务 ID）、description（释义/描述）、project_id、char（对应字符）、
          structure_id/structure_name（结构信息）、readable（可读性）、annotation_id（标注 ID）、
          vector_version、metadata（扩展元数据）、similarity（字形相似度 0~1）

        Args:
            project_id: 提供单字 embedding 模型的 jd_train 项目 ID。
            image_url: 待检索字图可访问的 HTTP/HTTPS 地址。
            top_k: 返回候选数量，默认 5。
            min_similarity: 可选余弦相似度下限，仅用于候选筛选，不是认字置信度。
            ctx: MCP 运行上下文，由框架注入。
        """
        if not isinstance(image_url, str) or not image_url.startswith(
            ("http://", "https://")
        ):
            raise ValueError("image_url 必须是可访问的 HTTP/HTTPS 地址")
        client = ctx.request_context.lifespan_context["http_client"]
        url = f"{JD_TRAIN_BASE_URL}/api/project/{project_id}/low-frequency-characters/search"
        log.info(
            "low_frequency_search project_id=%s image_url=%s top_k=%s",
            project_id,
            image_url,
            top_k,
        )
        response = await client.post(
            url,
            json={
                "image_url": image_url,
                "top_k": top_k,
                "min_similarity": min_similarity,
            },
            timeout=MCP_MEDIA_HTTP_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
