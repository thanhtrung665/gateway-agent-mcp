"""Chống "zip bomb" cho DOCX / XLSX (bản chất là file ZIP) TRƯỚC khi đưa vào python-docx / openpyxl.

File độc hại có thể nén vài KB nhưng giải nén ra hàng GB → treo / hết RAM máy chủ (từ chối dịch vụ cho MỌI tenant).
Kiểm trên bảng mục lục ZIP (không giải nén): số mục, tổng dung lượng khai báo, tỉ lệ nén, đường dẫn lạ.
"""
from __future__ import annotations

import io
import zipfile

MAX_MEMBERS = 5_000
MAX_TOTAL_UNCOMPRESSED = 200 * 1024 * 1024  # 200 MB — chứng từ văn phòng thật hiếm khi quá 50 MB khi giải nén
MAX_MEMBER_RATIO = 200  # tỉ lệ nén 1 mục; văn bản XML thường 5–20×, bom zip hàng nghìn ×
RATIO_CHECK_FLOOR = 10 * 1024 * 1024  # chỉ xét tỉ lệ khi mục giải nén > 10 MB (file nhỏ nén cao là bình thường)


class UnsafeArchive(ValueError):
    pass


def check_zip(data: bytes, *, max_members: int = MAX_MEMBERS, max_total: int = MAX_TOTAL_UNCOMPRESSED,
              max_ratio: int = MAX_MEMBER_RATIO) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            infos = zf.infolist()
    except (zipfile.BadZipFile, OSError, ValueError) as e:
        raise UnsafeArchive("File Office hỏng hoặc không phải DOCX/XLSX hợp lệ") from e
    if len(infos) > max_members:
        raise UnsafeArchive(f"File chứa quá nhiều thành phần ({len(infos)})")
    total = 0
    for info in infos:
        name = info.filename
        if name.startswith(("/", "\\")) or ".." in name.replace("\\", "/").split("/"):
            raise UnsafeArchive("File chứa đường dẫn không hợp lệ")
        total += info.file_size
        if info.file_size > RATIO_CHECK_FLOOR and info.file_size > max_ratio * max(info.compress_size, 1):
            raise UnsafeArchive("File có tỉ lệ nén bất thường (nghi zip bomb) — không xử lý")
    if total > max_total:
        raise UnsafeArchive(f"File giải nén quá lớn ({total // (1024 * 1024)} MB > {max_total // (1024 * 1024)} MB)")
