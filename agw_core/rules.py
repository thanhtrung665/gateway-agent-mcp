"""Luật gateway thuần (không AI): điểm quảng cáo (G01), cảnh báo an ninh (G02), chuẩn hoá tiêu đề luồng (G04).

Trọng số G01 giữ nguyên bản PSBV (`app/services/gateway/g01_ad_filter.py`): ≥ AD_THRESHOLD = quảng cáo chắc chắn.
"""
from __future__ import annotations

import re
from collections.abc import Iterable

AD_THRESHOLD = 5
MARKETING_DOMAINS = (
    "mailchimp", "mcsv.net", "sendgrid", "hubspot", "hs-email", "constantcontact", "mailgun",
    "sendinblue", "brevo", "mktomail", "marketo", "salesforce-marketing", "exacttarget",
    "campaign-archive", "list-manage", "e.linkedin.com", "facebookmail.com", "newsletter",
)
NOREPLY_RE = re.compile(r"^(no-?reply|do-?not-?reply|newsletter|marketing|news|promo|info)@", re.I)
UNSUBSCRIBE_RE = re.compile(r"unsubscribe|hủy đăng ký|huỷ đăng ký|opt[- ]out|manage (your )?preferences", re.I)
DANGEROUS_EXT = (".exe", ".js", ".vbs", ".scr", ".bat", ".cmd", ".iso", ".img", ".lnk", ".hta", ".html", ".htm",
                 ".jar", ".msi", ".ps1", ".docm", ".xlsm")
PAYMENT_RE = re.compile(
    r"(thay đổi|đổi|cập nhật)\s+(số\s+)?tài khoản|tài khoản (ngân hàng )?mới|new bank (account|details)|"
    r"change(d)? (of|in|our) bank|updated? (bank|banking|payment) (details|information)|"
    r"chuyển (tiền|khoản) gấp|urgent (wire|transfer|payment)", re.I)
RE_PREFIX = re.compile(r"^\s*((re|fw|fwd|tr|trả lời|chuyển tiếp)\s*:\s*)+", re.I)
_EMAIL = re.compile(r"[\w.+-]+@[\w.-]+")


def domain_of(addr: str | None) -> str:
    return addr.rsplit("@", 1)[-1].lower() if addr and "@" in addr else ""


def header(headers: dict[str, str] | None, name: str) -> str | None:
    for k, v in (headers or {}).items():
        if k.lower() == name.lower():
            return str(v)
    return None


def distance(a: str, b: str) -> int:
    """Levenshtein (chuỗi ngắn — tên miền); > 2 trả 3 cho nhanh."""
    if abs(len(a) - len(b)) > 2:
        return 3
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def normalize_subject(subject: str | None) -> str:
    return RE_PREFIX.sub("", subject or "").strip().lower()


def ad_score(sender: str | None, headers: dict[str, str] | None, body: str | None) -> tuple[int, list[str]]:
    points, reasons = 0, []

    def add(n: int, why: str) -> None:
        nonlocal points
        points += n
        reasons.append(f"+{n} {why}")

    if header(headers, "List-Unsubscribe"):
        add(3, "header List-Unsubscribe")
    precedence = (header(headers, "Precedence") or "").lower()
    if precedence in ("bulk", "list", "junk"):
        add(3, f"Precedence: {precedence}")
    auto = (header(headers, "Auto-Submitted") or "").lower()
    if auto and auto != "no":
        add(1, f"Auto-Submitted: {auto}")
    dom = domain_of(sender)
    if dom and any(m in dom for m in MARKETING_DOMAINS):
        add(3, f"domain marketing ({dom})")
    if sender and NOREPLY_RE.match(sender):
        add(1, "người gửi no-reply / newsletter")
    if UNSUBSCRIBE_RE.search(body or ""):
        add(1, "nội dung có link hủy đăng ký")
    return points, reasons


def security_flags(sender: str | None, headers: dict[str, str] | None, subject: str | None, body: str | None,
                   attachment_names: Iterable[str], internal_domains: Iterable[str] = ()) -> list[str]:
    flags: list[str] = []
    sender_domain = domain_of(sender)
    reply_to = header(headers, "Reply-To")
    if reply_to:
        found = _EMAIL.findall(reply_to)
        rt = domain_of(found[0]) if found else ""
        if rt and sender_domain and rt != sender_domain:
            flags.append(f"Reply-To ({rt}) khác domain người gửi ({sender_domain})")
    for name in attachment_names:
        if str(name).lower().endswith(DANGEROUS_EXT):
            flags.append(f"file đính kèm có đuôi nguy hiểm: {name}")
    if PAYMENT_RE.search(f"{subject or ''}\n{body or ''}"):
        flags.append("nhắc tới đổi tài khoản ngân hàng / chuyển tiền gấp — xác minh qua kênh khác trước khi làm theo")
    for d in internal_domains:
        if sender_domain and sender_domain != d and distance(sender_domain, d) <= 2:
            flags.append(f"domain người gửi ({sender_domain}) gần giống domain nội bộ ({d}) — nghi giả mạo")
    return flags
