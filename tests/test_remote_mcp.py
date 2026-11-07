"""Test `agw_remote_mcp.RemoteMCP` với 1 API giả (Starlette) — client MCP thật của SDK qua Streamable HTTP, cả giao thức
cũ (initialize) lẫn auto (2026-07-28). Tích hợp với API SaaS thật: `app/tests/test_saas_mcp.py` ở repo SaaS.
"""
from __future__ import annotations

import asyncio
import json
import tempfile

import httpx2
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from agw_remote_mcp import INTERNAL_SCOPE_KEY, RemoteMCP, build_server

KEY, TRIAL_KEY = "agw_acme0001_secret", "agw_trial001_secret"
SHARED_TOOLS = {"saas_inbox_list", "saas_inbox_get", "saas_analyze", "saas_save_reply_draft", "saas_request_reply",
                "saas_approvals", "saas_knowledge_search", "saas_connections", "saas_query", "saas_query_catalog",
                "saas_templates", "saas_fill_template", "saas_playbooks", "saas_dashboard"}
PRM = "http://agw.test/.well-known/oauth-protected-resource/mcp"
SEEN: list[tuple[str, str, str, bool]] = []
IPS: list[tuple[str, str | None]] = []  # (client.host, x-real-ip) API nhìn thấy


def _auth(request: Request) -> Response | None:
    token = request.headers.get("authorization", "")
    SEEN.append((request.method, request.url.path, token, bool(request.scope.get(INTERNAL_SCOPE_KEY))))
    IPS.append((request.client.host if request.client else "", request.headers.get("x-real-ip")))
    if token == f"Bearer {TRIAL_KEY}":
        return JSONResponse({"detail": "Gói hiện tại không gồm truy cập API / MCP"}, 402)
    if token != f"Bearer {KEY}":
        return JSONResponse({"detail": "API key không hợp lệ"}, 401)
    return None


async def me(request: Request):
    return _auth(request) or JSONResponse({"via": "api_key"})


async def inbox(request: Request):
    return _auth(request) or JSONResponse([{"id": "m1", "subject": "RFQ van bi"}])


async def inbox_item(request: Request):
    if err := _auth(request):
        return err
    if request.path_params["item_id"] != "m1":
        return JSONResponse({"detail": "Không tìm thấy"}, 404)
    return JSONResponse({"id": "m1"})


async def reply_requests(request: Request):
    return _auth(request) or JSONResponse({"approval_id": "a1", "status": "PENDING"}, 201)


api = Starlette(routes=[
    Route("/api/v1/me", me),
    Route("/api/v1/inbox", inbox),
    Route("/api/v1/inbox/{item_id}", inbox_item),
    Route("/api/v1/inbox/{item_id}/reply-requests", reply_requests, methods=["POST"]),
    Route("/mcp", endpoint=RemoteMCP(resource_metadata_url=PRM), methods=["GET", "POST", "DELETE"]),
])


def _client(token: str, mode: str = "auto"):
    from mcp import Client
    from mcp.client.streamable_http import streamable_http_client

    http = httpx2.AsyncClient(transport=httpx2.ASGITransport(app=api), base_url="http://agw.test",
                              headers={"Authorization": f"Bearer {token}"}, timeout=60)
    return Client(streamable_http_client("http://agw.test/mcp", http_client=http), mode=mode)


async def _post_mcp(token: str | None) -> httpx2.Response:
    headers = {"content-type": "application/json", "accept": "application/json, text/event-stream"}
    if token is not None:
        headers["authorization"] = f"Bearer {token}"
    async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=api), base_url="http://agw.test") as c:
        return await c.post("/mcp", headers=headers,
                            content=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}))


def _text(result) -> dict:
    return json.loads(result.content[0].text)


def test_auth_is_required_and_api_errors_pass_through():
    async def run():
        r = await _post_mcp(None)
        www = r.headers.get("www-authenticate", "")
        assert r.status_code == 401 and www.lower().startswith("bearer") and f'resource_metadata="{PRM}"' in www, www
        assert "error=" not in www, "chưa gửi token → không kèm error (RFC 6750 §3)"
        r = await _post_mcp("session-token-web")
        assert r.status_code == 401 and 'error="invalid_token"' in r.headers["www-authenticate"], "chỉ nhận dạng API key"
        r = await _post_mcp("agw_unknown1_secret")
        assert r.status_code == 401 and f'resource_metadata="{PRM}"' in r.headers["www-authenticate"], "API 401 → MCP 401"
        r = await _post_mcp(TRIAL_KEY)
        assert r.status_code == 402 and "MCP" in r.json()["detail"], "gói không có API → 402"

    asyncio.run(run())


def test_tools_forward_caller_token_and_hitl_note():
    SEEN.clear()

    async def run(mode: str):
        async with _client(KEY, mode) as c:
            names = {x.name for x in (await c.list_tools()).tools}
            assert names == SHARED_TOOLS, names ^ SHARED_TOOLS
            assert not any("approve" in n or "decide" in n for n in names), "không có công cụ duyệt"
            assert _text(await c.call_tool("saas_inbox_list", {}))["items"][0]["id"] == "m1"
            r = _text(await c.call_tool("saas_request_reply", {"item_id": "m1"}))
            assert r["status"] == "PENDING" and "chưa gửi" in r["note"]
            assert "404" in _text(await c.call_tool("saas_inbox_get", {"item_id": "x"}))["error"]
            assert "không hợp lệ" in _text(await c.call_tool(
                "saas_save_reply_draft", {"item_id": "m1", "body": "x", "to": "khong-hop-le"}))["error"]

    asyncio.run(run("legacy"))
    asyncio.run(run("auto"))
    api_calls = [s for s in SEEN if s[1] != "/api/v1/me"]
    assert api_calls and all(tok == f"Bearer {KEY}" for _, _, tok, _ in api_calls), "mọi lời gọi API mang token người gọi"
    assert all(marked for *_, marked in SEEN), "lời gọi nội bộ mang dấu scope agw.remote_mcp"


def test_remote_and_plugin_share_tool_definitions():
    """Plugin (cục bộ) và remote sinh từ cùng agw_core.saas_tools — cùng tên, mô tả, schema tham số."""
    from mcp import Client

    from tests.test_plugin import load_plugin

    local_server = load_plugin(tempfile.mkdtemp(prefix="agw-mcp-"), AGW_API_URL="http://agw.test",
                               AGW_API_KEY=KEY).build_server()

    async def tools(server):
        async with Client(server) as c:
            return {x.name: x for x in (await c.list_tools()).tools}

    local = asyncio.run(tools(local_server))
    remote = asyncio.run(tools(build_server(httpx2.AsyncClient(base_url="http://unused"))))
    assert set(remote) == SHARED_TOOLS and SHARED_TOOLS | {"saas_run_playbook"} <= set(local)
    for name in SHARED_TOOLS:
        assert local[name].description == remote[name].description, name
        assert local[name].input_schema == remote[name].input_schema, name


def test_internal_calls_keep_caller_address():
    """Rate limit / chống dò theo IP ở API phải thấy IP người gọi /mcp — không phải 1 địa chỉ nội bộ chung."""
    IPS.clear()

    async def run():
        transport = httpx2.ASGITransport(app=api, client=("203.0.113.7", 5000))
        async with httpx2.AsyncClient(transport=transport, base_url="http://agw.test") as c:
            r = await c.post("/mcp", headers={"authorization": f"Bearer {KEY}", "content-type": "application/json",
                                              "accept": "application/json, text/event-stream",
                                              "x-real-ip": "198.51.100.9"},
                             content=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}))
            assert r.status_code == 200, r.text

    asyncio.run(run())
    assert IPS and all(ip == ("203.0.113.7", "198.51.100.9") for ip in IPS), IPS
