# SOTA Agentic Gateway — Claude plugin (MCP)

Email and message intake for logistics, supply-chain and trading teams, inside Claude (or any MCP client):
triage your inbox with fraud and advertisement rules, read attachments (PDF, DOCX, XLSX, CSV, EML), fill
yellow-highlighted quotation / proforma / CI-PL templates, search your own price lists and catalogues, draft replies,
and send **only after you confirm**. Optionally connect to a SOTA Agentic Gateway SaaS workspace for a shared inbox
across email, Zalo, WhatsApp, Messenger and WeChat, data-source lookups, playbooks and a web approval queue.

## Install

Requires [uv](https://docs.astral.sh/uv/) (it installs Python dependencies on first run).

```bash
claude plugin marketplace add thanhtrung665/gateway-agent-mcp
claude plugin install sota-agentic-gateway@sota-agentic-gateway
```

Only need your SOTA Agentic Gateway workspace (no local mailbox / files)? Install
`sota-agentic-gateway-remote@sota-agentic-gateway` instead: remote MCP with OAuth sign-in, nothing to run locally.

Then open `/plugin`, choose **sota-agentic-gateway → Configure** and fill what you need (all optional):

| Setting | What it is |
|---|---|
| `workdir` | Work folder (default `~/SOTA-Agentic-Gateway`) with `templates/`, `knowledge/`, `output/`, `drafts/`. The plugin only reads/writes files inside it. |
| `imap_host`, `imap_user`, `imap_password` | Your mailbox. Use an **app password** (Gmail, Outlook.com, Yahoo…). |
| `smtp_host` | Outgoing server (port 587 STARTTLS, or set `AGW_SMTP_PORT=465`). User/password default to the IMAP ones. |
| `send_mode` | `elicit` (confirm in a dialog, default) · `cli` (send only from the terminal) · `disabled`. |
| `api_url`, `api_key` | SaaS workspace (API key from Settings → API keys, role MEMBER). |

Other MCP clients: run `uv run --script server/agw_mcp.py` over stdio with the same settings as environment variables
`AGW_WORKDIR`, `AGW_IMAP_HOST`, `AGW_IMAP_USER`, `AGW_IMAP_PASSWORD`, `AGW_SMTP_HOST`, `AGW_SMTP_PORT`,
`AGW_MAIL_FROM`, `AGW_INTERNAL_DOMAINS`, `AGW_SEND_MODE`, `AGW_API_URL`, `AGW_API_KEY`.
Check the setup with `uv run --script server/agw_mcp.py check`.

## Tools

Local: `gateway_status`, `mail_list_recent`, `mail_read`, `mail_attachment_text`, `file_read`, `email_check`,
`template_inspect`, `template_fill`, `knowledge_search`, `draft_create`, `draft_send`.

SaaS (when configured): `saas_inbox_list`, `saas_inbox_get`, `saas_analyze`, `saas_save_reply_draft`,
`saas_request_reply`, `saas_approvals`, `saas_knowledge_search`, `saas_connections`, `saas_query_catalog`,
`saas_query`, `saas_templates`, `saas_fill_template`, `saas_playbooks`, `saas_run_playbook`, `saas_dashboard`.

Skills: `email-triage`, `reply-drafting`, `template-fill`, `sota-saas`, `self-host-demo` (local demo from the source checkout — needs a self-host / source license).

## Human in the loop

- Nothing is sent automatically. `draft_send` shows recipients, CC, subject, body and attachments in the client's
  confirmation dialog (MCP elicitation) and sends only if you tick **send**. A client without that dialog gets a
  terminal command instead: `uv run --script server/agw_mcp.py send <draft_id>` (type `GUI` to send).
- A sent draft is moved to `drafts/sent/` and cannot be sent twice.
- In the SaaS, replies become approval requests decided on the web; API keys cannot approve.
- IMAP is opened read-only (messages are not marked as read). Files outside the work folder are refused, so an email
  cannot trick the assistant into reading and mailing other files.
- Email content is treated as untrusted data; rule-based warnings (look-alike domains, bank-detail changes,
  Reply-To mismatch, dangerous attachments) are returned with every message.

## Privacy

In local mode your mail and files go only to the AI model you use in Claude and to your own mail server. In SaaS mode
the plugin calls the workspace API URL you configure.
