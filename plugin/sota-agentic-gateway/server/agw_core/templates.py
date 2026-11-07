"""Template từ file khách upload: vùng TÔ VÀNG = trường dữ liệu cần thay.

DOCX: run có text highlight vàng (hoặc shading nền FFFF00); các run vàng liền nhau trong 1 đoạn = 1 trường.
XLSX: ô có nền đặc màu vàng (FFFF00).

Tên trường (key) suy ra theo thứ tự:
  1. Cú pháp tường minh trong vùng vàng: `{{ten_khach}}`, `[ten_khach]`, `<ten_khach>`
  2. Nhãn đứng trước: DOCX "Kính gửi: <vàng>" → `kinh_gui`; XLSX ô bên trái / ô tiêu đề phía trên
  3. Chính nội dung mẫu: "Nguyễn Văn A" → `nguyen_van_a`
Cùng key xuất hiện nhiều chỗ = 1 trường (điền 1 lần, thay mọi nơi).

Điền: giá trị có → thay + bỏ màu vàng; thiếu giá trị → GIỮ mẫu + GIỮ màu vàng để người duyệt thấy ngay chỗ thiếu.
"""
from __future__ import annotations

import io
import re
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

YELLOW_HEX = {"FFFF00", "FFFFFF00", "00FFFF00"}
_EXPLICIT = re.compile(r"^\s*(?:\{\{|\[|<|\{)\s*([\w .\-À-ỹ]+?)\s*(?:\}\}|\]|>|\})\s*$")
_LABEL_BEFORE = re.compile(r"([\wÀ-ỹ][\wÀ-ỹ .\-/]{0,60}?)\s*[:：]\s*$")


class TemplateError(ValueError):
    pass


def slugify(text: str, max_len: int = 40) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return (text[:max_len].strip("_") or "field") if text else "field"


def guess_type(sample: str) -> str:
    s = sample.strip()
    if re.fullmatch(r"\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}|\d{4}-\d{2}-\d{2}", s):
        return "date"
    if re.fullmatch(r"[\w.+\-]+@[\w\-]+\.[\w.\-]+", s):
        return "email"
    if re.fullmatch(r"[-+]?[\d.,]+\s*(%|usd|vnd|đ)?", s, re.I) and re.search(r"\d", s):
        return "number"
    return "text"


@dataclass
class _Field:
    key: str
    label: str
    sample: str
    type: str
    occurrences: int = 1
    locations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"key": self.key, "label": self.label, "sample": self.sample, "type": self.type,
                "occurrences": self.occurrences, "locations": self.locations[:10]}


def _derive_key(sample: str, label_hint: str | None) -> tuple[str, str]:
    m = _EXPLICIT.match(sample)
    if m:
        name = m.group(1).strip()
        return slugify(name), name
    if label_hint:
        return slugify(label_hint), label_hint.strip()
    return slugify(sample), sample.strip()


class _Collector:
    def __init__(self) -> None:
        self.fields: dict[str, _Field] = {}
        self.order: list[str] = []

    def add(self, sample: str, label_hint: str | None, location: str) -> str:
        key, label = _derive_key(sample, label_hint)
        f = self.fields.get(key)
        if f is None:
            self.fields[key] = _Field(key, label, sample.strip(), guess_type(sample), 1, [location])
            self.order.append(key)
        else:
            f.occurrences += 1
            f.locations.append(location)
        return key

    def result(self) -> list[dict[str, Any]]:
        return [self.fields[k].to_dict() for k in self.order]


# ─────────────────────────── DOCX ───────────────────────────

def _run_is_yellow(run) -> bool:
    from docx.enum.text import WD_COLOR_INDEX
    from docx.oxml.ns import qn

    if run.font.highlight_color == WD_COLOR_INDEX.YELLOW:
        return True
    rpr = run._r.rPr
    if rpr is not None:
        shd = rpr.find(qn("w:shd"))
        if shd is not None and (shd.get(qn("w:fill")) or "").upper() in YELLOW_HEX:
            return True
    return False


def _clear_yellow(run) -> None:
    from docx.oxml.ns import qn

    run.font.highlight_color = None
    rpr = run._r.rPr
    if rpr is not None:
        shd = rpr.find(qn("w:shd"))
        if shd is not None:
            rpr.remove(shd)


def _iter_paragraphs(doc) -> Iterator[tuple[str, Any, str | None]]:
    """→ (vị trí, đoạn, nhãn gợi ý từ ô bên trái nếu đoạn nằm trong bảng)."""
    def from_container(prefix: str, container, cell_hint: str | None = None) -> Iterator[tuple[str, Any, str | None]]:
        for i, p in enumerate(container.paragraphs):
            yield f"{prefix}p{i + 1}", p, cell_hint
        for t_i, table in enumerate(getattr(container, "tables", [])):
            for r_i, row in enumerate(table.rows):
                cells = row.cells
                for c_i, cell in enumerate(cells):
                    left = cells[c_i - 1].text.strip().rstrip(":：").strip() if c_i > 0 else ""
                    hint = left if left and len(left) <= 60 and cells[c_i - 1]._tc is not cell._tc else None
                    yield from from_container(f"{prefix}t{t_i + 1}r{r_i + 1}c{c_i + 1}/", cell, hint)

    yield from from_container("", doc)
    for s_i, section in enumerate(doc.sections):
        for part_name in ("header", "footer"):
            part = getattr(section, part_name, None)
            if part is not None and not part.is_linked_to_previous:
                yield from from_container(f"{part_name}{s_i + 1}/", part)


def _segments(paragraph) -> list[tuple[list[Any], str]]:
    """Nhóm run vàng liền nhau → [(runs, text_trước_segment)]."""
    segs: list[tuple[list[Any], str]] = []
    current: list[Any] = []
    before = ""
    text_so_far = ""
    for run in paragraph.runs:
        if _run_is_yellow(run) and run.text:
            if not current:
                before = text_so_far
            current.append(run)
        else:
            if current:
                segs.append((current, before))
                current = []
        text_so_far += run.text
    if current:
        segs.append((current, before))
    return segs


def _label_hint(before: str, cell_hint: str | None = None) -> str | None:
    if not before.strip():
        return cell_hint
    m = _LABEL_BEFORE.search(before)
    if not m:
        return None
    words = m.group(1).split()
    return " ".join(words[-4:]) if words else None


def extract_docx(data: bytes) -> list[dict[str, Any]]:
    from docx import Document

    doc = Document(io.BytesIO(data))
    col = _Collector()
    for loc, p, cell_hint in _iter_paragraphs(doc):
        for runs, before in _segments(p):
            sample = "".join(r.text for r in runs)
            if sample.strip():
                col.add(sample, _label_hint(before, cell_hint), loc)
    return col.result()


def fill_docx(data: bytes, values: dict[str, Any], clear_highlight: bool = True) -> bytes:
    from docx import Document

    doc = Document(io.BytesIO(data))
    for _, p, cell_hint in _iter_paragraphs(doc):
        for runs, before in _segments(p):
            sample = "".join(r.text for r in runs)
            if not sample.strip():
                continue
            key, _ = _derive_key(sample, _label_hint(before, cell_hint))
            val = values.get(key)
            if val is None or val == "":
                continue
            runs[0].text = str(val)
            for r in runs[1:]:
                r.text = ""
            if clear_highlight:
                for r in runs:
                    _clear_yellow(r)
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


# ─────────────────────────── XLSX ───────────────────────────

def _cell_is_yellow(cell) -> bool:
    fill = cell.fill
    if fill is None or fill.fill_type != "solid":
        return False
    color = fill.fgColor
    rgb = color.rgb if color is not None and color.type == "rgb" else None
    if isinstance(rgb, str) and rgb.upper() in YELLOW_HEX:
        return True
    return color is not None and color.type == "indexed" and color.indexed in (5, 13)  # vàng trong bảng màu mặc định


def _xlsx_hint(ws, cell) -> str | None:
    if cell.column > 1:
        left = ws.cell(row=cell.row, column=cell.column - 1).value
        if isinstance(left, str) and left.strip() and not _cell_is_yellow(ws.cell(row=cell.row, column=cell.column - 1)):
            return left.strip().rstrip(":：").strip()
    if cell.row > 1:
        above = ws.cell(row=cell.row - 1, column=cell.column)
        if isinstance(above.value, str) and above.value.strip() and not _cell_is_yellow(above):
            return above.value.strip().rstrip(":：").strip()
    return None


def _iter_yellow_cells(wb) -> Iterator[tuple[Any, Any, str]]:
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if _cell_is_yellow(cell) and cell.value not in (None, ""):
                    yield ws, cell, f"{ws.title}!{cell.coordinate}"


def extract_xlsx(data: bytes) -> list[dict[str, Any]]:
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(data))
    col = _Collector()
    for ws, cell, loc in _iter_yellow_cells(wb):
        col.add(str(cell.value), _xlsx_hint(ws, cell), loc)
    return col.result()


def _coerce(value: Any, original: Any) -> Any:
    if isinstance(original, (int, float)) and not isinstance(original, bool) and isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        try:
            return int(cleaned) if re.fullmatch(r"[-+]?\d+", cleaned) else float(cleaned)
        except ValueError:
            return value
    return value


def fill_xlsx(data: bytes, values: dict[str, Any], clear_highlight: bool = True) -> bytes:
    from openpyxl import load_workbook
    from openpyxl.styles import PatternFill

    wb = load_workbook(io.BytesIO(data))
    for ws, cell, _ in list(_iter_yellow_cells(wb)):
        key, _ = _derive_key(str(cell.value), _xlsx_hint(ws, cell))
        val = values.get(key)
        if val is None or val == "":
            continue
        cell.value = _coerce(val, cell.value)
        if clear_highlight:
            cell.fill = PatternFill(fill_type=None)
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


# ─────────────────────────── API chung ───────────────────────────

def file_type_of(file_name: str) -> str:
    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if ext not in ("docx", "xlsx"):
        raise TemplateError("Chỉ hỗ trợ file .docx và .xlsx (bản .doc/.xls cũ: mở bằng Office rồi lưu lại)")
    return ext


def _guard(data: bytes) -> None:
    from agw_core.safezip import UnsafeArchive, check_zip

    try:
        check_zip(data)
    except UnsafeArchive as e:
        raise TemplateError(str(e)) from e


def extract_fields(file_type: str, data: bytes) -> list[dict[str, Any]]:
    _guard(data)
    try:
        fields = extract_docx(data) if file_type == "docx" else extract_xlsx(data)
    except TemplateError:
        raise
    except Exception as e:  # noqa: BLE001 — file hỏng / sai định dạng
        raise TemplateError(f"Không đọc được file {file_type}: {e}") from e
    if not fields:
        raise TemplateError("Không tìm thấy vùng tô vàng nào — hãy tô vàng (Text Highlight / Fill màu vàng) "
                            "những chỗ cần thay rồi upload lại")
    return fields


def fill(file_type: str, data: bytes, values: dict[str, Any], clear_highlight: bool = True) -> bytes:
    _guard(data)
    return fill_docx(data, values, clear_highlight) if file_type == "docx" else fill_xlsx(data, values, clear_highlight)


def missing_fields(fields: list[dict[str, Any]], values: dict[str, Any]) -> list[str]:
    return [f["key"] for f in fields if values.get(f["key"]) in (None, "")]


def values_schema(fields: list[dict[str, Any]]) -> dict[str, Any]:
    """JSON Schema cho LLM điền template: mỗi trường là string hoặc null (null = không đủ căn cứ, KHÔNG bịa)."""
    return {
        "type": "object",
        "properties": {
            "values": {
                "type": "object",
                "properties": {f["key"]: {"anyOf": [{"type": "string"}, {"type": "null"}],
                                         "description": f"{f['label']} (mẫu: {f['sample']})"}
                               for f in fields},
            },
            "notes": {"type": "string"},
        },
    }
