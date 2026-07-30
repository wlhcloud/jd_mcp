from typing import Optional

from fastmcp import Context, FastMCP

from mcp_server.logger import log
from mcp_server.server_config import JD_TRAIN_BASE_URL, JD_TRAIN_VECTOR_API_KEY

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

        Args:
            project_id: 提供单字 embedding 模型的 jd_train 项目 ID。
            image_url: 待检索字图可访问的 HTTP/HTTPS 地址。
            top_k: 返回候选数量，默认 5。
            min_similarity: 可选余弦相似度下限，仅用于候选筛选，不是认字置信度。
            ctx: MCP 运行上下文，由框架注入。

        Returns:
            生僻字候选、业务元数据、字形相似度和向量版本。
        """
        if not isinstance(image_url, str) or not image_url.startswith(("http://", "https://")):
            raise ValueError("image_url 必须是可访问的 HTTP/HTTPS 地址")
        client = ctx.request_context.lifespan_context["http_client"]
        url = f"{JD_TRAIN_BASE_URL}/api/project/{project_id}/rare-characters/search"
        log.info("rare_character_search project_id=%s image_url=%s top_k=%s", project_id, image_url, top_k)
        response = await client.post(
            url,
            json={"image_url": image_url, "top_k": top_k, "min_similarity": min_similarity},
            headers={"X-API-Key": JD_TRAIN_VECTOR_API_KEY},
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

        Args:
            project_id: 提供单字 embedding 模型的 jd_train 项目 ID。
            image_url: 待检索字图可访问的 HTTP/HTTPS 地址。
            top_k: 返回候选数量，默认 5。
            min_similarity: 可选余弦相似度下限，仅用于候选筛选，不是认字置信度。
            ctx: MCP 运行上下文，由框架注入。

        Returns:
            低频字候选、业务元数据、字形相似度和向量版本。
        """
        if not isinstance(image_url, str) or not image_url.startswith(("http://", "https://")):
            raise ValueError("image_url 必须是可访问的 HTTP/HTTPS 地址")
        client = ctx.request_context.lifespan_context["http_client"]
        url = f"{JD_TRAIN_BASE_URL}/api/project/{project_id}/low-frequency-characters/search"
        log.info("low_frequency_search project_id=%s image_url=%s top_k=%s", project_id, image_url, top_k)
        response = await client.post(
            url,
            json={"image_url": image_url, "top_k": top_k, "min_similarity": min_similarity},
            headers={"X-API-Key": JD_TRAIN_VECTOR_API_KEY},
        )
        response.raise_for_status()
        return response.json()
