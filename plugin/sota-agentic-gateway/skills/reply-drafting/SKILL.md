---
name: reply-drafting
description: Draft a professional reply to a business email (customer inquiry, supplier quotation, PO confirmation, shipment update, payment follow-up) using facts from the knowledge folder or the SaaS workspace, then send only after the user confirms. Use when the user asks to answer, reply to or follow up on an email.
---

# Reply drafting (human approves every send)

1. Read the original with `mail_read` (or `saas_inbox_get` for SaaS items) and note what is actually asked.
2. Look up facts before writing — never invent prices, stock, lead times or dates:
   - local: `knowledge_search` over the user's price lists / catalogues / policies;
   - SaaS: `saas_knowledge_search`, `saas_query_catalog` + `saas_query` (named, read-only queries).
   If a fact is missing, write a clear placeholder like `[lead time — please confirm]` and tell the user.
3. Write in the language of the incoming mail (Vietnamese or English), short, with the customer's reference numbers.
   Keep the subject as `Re: <original subject>`. Never include internal purchase prices or supplier names in a
   customer reply, and never include selling prices in a supplier reply.
4. Local mailbox: `draft_create` (attachments must be inside the work folder, e.g. a file produced by
   `template_fill`). Show the preview to the user. Only when the user says to send, call `draft_send` — the client
   then shows a confirmation dialog; if it cannot, give the user the terminal command returned by the tool.
5. SaaS workspace: `saas_save_reply_draft` then `saas_request_reply`. This only creates an approval request —
   tell the user to approve it on the web app. There is no tool to approve.
