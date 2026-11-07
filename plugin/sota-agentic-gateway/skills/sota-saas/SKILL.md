---
name: sota-saas
description: Work with a SOTA Agentic Gateway SaaS workspace from Claude — unified inbox across email, Zalo, WhatsApp, Messenger and WeChat, AI analysis, knowledge base, data-source lookups (Postgres, Google Sheets, MISA, REST), templates, playbooks and the approval queue. Use when the user mentions their workspace, gateway inbox, approvals or playbooks.
---

# SOTA Agentic Gateway workspace

The `saas_*` tools come from one of two places:
- **Remote** (plugin `sota-agentic-gateway-remote`, recommended): the workspace's `https://<api>/mcp`, signed in with
  OAuth from `/mcp` — no key to copy. If its tools are missing or answer 401, tell the user to open `/mcp` and log in.
- **Local** (plugin `sota-agentic-gateway` with settings `api_url` + `api_key`, key from Settings → API keys, role
  MEMBER is enough). Check with `gateway_status`.
If no `saas_*` tool is available at all, tell the user which plugin / settings to configure.

- Inbox: `saas_inbox_list` (filter by `status`, `label`, `q`) → `saas_inbox_get`. Run `saas_analyze` only when the
  item has no analysis yet (it spends the workspace's AI budget).
- Facts: `saas_knowledge_search`; data lookups via `saas_query_catalog(connection_id)` then
  `saas_query(connection_id, name, params)` — only pre-declared read-only queries are allowed.
- Documents: `saas_templates`, `saas_fill_template`.
- Replies: `saas_save_reply_draft` → `saas_request_reply`. This creates an approval; a human approves it on the web.
- Playbooks: `saas_playbooks`; `saas_run_playbook` (local mode only) asks the user to confirm, and any outbound step
  still waits for web approval. In remote mode, ask the user to start the playbook from the web app.
- Monitoring: `saas_approvals` (read-only), `saas_dashboard` (traffic, AI cost, workload).

Never claim something was sent when the tool returned an approval id — say it is waiting for approval.
If a tool answers 402, the workspace hit its plan limit or the plan does not include API access: tell the user to
check "Gói & thanh toán" in the web app.
