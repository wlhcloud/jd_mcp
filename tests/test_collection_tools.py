import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from mcp_server.tools.collection_tools import register_collection_tools


class _McpStub:
    def __init__(self):
        self.tool_fn = None

    def tool(self, **_kwargs):
        def decorator(fn):
            self.tool_fn = fn
            return fn

        return decorator


class CollectionSearchProxyTest(unittest.IsolatedAsyncioTestCase):
    async def test_collection_search_uses_jd_api_proxy(self):
        mcp = _McpStub()
        register_collection_tools(mcp)
        client = object()
        ctx = SimpleNamespace(
            request_context=SimpleNamespace(lifespan_context={"http_client": client})
        )
        proxy_response = {
            "code": 200,
            "data": {
                "total": 1,
                "pageTotal": 1,
                "list": [{"title": "馆藏记录"}],
            },
        }
        request = AsyncMock(return_value=proxy_response)

        with patch("mcp_server.tools.collection_tools.request_json", new=request):
            result = await mcp.tool_fn("馆藏", page=2, size=20, ctx=ctx)

        args, kwargs = request.await_args
        self.assertEqual(args[1], "POST")
        self.assertTrue(args[2].endswith("/mcp/collection/fulltext-search"))
        self.assertEqual(
            kwargs["json"], {"keyword": "馆藏", "page": 2, "size": 20}
        )
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["size"], 20)
        self.assertEqual(result["items"][0]["title"], "馆藏记录")

    async def test_page_and_size_are_clamped(self):
        mcp = _McpStub()
        register_collection_tools(mcp)
        ctx = SimpleNamespace(
            request_context=SimpleNamespace(lifespan_context={"http_client": object()})
        )
        request = AsyncMock(return_value={"code": 200, "data": {"list": []}})

        with patch("mcp_server.tools.collection_tools.request_json", new=request):
            await mcp.tool_fn("文物", page=0, size=999, ctx=ctx)

        self.assertEqual(
            request.await_args.kwargs["json"],
            {"keyword": "文物", "page": 1, "size": 50},
        )


if __name__ == "__main__":
    unittest.main()
