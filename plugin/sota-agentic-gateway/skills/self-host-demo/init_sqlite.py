"""Create the SaaS tables in a throwaway SQLite file for a local demo (no Alembic, no Postgres).

    python -X utf8 init_sqlite.py <repo_dir> <db_file>

<repo_dir> = the `saas/` folder of the source checkout (the checkout root also works: `saas/` is found inside).

Only for demos: production self-hosting uses Postgres + `alembic upgrade head`.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    repo, db_file = Path(argv[1]).resolve(), Path(argv[2]).resolve()
    if not (repo / "app" / "saas" / "server.py").is_file() and (repo / "saas" / "app" / "saas" / "server.py").is_file():
        repo = repo / "saas"
    if not (repo / "app" / "saas" / "server.py").is_file():
        print(f"Not a SOTA Agentic Gateway source checkout: {repo}")
        return 2
    db_file.parent.mkdir(parents=True, exist_ok=True)
    os.environ["DATABASE_URL"] = "sqlite:///" + db_file.as_posix()
    os.environ.setdefault("INGESTION_ENABLED", "false")
    os.environ.setdefault("AGENT_WORKER_ENABLED", "false")
    sys.path.insert(0, str(repo))

    from app.db.base import Base, engine
    from app.saas.models import SAAS_TABLES

    Base.metadata.create_all(engine, tables=SAAS_TABLES)
    print(f"ok: {len(SAAS_TABLES)} tables in {db_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
