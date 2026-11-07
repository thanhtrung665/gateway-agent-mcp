"""Chép mã nguồn sang Claude plugin để plugin chạy độc lập (`uv run --script`), không cần cài gói:

- `agw_core/`            → `plugin/sota-agentic-gateway/server/agw_core/`
- `agw_mcp/server.py`    → `plugin/sota-agentic-gateway/server/agw_mcp.py` (y hệt — khối `# /// script` PEP 723 ở đầu)
- skill dùng chung (`SHARED_SKILLS`) của plugin cục bộ → plugin `sota-agentic-gateway-remote`

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
SERVER_DIR = ROOT / "plugin" / "sota-agentic-gateway" / "server"
DEST = SERVER_DIR / "agw_core"
SERVER_SRC, SERVER_DEST = ROOT / "agw_mcp" / "server.py", SERVER_DIR / "agw_mcp.py"
SKILLS_SRC = ROOT / "plugin" / "sota-agentic-gateway" / "skills"
SKILLS_DEST = ROOT / "plugin" / "sota-agentic-gateway-remote" / "skills"
SHARED_SKILLS = ("sota-saas",)  # skill chỉ dùng công cụ saas_* — hợp với cả 2 chế độ


def sources() -> list[str]:
    return sorted(p.name for p in SRC.glob("*.py"))


def differences() -> list[str]:
    diff = [n for n in sources() if not (DEST / n).is_file() or not filecmp.cmp(SRC / n, DEST / n, shallow=False)]
    extra = sorted(p.name for p in DEST.glob("*.py") if p.name not in sources()) if DEST.is_dir() else []
    if not SERVER_DEST.is_file() or not filecmp.cmp(SERVER_SRC, SERVER_DEST, shallow=False):
        diff.append("agw_mcp.py")
    for name in SHARED_SKILLS:
        a, b = SKILLS_SRC / name / "SKILL.md", SKILLS_DEST / name / "SKILL.md"
        if not b.is_file() or not filecmp.cmp(a, b, shallow=False):
            diff.append(f"skill {name} (remote)")
    return diff + [f"(thừa) {n}" for n in extra]


def main(argv: list[str]) -> int:
    if "--check" in argv:
        diff = differences()
        if diff:
            print("Bản chép trong plugin lệch bản gốc:", ", ".join(diff), "— chạy python scripts/sync_plugin_core.py")
            return 1
        print("Plugin khớp bản gốc (agw_core + agw_mcp.py + skill dùng chung)")
        return 0
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)
    for n in sources():
        shutil.copy2(SRC / n, DEST / n)
    shutil.copy2(SERVER_SRC, SERVER_DEST)
    for name in SHARED_SKILLS:
        (SKILLS_DEST / name).mkdir(parents=True, exist_ok=True)
        shutil.copy2(SKILLS_SRC / name / "SKILL.md", SKILLS_DEST / name / "SKILL.md")
    print(f"Đã chép {len(sources())} file → {DEST.relative_to(ROOT)} + {SERVER_DEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
