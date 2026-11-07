"""Chia đoạn + xếp hạng BM25 (bỏ dấu tiếng Việt, giữ mã hàng có gạch nối) + gộp thứ hạng RRF cho tìm kiếm lai."""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from collections.abc import Sequence

CHUNK_CHARS = 1200
CHUNK_OVERLAP = 150
K1, B = 1.5, 0.75
_TOKEN = re.compile(r"[a-z0-9]+(?:[-./][a-z0-9]+)*")


def fold(text: str) -> str:
    text = text.lower().replace("đ", "d")
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def tokens(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(fold(text)) if len(t) > 1 or t.isdigit()]


def chunk_text(text: str, size: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = re.sub(r"[ \t]+", " ", text).strip()
    if not text:
        return []
    out, start = [], 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):  # cắt ở xuống dòng / dấu chấm gần nhất cho đoạn tự nhiên
            cut = max(text.rfind("\n", start + size // 2, end), text.rfind(". ", start + size // 2, end))
            if cut > start:
                end = cut + 1
        out.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [c for c in out if c]


def bm25_rank(query: str, texts: Sequence[str]) -> list[tuple[int, float]]:
    """→ [(chỉ số văn bản, điểm)] giảm dần, chỉ văn bản có điểm > 0."""
    q = list(dict.fromkeys(tokens(query)))
    if not q or not texts:
        return []
    docs = [Counter(tokens(t)) for t in texts]
    n = len(docs)
    avgdl = sum(sum(d.values()) for d in docs) / n or 1
    df = {t: sum(1 for d in docs if t in d) for t in q}
    scored = []
    for i, tf in enumerate(docs):
        dl = sum(tf.values()) or 1
        s = 0.0
        for t in q:
            if tf.get(t):
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                s += idf * tf[t] * (K1 + 1) / (tf[t] + K1 * (1 - B + B * dl / avgdl))
        if s > 0:
            scored.append((i, s))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def rrf(rankings: Sequence[Sequence[int]], k: int = 60) -> list[tuple[int, float]]:
    """Reciprocal Rank Fusion: gộp nhiều bảng xếp hạng (danh sách chỉ số, tốt nhất trước)."""
    scores: dict[int, float] = {}
    for ranking in rankings:
        for pos, idx in enumerate(ranking):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + pos + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
