from typing import Optional
from fastmcp import FastMCP, Context
from mcp_server.server_config import JD_LITERATURE_BASE_URL
from mcp_server.tools.common import request_json

GROUP_NAME = "literature"
ATTACHMENT_GROUP_NAME = "attachment"


def register_literature_tools(mcp: FastMCP):
    """注册简牍文献同步、切分、检索和原文读取工具。"""

    @mcp.tool(name=f"{GROUP_NAME}_search")
    async def literature_search(
        query: str,
        top_k: int = 5,
        min_similarity: Optional[float] = None,
        knowledge_id: Optional[str] = None,
        ctx: Context = None,
    ) -> dict:
        """检索简牍文献相关文本片段。

        Args:
            query: 用户要查找的文献问题、关键词或待核验观点。
            top_k: 返回片段数量，范围 1-50，默认返回 5 条。
            min_similarity: 可选的相似度下限，范围 0-1；不传则使用服务默认值。
            knowledge_id: 可选知识库 ID，只在指定知识库中检索。
            ctx: MCP 运行上下文，由框架注入，不需要调用方传入。

        Returns:
            包含检索片段、来源、业务文档 ID和相似度的结果对象。
        """
        client = ctx.request_context.lifespan_context["http_client"]
        payload = {
            "query": query,
            "top_k": top_k,
            "min_similarity": min_similarity,
            "knowledge_id": knowledge_id,
        }
        return await request_json(
            client,
            "POST",
            f"{JD_LITERATURE_BASE_URL}/api/literature/search",
            json=payload,
        )

    @mcp.tool(name=f"{GROUP_NAME}_split")
    async def literature_split(
        url: str,
        business_id: Optional[str] = None,
        attach_name: Optional[str] = None,
        ctx: Context = None,
    ) -> dict:
        """解析网络文献并返回文本块，不写入向量库。

        Args:
            url: MCP/jd_literature 服务可访问的 HTTP/HTTPS 文档地址。
            business_id: 可选业务文档 ID，用于结果关联；不传时由服务生成。
            attach_name: 可选文件名，影响 PDF、DOCX 等格式识别。
            ctx: MCP 运行上下文，由框架注入。

        Returns:
            OCR/文本解析后的文本块列表和块数量。
        """
        client = ctx.request_context.lifespan_context["http_client"]
        payload = {
            "files": [
                {"url": url, "business_id": business_id, "attach_name": attach_name}
            ]
        }
        return await request_json(
            client,
            "POST",
            f"{JD_LITERATURE_BASE_URL}/api/literature/split",
            json=payload,
        )

    @mcp.tool(name=f"{ATTACHMENT_GROUP_NAME}_index_build")
    async def attachment_index_build(
        user_id: str,
        thread_id: str,
        url: str,
        name: str,
        attach_id: str,
        force: bool = False,
        ctx: Context = None,
    ) -> dict:
        """为当前聊天附件建立会话级向量索引。

        Args:
            user_id: 聊天用户 ID，用于数据隔离。
            thread_id: 聊天会话 ID，用于数据隔离。
            url: 附件在线地址url,可通过HTTP/HTTPS访问
            name: 附件名称
            attach_id: 可选附件 ID。
            force: 是否覆盖已有索引。
            ctx: MCP 运行上下文，由框架注入。

        Returns:
            包含 indexed、already_indexed、attach_id、file_name 和 chunks 的结果对象。
        """
        client = ctx.request_context.lifespan_context["http_client"]
        return await request_json(
            client,
            "POST",
            f"{JD_LITERATURE_BASE_URL}/api/literature/attachments/index",
            json={
                "user_id": user_id,
                "thread_id": thread_id,
                "attachment": {
                    "url": url,
                    "name": name,
                    "attach_id": attach_id,
                },
                "force": force,
            },
        )

    @mcp.tool(name=f"{ATTACHMENT_GROUP_NAME}_search")
    async def attachment_search(
        user_id: str,
        thread_id: str,
        query: str,
        attach_id: Optional[str] = None,
        attachment_name: Optional[str] = None,
        top_k: int = 6,
        min_similarity: Optional[float] = None,
        ctx: Context = None,
    ) -> dict:
        """检索当前聊天附件的文本片段。

        Args:
            user_id: 当前聊天用户 ID，必须与建立索引时一致。
            thread_id: 当前聊天会话 ID，必须与建立索引时一致。
            query: 根据用户问题重写后的附件检索语句。
            attach_id: 可选附件 ID，不传时检索当前会话全部附件。
            attachment_name: 可选附件名称，仅用于辅助定位附件。
            top_k: 返回片段数量，范围 1-20。
            min_similarity: 可选相似度下限。
            ctx: MCP 运行上下文，由框架注入。

        Returns:
            包含命中文本、附件名称、chunk 序号和相似度的结果对象。
        """
        client = ctx.request_context.lifespan_context["http_client"]
        return await request_json(
            client,
            "POST",
            f"{JD_LITERATURE_BASE_URL}/api/literature/attachments/search",
            json={
                "user_id": user_id,
                "thread_id": thread_id,
                "query": query,
                "attach_id": attach_id,
                "attachment_name": attachment_name,
                "top_k": top_k,
                "min_similarity": min_similarity,
            },
        )

    @mcp.tool(name=f"{ATTACHMENT_GROUP_NAME}_summary_pack")
    async def attachment_summary_pack(
        user_id: str,
        thread_id: str,
        attach_id: Optional[str] = None,
        max_chars: int = 12000,
        chunk_limit: int = 80,
        ctx: Context = None,
    ) -> dict:
        """按原始顺序读取会话附件文本块，供摘要和问答使用。

        Args:
            user_id: 当前聊天用户 ID。
            thread_id: 当前聊天会话 ID。
            attach_id: 可选附件 ID。
            max_chars: 返回文本最大字符数，范围 100-50000。
            chunk_limit: 最多返回的文本块数量，范围 1-500。
            ctx: MCP 运行上下文，由框架注入。

        Returns:
            按 chunk 顺序排列的附件文本和 truncated 状态。
        """
        client = ctx.request_context.lifespan_context["http_client"]
        return await request_json(
            client,
            "POST",
            f"{JD_LITERATURE_BASE_URL}/api/literature/attachments/summary",
            json={
                "user_id": user_id,
                "thread_id": thread_id,
                "attach_id": attach_id,
                "max_chars": max_chars,
                "chunk_limit": chunk_limit,
            },
        )
