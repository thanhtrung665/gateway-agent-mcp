"""Đọc email thô (RFC 822 / .eml) → cấu trúc gọn: người gửi, tiêu đề, thân (ưu tiên text/plain), file đính kèm, header
cần cho luật gateway."""
from __future__ import annotations

import email
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from email.header import decode_header, make_header
from email.message import Message
from email.utils import getaddresses, parseaddr, parsedate_to_datetime

MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024
KEEP_HEADERS = ("List-Unsubscribe", "Precedence", "Auto-Submitted", "Reply-To", "In-Reply-To", "X-Mailer")


@dataclass
class ParsedAttachment:
    name: str
    mime_type: str | None = None
    size: int = 0
    content: bytes | None = None  # None khi vượt MAX_ATTACHMENT_BYTES


@dataclass
class ParsedEmail:
    message_id: str
    sender: str | None
    sender_name: str | None
    subject: str
    body: str
    date: datetime | None
    recipients: list[str]
    thread_key: str | None
    headers: dict[str, str] = field(default_factory=dict)
    attachments: list[ParsedAttachment] = field(default_factory=list)


def html_to_text(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "head"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def decode_value(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except (UnicodeDecodeError, LookupError):
        return value


def parse_email(raw: bytes) -> ParsedEmail:
    msg: Message = email.message_from_bytes(raw)
    plain, html = [], []
    attachments: list[ParsedAttachment] = []
    for part in msg.walk():
        if part.is_multipart():
            continue
        disp = (part.get_content_disposition() or "").lower()
        ctype = part.get_content_type()
        filename = part.get_filename()
        raw_payload = part.get_payload(decode=True)
        payload: bytes = raw_payload if isinstance(raw_payload, bytes) else b""
        if disp == "attachment" or (filename and disp != "inline"):
            attachments.append(ParsedAttachment(
                name=decode_value(filename) or "attachment", mime_type=ctype, size=len(payload),
                content=payload if len(payload) <= MAX_ATTACHMENT_BYTES else None))
            continue
        charset = part.get_content_charset() or "utf-8"
        try:
            text = payload.decode(charset, errors="replace")
        except LookupError:
            text = payload.decode("utf-8", errors="replace")
        if ctype == "text/plain":
            plain.append(text)
        elif ctype == "text/html":
            html.append(text)
    body = "\n".join(plain).strip() or html_to_text("\n".join(html))
    name, addr = parseaddr(decode_value(msg.get("From")))
    recipients = [a for _, a in getaddresses([decode_value(msg.get("To")), decode_value(msg.get("Cc"))]) if a]
    try:
        date_header = msg.get("Date")
        date = parsedate_to_datetime(str(date_header)) if date_header else None
    except (TypeError, ValueError):
        date = None
    message_id = (msg.get("Message-ID") or "").strip()
    refs = (msg.get("References") or "").split()
    return ParsedEmail(
        # Không có Message-ID → id ổn định theo nội dung (hash() của Python đổi theo tiến trình — không dùng)
        message_id=message_id or f"no-id-{hashlib.sha256(raw).hexdigest()[:32]}",
        sender=addr.lower() or None, sender_name=name or None, subject=decode_value(msg.get("Subject")),
        body=body, date=date, recipients=recipients,
        thread_key=refs[0] if refs else (msg.get("In-Reply-To") or message_id or None),
        headers={h: decode_value(msg.get(h)) for h in KEEP_HEADERS if msg.get(h)}, attachments=attachments,
    )
