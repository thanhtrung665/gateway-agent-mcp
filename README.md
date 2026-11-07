# SOTA Agentic Gateway — MCP server & Claude plugin

MCP server cho việc tiếp nhận & phản hồi email / tin nhắn trong logistics, chuỗi cung ứng, thương mại: phân loại hộp
thư (luật quảng cáo / lừa đảo), trích chữ file đính kèm, điền template DOCX / XLSX tô vàng, tra thư mục tri thức, soạn
nháp — và **chỉ gửi sau khi bạn xác nhận**. Tuỳ chọn nối workspace SaaS SOTA Agentic Gateway (gửi = tạo yêu cầu duyệt).

- Không có công cụ nào tự gửi hay tự duyệt. Gửi email cục bộ cần bạn bấm xác nhận trong hộp thoại của client (MCP
  elicitation); client không có hộp thoại → server trả lệnh terminal `uvx sota-agw-mcp send <draft_id>` để bạn tự chạy.
- IMAP chỉ đọc. File chỉ đọc / ghi trong thư mục làm việc `AGW_WORKDIR`.
- Nội dung email / file được coi là dữ liệu bên ngoài — không phải lệnh.

## Cài & chạy

Cần [uv](https://docs.astral.sh/uv/). Không cần cài trước — client gọi `uvx sota-agw-mcp` (stdio).

**Claude Code**

```bash
claude mcp add sota-agw -e AGW_WORKDIR=$HOME/SOTA-Agentic-Gateway -- uvx sota-agw-mcp
# hoặc cài plugin (có thêm 5 skill + ô cấu hình):
claude plugin marketplace add thanhtrung665/gateway-agent-mcp
claude plugin install sota-agentic-gateway@sota-agentic-gateway
```

**Claude Desktop** (`claude_desktop_config.json`) · **Cursor** (`~/.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "sota-agw": {
      "command": "uvx",
      "args": ["sota-agw-mcp"],
      "env": {
        "AGW_WORKDIR": "/Users/ban/SOTA-Agentic-Gateway",
        "AGW_IMAP_HOST": "imap.gmail.com",
        "AGW_IMAP_USER": "ban@congty.vn",
        "AGW_IMAP_PASSWORD": "<app password>",
        "AGW_SMTP_HOST": "smtp.gmail.com"
      }
    }
  }
}
```

**VS Code** (`.vscode/mcp.json`)

```json
{
  "servers": {
    "sota-agw": { "type": "stdio", "command": "uvx", "args": ["sota-agw-mcp"], "env": { "AGW_WORKDIR": "${userHome}/SOTA-Agentic-Gateway" } }
  }
}
```

Kiểm cấu hình: `uvx sota-agw-mcp check` (in thư mục làm việc, thử đăng nhập IMAP / SaaS — không in mật khẩu).

## Cấu hình (biến môi trường)

| Biến | Ý nghĩa |
|---|---|
| `AGW_WORKDIR` | Thư mục làm việc (`templates/`, `knowledge/`, `output/`, `drafts/`). Mặc định `~/SOTA-Agentic-Gateway` |
| `AGW_IMAP_HOST` · `AGW_IMAP_PORT` · `AGW_IMAP_USER` · `AGW_IMAP_PASSWORD` | Hộp thư (IMAP SSL, mặc định cổng 993). Dùng **App Password**, không dùng mật khẩu chính |
| `AGW_SMTP_HOST` · `AGW_SMTP_PORT` · `AGW_SMTP_USER` · `AGW_SMTP_PASSWORD` · `AGW_MAIL_FROM` | Gửi (mặc định 587 STARTTLS; user / mật khẩu mặc định = IMAP) |
| `AGW_INTERNAL_DOMAINS` | Domain nội bộ (phân cách dấu phẩy) — dùng cho cảnh báo giả mạo |
| `AGW_SEND_MODE` | `elicit` (mặc định: hỏi xác nhận trong client) · `cli` (chỉ gửi bằng lệnh terminal) · `disabled` |
| `AGW_API_URL` · `AGW_API_KEY` | Nối workspace SaaS (API key `agw_…`, vai trò MEMBER là đủ) → thêm công cụ `saas_*` |

Mật khẩu nằm trong file cấu hình của client dưới dạng chữ thường — dùng App Password riêng, thu hồi được. Bản plugin
Claude Code lưu các ô bí mật an toàn hơn (`userConfig` sensitive).

## Remote MCP (workspace SaaS — không cần cài gì)

Dán `https://<api-saas>/mcp` vào client hỗ trợ MCP từ xa: client mở trang đăng nhập + đồng ý (OAuth 2.1), hoặc gửi
header `Authorization: Bearer agw_…`. Mã endpoint là gói `agw_remote_mcp` trong gói này; máy chủ uỷ quyền nằm ở API SaaS.

```bash
claude mcp add --transport http sota-agw-remote https://<api-saas>/mcp
```

## Trong gói

| Gói | Nội dung |
|---|---|
| `agw_mcp` | MCP server cục bộ (stdio) — lệnh `sota-agw-mcp` |
| `agw_core` | Lõi thuần Python: tách email RFC 822, luật quảng cáo / an ninh, BM25 + RRF, trích chữ PDF / DOCX / XLSX / EML, template tô vàng, định nghĩa công cụ SaaS dùng chung |
| `agw_remote_mcp` | Remote MCP (ASGI, Streamable HTTP stateless) cho API SaaS |

Mã nguồn, Claude plugin và skill: <https://github.com/thanhtrung665/gateway-agent-mcp>

## Phát triển

```bash
uv sync
uv run pytest -q                                   # plugin + gói + remote MCP (không cần SaaS, không ra mạng)
uv run ruff check .
python -X utf8 scripts/sync_plugin_core.py         # sau khi sửa agw_core/ hoặc agw_mcp/server.py → chép vào plugin
uv build && uv run python scripts/smoke_stdio.py uvx --isolated --from dist/<wheel> sota-agw-mcp
claude plugin validate plugin/sota-agentic-gateway && claude plugin validate .
```

`plugin/sota-agentic-gateway/server/agw_mcp.py` là bản chép y hệt `agw_mcp/server.py` (plugin chạy bằng
`uv run --script`, phụ thuộc khai ở khối `# /// script` đầu file — test kiểm khớp `pyproject.toml`). Repo SaaS cài gói
này qua git dependency ghim commit (`sota-agw-mcp[remote] @ git+https://github.com/thanhtrung665/gateway-agent-mcp@<commit>`).

Phát hành PyPI: tag `vX.Y.Z` (khớp `version` trong `pyproject.toml`) → workflow `publish.yml` (Trusted Publishing).

## Giấy phép

Thương mại — xem [LICENSE](https://github.com/thanhtrung665/gateway-agent-mcp/blob/main/LICENSE).
