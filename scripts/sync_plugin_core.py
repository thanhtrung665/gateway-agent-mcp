"""Chép `agw_core/` (lõi dùng chung SaaS ↔ plugin) vào plugin để plugin chạy độc lập, không cần cả repo.

    python scripts/sync_plugin_core.py          # chép
    python scripts/sync_plugin_core.py --check  # chỉ kiểm (CI / tests): khác → exit 1
"""
from __future__ import annotations

import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # gốc repo gateway-agent-mcp
SRC = ROOT / "agw_core"
DEST = ROOT / "plugin" / "sota-agentic-gateway" / "server" / "agw_core"


def sources() -> list[str]:
    return sorted(p.name for p in SRC.glob("*.py"))


def differences() -> list[str]:
    diff = [n for n in sources() if not (DEST / n).is_file() or not filecmp.cmp(SRC / n, DEST / n, shallow=False)]
    extra = sorted(p.name for p in DEST.glob("*.py") if p.name not in sources()) if DEST.is_dir() else []
    return diff + [f"(thừa) {n}" for n in extra]


def main(argv: list[str]) -> int:
    if "--check" in argv:
        diff = differences()
        if diff:
            print("agw_core của plugin lệch bản gốc:", ", ".join(diff), "— chạy python scripts/sync_plugin_core.py")
            return 1
        print("agw_core của plugin khớp bản gốc")
        return 0
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)
    for n in sources():
        shutil.copy2(SRC / n, DEST / n)
    print(f"Đã chép {len(sources())} file → {DEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
