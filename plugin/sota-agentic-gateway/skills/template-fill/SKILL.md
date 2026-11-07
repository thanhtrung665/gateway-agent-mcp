---
name: template-fill
description: Fill company document templates (quotation, proforma invoice, commercial invoice / packing list, delivery note) where the fields to fill are highlighted in yellow in a DOCX or XLSX file, using data from an email, attachment or lookup. Use when the user asks to prepare a quotation, PI, CI/PL or any form from a template.
---

# Yellow-highlight template filling

Templates live in `<work folder>/templates/` (see `gateway_status`). In each DOCX/XLSX, every run/cell highlighted
**yellow** is a field; the sample text in it hints at the type (date, number, money, text).

1. `template_inspect(path)` → list of fields with `key`, `label`, sample and `values_schema`.
2. Collect values from the source (email body, `mail_attachment_text`, `knowledge_search`, `saas_query`).
   Use exact numbers from the source; do the arithmetic explicitly (quantity × unit price = amount) and show it.
3. `template_fill(path, values)` → new file in `output/`. The original template is never modified; yellow is cleared
   in the output.
4. Report `missing_fields` to the user and ask for them; do not guess commercial terms (price, incoterm, payment
   term, validity).
5. The filled file is a draft for the user to open and check. To send it, attach it via `draft_create` and follow
   the `reply-drafting` skill (confirmation required).

SaaS workspace: `saas_templates` then `saas_fill_template` (optionally `use_ai=true` with `inbox_item_id`); the render
is reviewed on the web and can be attached to a reply approval with `saas_request_reply(template_render_ids=[…])`.
