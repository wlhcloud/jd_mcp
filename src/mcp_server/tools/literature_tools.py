from typing import Optional
from fastmcp import FastMCP, Context
from mcp_server.logger import log
from mcp_server.server_config import JD_LITERATURE_BASE_URL
from mcp_server.tools.common import request_json

GROUP_NAME = "literature"
ATTACHMENT_GROUP_NAME = "attachment"


def _literature_sources(result: dict) -> list[dict]:
    """将文献检索命中项投影为聊天层可稳定消费的引用结构。"""
    items = result.get("items") or []
    if not isinstance(items, list):
        return []

    sources = []
    seen = set()
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        raw_source = str(item.get("url") or item.get("source") or "").strip()
        source_url = (
            raw_source if raw_source.lower().startswith(("http://", "https://")) else ""
        )
        source_name = item.get("attach_name") or item.get("name") or "未知文献"
        source_id = source_url or source_name
        if source_id in seen:
            continue
        seen.add(source_id)
        sources.append(
            {
                "id": source_id,
                "type": "literature",
                "index": len(sources) + 1,
                "name": source_name,
                "url": source_url,
                "quote": item.get("content") or item.get("quote") or "",
                "similarity": item.get("similarity"),
            }
        )
    return sources


def _public_literature_items(result: dict) -> list[dict]:
    """仅保留回答所需字段：正文、文献名、相似度、来源与图片信息（去掉冗余 metadata_json）。

    index 与 _literature_sources 的来源序号保持一致（同源共享同一 index），
    让模型正文标注的 [n] 与前端参考文献编号一一对应。
    """
    items = result.get("items") or []
    if not isinstance(items, list):
        return []
    index_map = {}
    public = []
    for item in items:
        if not isinstance(item, dict):
            continue
        raw_source = str(item.get("url") or item.get("source") or "").strip()
        source_url = (
            raw_source if raw_source.lower().startswith(("http://", "https://")) else ""
        )
        source_name = item.get("attach_name") or item.get("name") or "未知文献"
        key = source_url or source_name
        if key not in index_map:
            index_map[key] = len(index_map) + 1
        public.append(
            {
                "index": index_map[key],
                "attach_name": source_name,
                "content": item.get("content") or "",
                "source": raw_source,
                "similarity": item.get("similarity"),
                "modality": item.get("modality") or "text",
                "image_url": item.get("image_url") or "",
                "image_path": item.get("image_path") or "",
                "page_no": item.get("page_no"),
            }
        )
    return public


def register_literature_tools(mcp: FastMCP):
    """注册简牍文献同步、切分、检索和原文读取工具。"""

    @mcp.tool(name=f"{GROUP_NAME}_search")
    async def literature_search(
        query: str,
        top_k: int = 5,
        query_image: Optional[str] = None,
        evaluate: bool = False,
        ctx: Context = None,
    ) -> dict:
        """检索简牍文献相关文本片段；支持以图搜图。

        返回结构：检索结果对象：
        - success: 是否成功
        - items: 命中条目列表（无结果时为空数组），每条含 attach_name（文献/附件名）、
          content（命中文本或图片描述）、source（来源文档地址）、similarity（相似度 0~1）、
          modality（text/image）、image_url（图片块的真实图片地址，回答中引用图片时使用）、
          image_path/page_no（图片块页码信息）
        - sources: 标准化引用列表，每条含 id、type（固定 literature）、index（从 1 起的
          引用序号）、name（文献名）、url（来源地址）、quote（引用文本）、similarity

        Args:
            query: 用户要查找的文献问题、关键词或待核验观点；以图搜图时可为空或图片描述。
            top_k: 返回片段数量，范围 1-50，默认返回 5 条。
            min_similarity: 可选相似度下限，范围 0-1，默认不限制（None，由 BM25+向量混合检索自由融合）；
                当前多模态向量模型分数普遍在 0.3~0.8，设置过高（如 0.8）会滤掉全部向量结果、只剩关键词命中。
            query_image: 可选图片 URL，传入时以图搜图（需 jd_literature multimodal 模式）。
            evaluate: 是否附加 RAGAS 质量评估（会额外调用 LLM 生成真实答案，耗时明显），默认 False。
            ctx: MCP 运行上下文，由框架注入，不需要调用方传入。
        """
        client = ctx.request_context.lifespan_context["http_client"]
        payload = {
            "query": query,
            "top_k": top_k,
            "min_similarity": 0.7,
            "knowledge_id": None,  # 目前不支持指定知识库 ID，保留参数以兼容未来扩展
            "evaluate": evaluate,
        }
        if query_image:
            payload["query_image"] = query_image
        log.info(
            "literature_search query=%s... top_k=%s query_image=%s",
            query[:80],
            top_k,
            bool(query_image),
        )
        result = await request_json(
            client,
            "POST",
            f"{JD_LITERATURE_BASE_URL}/api/literature/search",
            json=payload,
        )
        if isinstance(result, dict):
            result["sources"] = _literature_sources(result)
            result["items"] = _public_literature_items(result)
        return result

    @mcp.tool(name=f"{GROUP_NAME}_split")
    async def literature_split(
        url: str,
        business_id: Optional[str] = None,
        attach_name: Optional[str] = None,
        ctx: Context = None,
    ) -> dict:
        """解析网络文献并返回文本块，不写入向量库。

        返回结构：解析结果对象，data 为文档解析数组，每条含：
        - business_id: 业务文档 ID（未传时由服务生成）
        - url: 源文档地址
        - attach_name: 附件名
        - chunks: 文本块数组，每项含 chunk_index（从 0 开始）、content（文本内容）
        - chunk_count: 文本块数量

        Args:
            url: MCP/jd_literature 服务可访问的 HTTP/HTTPS 文档地址。
            business_id: 可选业务文档 ID，用于结果关联；不传时由服务生成。
            attach_name: 可选文件名，影响 PDF、DOCX 等格式识别。
            ctx: MCP 运行上下文，由框架注入。
        """
        client = ctx.request_context.lifespan_context["http_client"]
        payload = {
            "files": [
                {"url": url, "business_id": business_id, "attach_name": attach_name}
            ]
        }
        log.info("literature_split url={} business_id={}", url, business_id)
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

        返回结构：索引构建结果对象，data 为两种形态之一：
        - 已存在且未强制重建：{ indexed: false, reason: "already_indexed", attach_id, file_name }
        - 构建成功：{ indexed: true, attach_id, file_name, chunks: 文本块数 }

        Args:
            user_id: 聊天用户 ID，用于数据隔离。
            thread_id: 聊天会话 ID，用于数据隔离。
            url: 附件在线地址url,可通过HTTP/HTTPS访问
            name: 附件名称
            attach_id: 可选附件 ID。
            force: 是否覆盖已有索引。
            ctx: MCP 运行上下文，由框架注入。
        """
        client = ctx.request_context.lifespan_context["http_client"]
        log.info(
            "attachment_index_build user_id=%s thread_id=%s name=%s attach_id=%s force=%s",
            user_id,
            thread_id,
            name,
            attach_id,
            force,
        )
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

        返回结构：检索结果对象，data 为命中片段数组，每条含：
        - text_id: 文本块标识（user:thread:attach:序号）
        - attach_id: 附件 ID
        - file_name: 附件名称
        - chunk_index: 文本块序号
        - content: 命中文本片段
        - metadata: 元数据（含 url 等）
        - similarity: 相似度 0~1

        Args:
            user_id: 当前聊天用户 ID，必须与建立索引时一致。
            thread_id: 当前聊天会话 ID，必须与建立索引时一致。
            query: 根据用户问题重写后的附件检索语句。
            attach_id: 可选附件 ID，不传时检索当前会话全部附件。
            attachment_name: 可选附件名称，仅用于辅助定位附件。
            top_k: 返回片段数量，范围 1-20。
            min_similarity: 可选相似度下限。
            ctx: MCP 运行上下文，由框架注入。
        """
        client = ctx.request_context.lifespan_context["http_client"]
        log.info(
            "attachment_search user_id=%s thread_id=%s query=%s... top_k=%s",
            user_id,
            thread_id,
            query[:80],
            top_k,
        )
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

        返回结构：汇总结果对象，data 含：
        - user_id / thread_id: 会话标识
        - attach_id: 附件 ID（未过滤时为 null）
        - chunks: 按原始顺序排列的文本块数组，每项含 file_name、attach_id、chunk_index、content
        - truncated: 是否因超过 max_chars 而截断

        Args:
            user_id: 当前聊天用户 ID。
            thread_id: 当前聊天会话 ID。
            attach_id: 可选附件 ID。
            max_chars: 返回文本最大字符数，范围 100-50000。
            chunk_limit: 最多返回的文本块数量，范围 1-500。
            ctx: MCP 运行上下文，由框架注入。
        """
        client = ctx.request_context.lifespan_context["http_client"]
        log.info(
            "attachment_summary_pack user_id=%s thread_id=%s attach_id=%s max_chars=%s",
            user_id,
            thread_id,
            attach_id,
            max_chars,
        )
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
