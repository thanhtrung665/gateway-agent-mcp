# CLAUDE.md — gateway-agent-mcp (SOTA Agentic Gateway: MCP & Claude plugin)

Repo tách từ `agentic-gateway-saas` (2026-11-07). Repo này **public** — không bao giờ commit secrets (`.env`, key, token,
dữ liệu khách). Kế hoạch / nhật ký chung vẫn ở repo SaaS (`SPEC.md` §S.1, `PROGRESS.md`).

## Cấu trúc
- `agw_core/` — **bản gốc** lõi dùng chung (SaaS cài qua git dependency; plugin mang bản chép). Thuần Python, thư viện
  ngoài chỉ import lười. Công cụ SaaS định nghĩa **một lần** ở `agw_core/saas_tools.py` — plugin và remote cùng dùng.
- `agw_remote_mcp/` — remote MCP (ASGI). Không chứa logic nghiệp vụ: công cụ gọi lại REST của API đang phục vụ
  (`scope["app"]`) bằng token người gọi; mọi lớp kiểm (tenant, vai trò, gói, rate limit, audit, HITL) ở API.
- `agw_mcp/` — MCP server cục bộ (stdio), **nguồn duy nhất** `agw_mcp/server.py`; lệnh `sota-agw-mcp` (gói PyPI).
- `plugin/sota-agentic-gateway/` — Claude plugin; `server/agw_mcp.py` (= bản chép y hệt `agw_mcp/server.py`, chạy bằng
  `uv run --script`, phụ thuộc ở khối `# /// script` đầu file) và `server/agw_core/` là bản chép — KHÔNG sửa tay.

## Quy tắc
- Sửa `agw_core/` hoặc `agw_mcp/server.py` → `python -X utf8 scripts/sync_plugin_core.py` (test + CI kiểm đồng bộ).
- Phụ thuộc của server khai ở 2 nơi phải khớp (test kiểm): `dependencies` trong `pyproject.toml` và khối `# /// script`.
- Bất biến HITL: không công cụ nào tự gửi / ghi ra ngoài; không có công cụ duyệt (API key không duyệt). MCP cục bộ:
  gửi chỉ sau `Resolve(...)` + `Elicit`; file chỉ trong `AGW_WORKDIR`; IMAP chỉ đọc. Remote: gửi = tạo yêu cầu duyệt.
- Công cụ cần elicitation chỉ có ở MCP cục bộ (remote stateless không hỏi người dùng được).
- **Một số phiên bản** cho cả repo — đổi cùng lúc 5 chỗ (test kiểm): `pyproject.toml` `version`, `VERSION` trong
  `agw_mcp/server.py`, `agw_core.__version__`, `plugin.json`, `marketplace.json`; rồi sync + `claude plugin validate`.
- **Phát hành PyPI** (`sota-agw-mcp`) — **CHƯA phát hành, chỉ nội bộ (👤 chốt 2026-11-07); không tag `v*` / `test-v*`
  khi chưa được chốt.** Không viết hướng dẫn / mã gọi `uvx sota-agw-mcp` không kèm `--from` (tên chưa đăng ký PyPI →
  có thể cài gói chiếm tên). Khi được phép: KHÔNG `uv publish` từ máy. Tag `vX.Y.Z` khớp version → `publish.yml` (Trusted
  Publishing, environment `pypi`); thử trước bằng Run workflow → TestPyPI. Phiên bản đã lên PyPI không xoá / ghi đè được
  — tăng số mới khi sửa. Trước tag: `uv build` + `scripts/smoke_stdio.py` với wheel.
- Trước commit: `uv run pytest -q`, `uv run ruff check .`, `scripts/sync_plugin_core.py --check`; đổi đóng gói → thêm
  `uv build`, `uvx twine check dist/*`, `scripts/smoke_stdio.py`.
- Sau khi push thay đổi `agw_core` / `agw_remote_mcp`: cập nhật commit ghim ở repo SaaS (`saas/pyproject.toml`) + chạy
  test SaaS (`test_saas_mcp`, `test_saas_platform`…).
- Windows: chạy Python với `-X utf8` (console cp1258).
