# 简牍 MCP 中台

参考 `ERP_OPENCLAW/src/mcp_server`，使用 FastMCP、lifespan 共享 `httpx.AsyncClient` 和分组工具注册。

工具分组：

```text
literature_search
literature_fetch
literature_split
media_rare_character_search
media_low_frequency_search(project_id, image_url)
ocr_pipeline_infer
```

启动：

```bash
python app.py
```
