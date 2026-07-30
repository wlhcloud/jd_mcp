import httpx
from mcp_server.server_config import MCP_API_KEY


def headers():
    return {"Authorization": f"Bearer {MCP_API_KEY}"} if MCP_API_KEY else {}


async def request_json(client: httpx.AsyncClient, method: str, url: str, **kwargs):
    response = await client.request(method, url, headers=headers(), **kwargs)
    response.raise_for_status()
    return response.json()
