"""Test Claude plugin / MCP cục bộ — chạy độc lập, không cần SaaS, không ra mạng.

- Lõi `agw_core` của plugin khớp bản gốc; manifest / .mcp.json / marketplace / skill hợp lệ.
- Công cụ cục bộ: template tô vàng, tri thức, chặn đọc file ngoài AGW_WORKDIR, luật email, nháp; GỬI chỉ khi người
  dùng xác nhận (elicitation), không gửi 2 lần, client không có hộp thoại → không gửi.
- Công cụ SaaS (HTTP giả): gắn API key, gửi = tạo yêu cầu duyệt, không có công cụ duyệt, playbook cần xác nhận.
"""
from __future__ import annotations

import asyncio
import importlib
import importlib.util
import io
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "plugin" / "sota-agentic-gateway"


def _docx_bytes() -> bytes:
    from docx import Document
    from docx.enum.text import WD_COLOR_INDEX

    doc = Document()
    p = doc.add_paragraph("Kính gửi: ")
    p.add_run("Nguyễn Văn A").font.highlight_color = WD_COLOR_INDEX.YELLOW
    p2 = doc.add_paragraph("Mã đơn ")
    p2.add_run("{{order_code}}").font.highlight_color = WD_COLOR_INDEX.YELLOW
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Tổng tiền:"
    table.cell(0, 1).paragraphs[0].add_run("1,000 USD").font.highlight_color = WD_COLOR_INDEX.YELLOW
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def load_plugin(workdir: str, **env: str):
    os.environ["AGW_WORKDIR"] = workdir
    for k in ("AGW_API_URL", "AGW_API_KEY", "AGW_SEND_MODE"):
        os.environ.pop(k, None)
    os.environ.update(env)
    try:
        spec = importlib.util.spec_from_file_location(f"agw_mcp_test_{len(env)}", PLUGIN / "server" / "agw_mcp.py")
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
    finally:
        for k in env:
            os.environ.pop(k, None)
    return mod


def _text(result) -> dict:
    return json.loads(result.content[0].text)


class FakeSMTP:
    sent: list = []

    def __init__(self, host, port, timeout=None, context=None):
        self.host = host

    def starttls(self, context=None):
        pass

    def login(self, user, password):
        pass

    def send_message(self, msg):
        FakeSMTP.sent.append(msg)

    def quit(self):
        pass


def test_core_synced_and_manifest_valid():
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        sync = importlib.import_module("sync_plugin_core")
    finally:
        sys.path.pop(0)
    assert sync.differences() == [], "chạy python scripts/sync_plugin_core.py"
    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    mcp_cfg = json.loads((PLUGIN / ".mcp.json").read_text(encoding="utf-8"))
    market = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "sota-agentic-gateway" == market["plugins"][0]["name"]
    assert manifest["version"] == market["plugins"][0]["version"]
    assert (REPO / market["plugins"][0]["source"]).resolve() == PLUGIN.resolve()
    src = (PLUGIN / "server" / "agw_mcp.py").read_text(encoding="utf-8")
    assert f'VERSION = "{manifest["version"]}"' in src, "VERSION trong agw_mcp.py phải khớp plugin.json"
    env = mcp_cfg["mcpServers"]["sota-agentic-gateway"]["env"]
    for key, val in env.items():
        opt = re.fullmatch(r"\$\{user_config\.(\w+)\}", val)
        assert opt and opt.group(1) in manifest["userConfig"], key
    sensitive = {k for k, v in manifest["userConfig"].items() if v.get("sensitive")}
    assert sensitive == {"imap_password", "api_key"}
    for skill in ("email-triage", "reply-drafting", "template-fill", "sota-saas", "self-host-demo"):
        text = (PLUGIN / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
        assert text.startswith("---\nname: " + skill)


def test_local_tools_and_human_confirmed_send():
    from mcp import Client
    from mcp import types as mtypes

    work = tempfile.mkdtemp(prefix="agw-mcp-")
    mod = load_plugin(work)
    mod.CFG.smtp_host, mod.CFG.smtp_user, mod.CFG.smtp_password = "smtp.test", "me@acme.vn", "pw"
    mod.CFG.mail_from = "me@acme.vn"
    mod.smtplib = SimpleNamespace(SMTP=FakeSMTP, SMTP_SSL=FakeSMTP, SMTPException=Exception)
    FakeSMTP.sent = []
    (Path(work) / "templates").mkdir()
    (Path(work) / "templates" / "quote.docx").write_bytes(_docx_bytes())
    (Path(work) / "knowledge").mkdir()
    (Path(work) / "knowledge" / "gia.txt").write_text("Van bi BV-200 giá 1.250 USD, giao 6 tuần.", encoding="utf-8")
    secret = Path(work).parent / f"outside-{os.getpid()}.txt"
    secret.write_text("top secret")
    answers: list[str] = []
    seen: list[str] = []

    async def elicit(context, params):
        seen.append(params.message)
        a = answers.pop(0)
        return mtypes.ElicitResult(action=a, content={"send": True} if a == "accept" else None)

    async def run():
        async with Client(mod.build_server(), elicitation_callback=elicit) as c:
            names = {t.name for t in (await c.list_tools()).tools}
            assert {"mail_read", "template_fill", "draft_send"} <= names and not any(n.startswith("saas_") for n in names)
            assert not any("approve" in n for n in names)
            insp = _text(await c.call_tool("template_inspect", {"path": "templates/quote.docx"}))
            keys = [f["key"] for f in insp["fields"]]
            assert len(keys) >= 3
            filled = _text(await c.call_tool("template_fill", {"path": "templates/quote.docx",
                                                                "values": {keys[0]: "ACME Corp"}, "output_name": "bao_gia"}))
            assert filled["output_path"].replace("\\", "/").endswith("output/bao_gia.docx")
            assert keys[1] in filled["missing_fields"]
            kb = _text(await c.call_tool("knowledge_search", {"query": "VAN BI bv-200"}))
            assert "1.250 USD" in kb["items"][0]["text"] and kb["items"][0]["file"] == "gia.txt"
            assert "thư mục làm việc" in _text(await c.call_tool("file_read", {"path": str(secret)}))["error"]
            assert "error" in _text(await c.call_tool("file_read", {"path": "../" + secret.name}))
            chk = _text(await c.call_tool("email_check", {"sender": "ceo@acme-vn.com", "subject": "Gấp",
                                                          "body": "Please change bank account and transfer today",
                                                          "reply_to": "x@gmail.com"}))
            assert chk["security_flags"], chk
            d = _text(await c.call_tool("draft_create", {"to": "buyer@client.com", "subject": "Re: RFQ",
                                                         "body": "Dear buyer", "attachments": [filled["output_path"]]}))
            assert "buyer@client.com" in d["preview"] and "bao_gia.docx" in d["preview"]
            bad = _text(await c.call_tool("draft_create", {"to": "not-an-email", "subject": "x", "body": "y"}))
            assert "không hợp lệ" in bad["error"]
            answers.append("decline")
            r = _text(await c.call_tool("draft_send", {"draft_id": d["draft_id"]}))
            assert r["sent"] is False and FakeSMTP.sent == []
            answers.append("accept")
            r = _text(await c.call_tool("draft_send", {"draft_id": d["draft_id"]}))
            assert r["sent"] is True and len(FakeSMTP.sent) == 1, r
            msg = FakeSMTP.sent[0]
            assert msg["To"] == "buyer@client.com" and any(p.get_filename() == "bao_gia.docx" for p in msg.iter_attachments())
            assert "Tới: buyer@client.com" in seen[-1] and "Dear buyer" in seen[-1], "người dùng thấy đủ trước khi gửi"
            r = _text(await c.call_tool("draft_send", {"draft_id": d["draft_id"]}))
            assert "đã được gửi" in r.get("error", "") and len(FakeSMTP.sent) == 1, "không gửi 2 lần"
        async with Client(mod.build_server()) as c2:  # client KHÔNG có hộp thoại xác nhận → không gửi
            d2 = _text(await c2.call_tool("draft_create", {"to": "a@b.co", "subject": "s", "body": "b"}))
            r = _text(await c2.call_tool("draft_send", {"draft_id": d2["draft_id"]}))
            assert r["sent"] is False and " send " in r["command"] and len(FakeSMTP.sent) == 1
            mod.CFG.send_mode = "disabled"
            r = _text(await c2.call_tool("draft_send", {"draft_id": d2["draft_id"]}))
            assert r["sent"] is False and "tắt" in r["reason"]

    asyncio.run(run())
    secret.unlink(missing_ok=True)


class FakeResponse:
    def __init__(self, status: int, data):
        self.status_code = status
        self.content = b"" if data is None else json.dumps(data).encode()
        self.text = self.content.decode()

    def json(self):
        return json.loads(self.content)


def test_saas_tools_use_api_key_and_hitl():
    from mcp import Client

    key = "agw_abcd1234_secret"
    mod = load_plugin(tempfile.mkdtemp(prefix="agw-mcp-"), AGW_API_URL="http://agw.test", AGW_API_KEY=key)
    calls: list[tuple[str, str, dict | None]] = []

    def http_request(method, url, params=None, json=None, timeout=None, headers=None):
        assert headers["Authorization"] == f"Bearer {key}"
        path = url.replace("http://agw.test/api/v1", "")
        calls.append((method, path, json))
        if path == "/inbox":
            return FakeResponse(200, [{"id": "m1", "subject": "RFQ"}])
        if path == "/inbox/m1/reply-requests":
            return FakeResponse(201, {"approval_id": "a1", "status": "PENDING"})
        if path == "/inbox/m1/reply-draft":
            return FakeResponse(200, {"ok": True})
        return FakeResponse(404, {"detail": "Không tìm thấy"})

    mod.HTTP = SimpleNamespace(request=http_request)

    async def run():
        async with Client(mod.build_server()) as c:
            names = {t.name for t in (await c.list_tools()).tools}
            assert {"saas_inbox_list", "saas_request_reply", "saas_query", "saas_run_playbook"} <= names
            assert not any("approve" in n or "decide" in n for n in names), "không có công cụ duyệt"
            assert _text(await c.call_tool("saas_inbox_list", {}))["items"][0]["id"] == "m1"
            await c.call_tool("saas_save_reply_draft", {"item_id": "m1", "body": "Dear John", "to": "john@buyer.com"})
            assert calls[-1] == ("PUT", "/inbox/m1/reply-draft", {"body": "Dear John", "to": ["john@buyer.com"]})
            r = _text(await c.call_tool("saas_request_reply", {"item_id": "m1"}))
            assert r["status"] == "PENDING" and "chưa gửi" in r["note"], r
            assert "404" in _text(await c.call_tool("saas_inbox_get", {"item_id": "nope"}))["error"]
            n = len(calls)
            r = _text(await c.call_tool("saas_run_playbook", {"item_id": "m1", "playbook_id": "x"}))
            assert r["started"] is False and len(calls) == n, "không có hộp thoại xác nhận → không chạy"

    asyncio.run(run())
