"""Kiểm gói đã cài như client MCP thật: khởi động server qua stdio, liệt kê công cụ, gọi 1 công cụ chỉ đọc.

    python scripts/smoke_stdio.py <lệnh> [tham số…]
    # vd: python scripts/smoke_stdio.py uvx --from dist/sota_agw_mcp-0.9.0-py3-none-any.whl sota-agw-mcp

Không cần IMAP / SaaS: AGW_WORKDIR là thư mục tạm, không đặt AGW_API_* → chỉ có công cụ cục bộ, không có công cụ SaaS.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile


async def run(command: str, args: list[str]) -> None:
    from mcp import Client, StdioServerParameters

    env = {k: v for k, v in os.environ.items() if not k.startswith(("AGW_", "CLAUDE_PLUGIN_OPTION_"))}
    env["AGW_WORKDIR"] = tempfile.mkdtemp(prefix="agw-smoke-")
    async with Client(StdioServerParameters(command=command, args=args, env=env)) as c:
        names = sorted(t.name for t in (await c.list_tools()).tools)
        assert {"gateway_status", "draft_create", "draft_send", "template_fill", "knowledge_search"} <= set(names), names
        assert not any(n.startswith("saas_") for n in names), "chưa cấu hình SaaS → không có công cụ SaaS"
        assert not any("approve" in n for n in names), "không có công cụ duyệt"
        status = json.loads((await c.call_tool("gateway_status", {})).content[0].text)
        assert os.path.samefile(status["workdir"], env["AGW_WORKDIR"]), status
        print(f"OK: {len(names)} công cụ qua stdio — {', '.join(names)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    asyncio.run(run(sys.argv[1], sys.argv[2:]))
