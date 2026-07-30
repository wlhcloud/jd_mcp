import os

MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.getenv("MCP_PORT", "5603"))
MCP_PATH = os.getenv("MCP_PATH", "/mcp")
JD_LITERATURE_BASE_URL = os.getenv("JD_LITERATURE_BASE_URL", "http://127.0.0.1:5602")
JD_MEDIA_BASE_URL = os.getenv("JD_MEDIA_BASE_URL", "http://127.0.0.1:5601")
JD_TRAIN_BASE_URL = os.getenv("JD_TRAIN_BASE_URL", "http://127.0.0.1:5500")
JD_TRAIN_API_KEY = os.getenv("JD_TRAIN_API_KEY", "")
JD_TRAIN_VECTOR_API_KEY = os.getenv("JD_TRAIN_VECTOR_API_KEY", "")
MCP_HTTP_TIMEOUT = float(os.getenv("MCP_HTTP_TIMEOUT", "120"))
MCP_API_KEY = os.getenv("MCP_API_KEY", "")
