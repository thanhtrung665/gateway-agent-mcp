# SOTA Agentic Gateway — MCP & Claude plugin

Phần **MCP / plugin** của SOTA Agentic Gateway: cổng tiếp nhận & phản hồi email / tin nhắn cho logistics, chuỗi cung
ứng, thương mại — **mọi việc gửi ra ngoài đều qua người duyệt**. Nền tảng SaaS (API, web, worker) nằm ở repo riêng
`agentic-gateway-saas`.

| Thư mục | Nội dung |
|---|---|
| [`agw_core/`](agw_core/) | Lõi dùng chung, thuần Python: tách email RFC 822, luật G01 quảng cáo / G02 an ninh, BM25 + RRF, trích chữ file, template tô vàng, **định nghĩa công cụ SaaS** (`saas_tools.py`) |
| [`agw_remote_mcp/`](agw_remote_mcp/) | **Remote MCP** — endpoint ASGI `/mcp` (Streamable HTTP, stateless) mà API SaaS gắn vào; công cụ gọi lại REST `/api/v1` của chính API bằng token người gọi |
| [`plugin/sota-agentic-gateway/`](plugin/sota-agentic-gateway/README.md) | **Claude plugin + MCP cục bộ** (`server/agw_mcp.py`, stdio): IMAP chỉ đọc, file, template, tri thức thư mục, nháp + gửi SMTP **chỉ sau khi bạn xác nhận**; nối workspace SaaS bằng API key. 5 skill |
| `.claude-plugin/marketplace.json` | Marketplace của plugin (phải ở gốc repo) |

## Dùng

```bash
# Claude Code — cài plugin
claude plugin marketplace add thanhtrung665/gateway-agent-mcp
claude plugin install sota-agentic-gateway@sota-agentic-gateway

# Client MCP bất kỳ — remote (workspace SaaS, gói có truy cập API)
#   URL: https://<api-saas>/mcp   ·   Header: Authorization: Bearer agw_…
```

Gói Python `sota-agw-mcp` (= `agw_core` + `agw_remote_mcp`) được repo SaaS cài trực tiếp từ GitHub, ghim theo commit:

```toml
"sota-agw-mcp[remote] @ git+https://github.com/thanhtrung665/gateway-agent-mcp@<commit>"
```

## Phát triển

```bash
uv sync --all-extras
uv run pytest -q                              # test plugin + remote MCP (không cần SaaS, không ra mạng)
uv run ruff check .
python -X utf8 scripts/sync_plugin_core.py    # sau khi sửa agw_core/ → chép vào plugin (CI kiểm --check)
claude plugin validate plugin/sota-agentic-gateway && claude plugin validate .
```

Sửa `agw_core/` hoặc `agw_remote_mcp/` xong: push, rồi ở repo SaaS đổi commit ghim trong `saas/pyproject.toml` +
`uv lock` + chạy test SaaS (`test_saas_mcp` là test tích hợp với API thật).
