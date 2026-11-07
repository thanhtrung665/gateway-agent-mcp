---
name: sota-saas
description: Work with a SOTA Agentic Gateway SaaS workspace from Claude — unified inbox across email, Zalo, WhatsApp, Messenger and WeChat, AI analysis, knowledge base, data-source lookups (Postgres, Google Sheets, MISA, REST), templates, playbooks and the approval queue. Use when the user mentions their workspace, gateway inbox, approvals or playbooks.
---

# SOTA Agentic Gateway workspace

Requires the plugin settings `api_url` and `api_key` (create the key in the web app: Settings → API keys; role MEMBER
is enough). Check with `gateway_status`.

- Inbox: `saas_inbox_list` (filter by `status`, `label`, `q`) → `saas_inbox_get`. Run `saas_analyze` only when the
  item has no analysis yet (it spends the workspace's AI budget).
- Facts: `saas_knowledge_search`; data lookups via `saas_query_catalog(connection_id)` then
  `saas_query(connection_id, name, params)` — only pre-declared read-only queries are allowed.
- Documents: `saas_templates`, `saas_fill_template`.
- Replies: `saas_save_reply_draft` → `saas_request_reply`. This creates an approval; a human approves it on the web.
- Playbooks: `saas_playbooks`; `saas_run_playbook` asks the user to confirm, and any outbound step still waits for web
  approval.
- Monitoring: `saas_approvals` (read-only), `saas_dashboard` (traffic, AI cost, workload).

Never claim something was sent when the tool returned an approval id — say it is waiting for approval.
If a tool answers 402, the workspace hit its plan limit or the plan does not include API access: tell the user to
check "Gói & thanh toán" in the web app.
