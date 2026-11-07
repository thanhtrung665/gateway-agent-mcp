"""Remote MCP cho API SOTA Agentic Gateway — ASGI endpoint (Streamable HTTP, stateless, trả JSON).

SaaS gắn vào app của mình (`app/saas/mcp_remote.py` của repo `agentic-gateway-saas`):

    from starlette.routing import Route
    from agw_remote_mcp import RemoteMCP
    app.router.routes.append(Route("/mcp", endpoint=RemoteMCP(accept_token=looks_like_api_key),
                                   methods=["GET", "POST", "DELETE"]))

- Công cụ = `agw_core.saas_tools` (cùng định nghĩa với MCP cục bộ của plugin).
- Mỗi công cụ gọi lại REST `{api_prefix}/*` của CHÍNH app đang phục vụ (`scope["app"]`, ASGI — không ra mạng) bằng đúng
  token của người gọi → mọi lớp kiểm (tenant, vai trò, gói, giới hạn tốc độ, audit, HITL) nằm ở API, không lặp ở đây.
- Stateless: mỗi request dựng server + session manager riêng (hợp serverless, hàm ≤ 60 s). Token nằm trong closure của
  request — không có trạng thái chung giữa các request.
- Trước khi phục vụ: `accept_token(token)` (lọc dạng token, vd chỉ API key) rồi `GET {me_path}` phải 200; lỗi → trả
  nguyên mã (401 kèm `WWW-Authenticate`, 402 gói, 403, 429 kèm `Retry-After`).
- Không có công cụ duyệt; công cụ cần elicitation (`saas_run_playbook`) không có ở remote.

Cần extra `remote` (`mcp>=2.3,<3`, kéo theo `httpx2`, `starlette`).
"""
from __future__ import annotations

import functools
import json
import logging
from collections.abc import Callable
from typing import Any

import httpx2
from mcp.server.mcpserver import MCPServer
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import ToolAnnotations

from agw_core import saas_tools

__all__ = ["RemoteMCP", "build_server", "VERSION"]

VERSION = "0.2.0"
INTERNAL_BASE = "http://agw-internal"  # ASGITransport — không phân giải DNS, không ra mạng
USER_AGENT = f"agw-remote-mcp/{VERSION}"
_RO = ToolAnnotations(read_only_hint=True, open_world_hint=True)
_REQ = ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=True)
_WWW_AUTH = (b"www-authenticate", b'Bearer realm="sota-agentic-gateway"')

log = logging.getLogger(__name__)
# Mỗi request dựng 1 session manager → SDK log "started/shutting down" 2 dòng INFO mỗi lần gọi: hạ xuống WARNING
logging.getLogger("mcp.server.streamable_http_manager").setLevel(logging.WARNING)


def _bearer(scope: dict[str, Any]) -> str:
    for k, v in scope.get("headers") or []:
        if k == b"authorization":
            val = v.decode("latin-1").strip()
            return val[7:].strip() if val[:7].lower() == "bearer " else ""
    return ""


async def _reply(send: Any, status: int, detail: str, headers: list[tuple[bytes, bytes]] | None = None) -> None:
    body = json.dumps({"detail": detail}, ensure_ascii=False).encode("utf-8")
    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", b"application/json; charset=utf-8"),
                            (b"content-length", str(len(body)).encode()), *(headers or [])]})
    await send({"type": "http.response.body", "body": body})


def _guard(fn: Any) -> Any:
    """Lỗi REST → thông báo cho model (không lộ traceback)."""
    @functools.wraps(fn)
    async def w(*a: Any, **kw: Any) -> Any:
        try:
            return await fn(*a, **kw)
        except saas_tools.SaasToolError as e:
            return {"error": str(e)}
    return w


def build_server(http: httpx2.AsyncClient, *, api_prefix: str = "/api/v1") -> MCPServer:
    """MCP server với công cụ SaaS; `http` = client đã gắn token + transport tới API."""
    async def call(method: str, path: str, *, params: dict | None = None, body: dict | None = None) -> Any:
        try:
            r = await http.request(method, f"{api_prefix}{path}", params=params, json=body)
        except Exception as e:  # lỗi trong app (không phải HTTP 4xx/5xx) — không lộ chi tiết cho model
            log.exception("remote MCP: lỗi khi gọi %s %s", method, path)
            raise saas_tools.SaasToolError("Lỗi máy chủ SOTA Agentic Gateway — thử lại sau") from e
        try:
            data = r.json() if r.content else None
        except ValueError:
            data = None
        return saas_tools.unwrap(r.status_code, data, r.text)

    server = MCPServer(name="sota-agentic-gateway", title="SOTA Agentic Gateway", version=VERSION,
                       instructions=saas_tools.INSTRUCTIONS,
                       description="Workspace SOTA Agentic Gateway: hộp thư hợp nhất, phân tích, tri thức, dữ liệu, "
                                   "template, playbook — gửi luôn qua người duyệt.")
    saas_tools.register(server, call, guard=_guard, ro=_RO, req=_REQ)
    return server


class RemoteMCP:
    """ASGI endpoint `/mcp`. `accept_token`: lọc dạng token được nhận (mặc định: API key `agw_…`)."""

    def __init__(self, *, accept_token: Callable[[str], bool] | None = None, api_prefix: str = "/api/v1",
                 me_path: str = "/api/v1/me") -> None:
        self.accept_token = accept_token or (lambda t: t.startswith("agw_") and t.count("_") >= 2)
        self.api_prefix = api_prefix
        self.me_path = me_path

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            return
        token = _bearer(scope)
        if not token or not self.accept_token(token):
            await _reply(send, 401, "Cần API key SOTA Agentic Gateway (Cài đặt → API key) trong header "
                                    "Authorization: Bearer agw_…", [_WWW_AUTH])
            return
        # Gọi lại chính app đang phục vụ (scope["app"]) → cùng middleware, cùng dependency override khi test
        transport = httpx2.ASGITransport(app=scope["app"])
        async with httpx2.AsyncClient(transport=transport, base_url=INTERNAL_BASE, timeout=60,
                                      headers={"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT}) as http:
            me = await http.get(self.me_path)  # key hợp lệ? workspace hoạt động? gói có API? giới hạn tốc độ?
            if me.status_code != 200:
                try:
                    detail = str(me.json().get("detail") or me.reason_phrase)
                except (ValueError, AttributeError):
                    detail = me.reason_phrase
                extra = [_WWW_AUTH] if me.status_code == 401 else []
                if me.status_code == 429:
                    extra.append((b"retry-after", me.headers.get("retry-after", "10").encode()))
                await _reply(send, me.status_code, detail, extra)
                return
            manager = StreamableHTTPSessionManager(app=build_server(http, api_prefix=self.api_prefix)._lowlevel_server,
                                                   stateless=True, json_response=True)
            async with manager.run():
                await manager.handle_request(scope, receive, send)
