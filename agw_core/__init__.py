"""SOTA Agentic Gateway — lõi dùng chung (thuần Python, không DB / không cấu hình nền tảng).

Bản GỐC nằm ở repo `gateway-agent-mcp` (thư mục này). Dùng bởi:
- SaaS `agentic-gateway-saas` (`app/saas/`) — cài gói `sota-agw-mcp` từ repo này (git dependency, ghim commit);
- remote MCP `agw_remote_mcp` (công cụ SaaS ở `saas_tools.py`);
- MCP server của Claude Plugin — `plugin/sota-agentic-gateway/server/agw_core/` là BẢN SAO (plugin chạy độc lập bằng
  `uv run --script`), đồng bộ bằng `python scripts/sync_plugin_core.py`; test + CI kiểm hai bản giống hệt nhau.
"""
__version__ = "0.10.0"
