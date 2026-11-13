"""Reconstrói o manifesto global a partir do banco deste computador.

Uso (na pasta do projeto):

    python scripts/rebuild_manifest.py --dry-run
    python scripts/rebuild_manifest.py

O script confere no Terabox todos os arquivos dos mapeamentos habilitados,
mescla com o manifesto existente (preservando entradas de outros PCs) e grava
o resultado. Rode com o app fechado e sem outro computador sincronizando.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from backend import auth, database  # noqa: E402
from backend.sync_engine import sync_engine  # noqa: E402
from backend.sync_plan import SyncPlan  # noqa: E402
from backend.terabox_client import TeraboxClient  # noqa: E402


async def _main(dry_run: bool) -> int:
    await database.init_db()

    running = await database.fetch_one(
        "SELECT id FROM sync_runs WHERE status = 'running' ORDER BY id DESC LIMIT 1"
    )
    if running:
        print(
            f"ERRO: o sync #{running['id']} está marcado como em andamento. "
            "Pare o sync antes de reconstruir o manifesto."
        )
        return 2

    auth_data = await auth.get_cached_auth()
    if not auth_data:
        print(
            "ERRO: não há autenticação em cache. Abra o app, conecte-se ao "
            "Terabox e tente novamente."
        )
        return 3

    mappings = await database.fetch_all(
        "SELECT * FROM mappings WHERE enabled = 1 ORDER BY id"
    )
    if not mappings:
        print("ERRO: nenhum mapeamento habilitado neste computador.")
        return 4

    uploaded = await database.fetch_one(
        "SELECT COUNT(*) AS total FROM files WHERE status = 'uploaded'"
    )
    print(f"Mapeamentos habilitados: {len(mappings)}")
    print(f"Arquivos uploaded no banco local: {int(uploaded['total'])}")
    print("Conferindo o remoto e mesclando o manifesto...")

    client = TeraboxClient(auth_data["cookies"], auth_data["jstoken"])
    try:
        plan = SyncPlan(mappings=mappings)
        merged = await sync_engine._update_manifest(
            client,
            plan,
            datetime.now().isoformat(),
            dry_run=dry_run,
        )
    finally:
        await client.close()

    files = merged.get("files") or []
    directories = merged.get("directories") or []
    print(f"Manifesto final: {len(files)} arquivo(s), {len(directories)} pasta(s).")

    by_uid = {}
    for entry in files:
        uid = str(entry.get("mapping_uid") or "")
        by_uid[uid] = by_uid.get(uid, 0) + 1
    for mapping in mappings:
        uid = str(mapping.get("uid") or "")
        print(f"  {by_uid.get(uid, 0):>6}  {mapping.get('name')}")

    if dry_run:
        print("DRY-RUN: nada foi gravado no Terabox.")
    else:
        print("Manifesto gravado no Terabox com sucesso.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Reconstrói o manifesto global do Terabox."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Confere e monta o manifesto, mas não grava no Terabox.",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_main(args.dry_run)))
