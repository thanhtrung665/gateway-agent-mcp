# CLAUDE.md — gateway-agent-mcp (SOTA Agentic Gateway: MCP & Claude plugin)

Repo tách từ `agentic-gateway-saas` (2026-11-07). Repo này **public** — không bao giờ commit secrets (`.env`, key, token,
dữ liệu khách). Kế hoạch / nhật ký chung vẫn ở repo SaaS (`SPEC.md` §S.1, `PROGRESS.md`).

## Cấu trúc
- `agw_core/` — **bản gốc** lõi dùng chung (SaaS cài qua git dependency; plugin mang bản chép). Thuần Python, thư viện
  ngoài chỉ import lười. Công cụ SaaS định nghĩa **một lần** ở `agw_core/saas_tools.py` — plugin và remote cùng dùng.
- `agw_remote_mcp/` — remote MCP (ASGI). Không chứa logic nghiệp vụ: công cụ gọi lại REST của API đang phục vụ
  (`scope["app"]`) bằng token người gọi; mọi lớp kiểm (tenant, vai trò, gói, rate limit, audit, HITL) ở API.
- `plugin/sota-agentic-gateway/` — Claude plugin; `server/agw_mcp.py` chạy bằng `uv run --script` (phụ thuộc khai báo
  PEP 723 trong file), `server/agw_core/` là bản chép.

## Quy tắc
- Sửa `agw_core/` → `python -X utf8 scripts/sync_plugin_core.py` (test + CI kiểm đồng bộ).
- Bất biến HITL: không công cụ nào tự gửi / ghi ra ngoài; không có công cụ duyệt (API key không duyệt). MCP cục bộ:
  gửi chỉ sau `Resolve(...)` + `Elicit`; file chỉ trong `AGW_WORKDIR`; IMAP chỉ đọc. Remote: gửi = tạo yêu cầu duyệt.
- Công cụ cần elicitation chỉ có ở MCP cục bộ (remote stateless không hỏi người dùng được).
- Đổi phiên bản plugin: `plugin.json` + `marketplace.json` + `VERSION` trong `agw_mcp.py` (test kiểm khớp);
  `claude plugin validate plugin/sota-agentic-gateway` + `claude plugin validate .`.
- Trước commit: `uv run pytest -q`, `uv run ruff check .`, `scripts/sync_plugin_core.py --check`.
- Sau khi push thay đổi `agw_core` / `agw_remote_mcp`: cập nhật commit ghim ở repo SaaS (`saas/pyproject.toml`) + chạy
  test SaaS (`test_saas_mcp`, `test_saas_platform`…).
- Windows: chạy Python với `-X utf8` (console cp1258).
