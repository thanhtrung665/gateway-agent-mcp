# SOTA Agentic Gateway — Remote (Claude Code plugin)

Nối Claude Code với workspace SOTA Agentic Gateway qua **remote MCP** — không cần cài Python / uv, không cần API key.

```bash
claude plugin marketplace add thanhtrung665/gateway-agent-mcp
claude plugin install sota-agentic-gateway-remote@sota-agentic-gateway
```

1. Nhập **Remote MCP URL** (`https://<api>/mcp` — xem Cài đặt → Claude / MCP trên web app).
2. Mở `/mcp` → chọn `sota-agentic-gateway` → đăng nhập: trình duyệt mở trang đồng ý của SOTA Agentic Gateway, chọn
   workspace → Cho phép. Token được Claude Code lưu an toàn và tự làm mới; thu hồi ở Cài đặt → Claude / MCP.

Ứng dụng nhận vai trò MEMBER: đọc hộp thư, phân tích, tra tri thức / dữ liệu, điền template, lưu nháp, **tạo yêu cầu
duyệt** — không tự gửi, không duyệt. Cần hộp thư IMAP / file trên máy → dùng plugin `sota-agentic-gateway` (cục bộ).
Prompt có sẵn: `inbox_saas`, `reply_saas` (gõ `/` trong Claude Code).
