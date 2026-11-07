"""Trích chữ từ file (bản gọn cho MCP server chạy cục bộ): PDF có lớp chữ, DOCX, XLSX, CSV, TXT, HTML, EML.
Bản SaaS dùng S01 Document Parser đầy đủ (OCR trang scan qua model BYOK…)."""
from __future__ import annotations

import csv
import io

MAX_CHARS = 200_000


class UnsupportedFile(ValueError):
    pass


def kind_of(data: bytes, name: str = "") -> str:
    n = name.lower()
    if data[:4] == b"%PDF" or n.endswith(".pdf"):
        return "pdf"
    if data[:2] == b"PK":
        if n.endswith(".xlsx") or b"xl/" in data[:2000]:
            return "xlsx"
        if n.endswith(".docx") or b"word/" in data[:2000]:
            return "docx"
        return "zip"
    for ext in ("csv", "txt", "md", "html", "htm", "eml", "json"):
        if n.endswith("." + ext):
            return {"htm": "html", "md": "txt", "json": "txt"}.get(ext, ext)
    return "unknown"


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "cp1258", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def extract_text(data: bytes, name: str = "") -> str:
    kind = kind_of(data, name)
    if kind == "pdf":
        import pdfplumber

        with pdfplumber.open(io.BytesIO(data)) as pdf:
            text = "\n\n".join((p.extract_text() or "") for p in pdf.pages[:60])
        if not text.strip():
            raise UnsupportedFile(f"{name}: PDF không có lớp chữ (bản scan) — cần OCR")
    elif kind == "docx":
        from docx import Document

        doc = Document(io.BytesIO(data))
        parts = [p.text for p in doc.paragraphs]
        for t in doc.tables:
            parts += [" | ".join(c.text.strip() for c in row.cells) for row in t.rows]
        text = "\n".join(parts)
    elif kind == "xlsx":
        from openpyxl import load_workbook

        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        parts = []
        for ws in wb.worksheets:
            parts.append(f"## {ws.title}")
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i >= 2000:
                    break
                if any(v is not None for v in row):
                    parts.append(" | ".join("" if v is None else str(v) for v in row))
        text = "\n".join(parts)
    elif kind == "csv":
        rows = csv.reader(io.StringIO(_decode(data)))
        text = "\n".join(" | ".join(r) for i, r in enumerate(rows) if i < 5000)
    elif kind == "html":
        from agw_core.email_parse import html_to_text

        text = html_to_text(_decode(data))
    elif kind == "eml":
        from agw_core.email_parse import parse_email

        e = parse_email(data)
        text = f"Từ: {e.sender_name} <{e.sender}>\nTiêu đề: {e.subject}\n\n{e.body}"
    elif kind == "txt":
        text = _decode(data)
    else:
        raise UnsupportedFile(f"{name or 'file'}: định dạng chưa hỗ trợ")
    return text[:MAX_CHARS]
