#!/usr/bin/env python3
"""Auditoria somente leitura do banco de sessoes do OpenCode.

Nao altera o banco nem os arquivos do OpenCode. Gera um relatorio CSV e um
resumo JSON na pasta relatorios/.
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB = Path.home() / ".local" / "share" / "opencode" / "opencode.db"
DEFAULT_OUT = Path(__file__).resolve().parent / "relatorios"
MB = 1024 * 1024


def setup_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def fmt_num(value: float, decimals: int = 1) -> str:
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".")


def fmt_mb(value: float) -> str:
    return f"{fmt_num(value / MB)} MB"


def fmt_ts(ms: int | None) -> str:
    if not ms:
        return "-"
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc).astimezone()
    return dt.strftime("%Y-%m-%d %H:%M")


def trunc(text: str | None, width: int) -> str:
    text = (text or "").replace("\r", " ").replace("\n", " ").strip()
    if len(text) <= width:
        return text
    return text[: max(0, width - 3)] + "..."


def project_label(worktree: str | None) -> str:
    if not worktree:
        return "(sem projeto)"
    name = Path(worktree).name
    return name or worktree


def connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.is_file():
        raise SystemExit(f"ERRO: banco nao encontrado: {db_path}")
    uri = f"file:{db_path.as_posix()}?mode=ro"
    try:
        con = sqlite3.connect(uri, uri=True, timeout=10)
    except sqlite3.Error as exc:
        raise SystemExit(f"ERRO ao abrir o banco em modo somente leitura: {exc}") from exc
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only = ON")
    return con


def table_exists(con: sqlite3.Connection, name: str) -> bool:
    row = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def scalar(con: sqlite3.Connection, sql: str, params: tuple = ()):
    row = con.execute(sql, params).fetchone()
    return row[0] if row else None


def print_table(headers: list[str], rows: list[list[str]], aligns: list[str]) -> None:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    def render(cells: list[str]) -> str:
        parts = []
        for i, cell in enumerate(cells):
            text = str(cell)
            parts.append(text.ljust(widths[i]) if aligns[i] == "l" else text.rjust(widths[i]))
        return "  ".join(parts)

    print(render(headers))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print(render(row))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Auditoria somente leitura das sessoes do OpenCode.",
    )
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Caminho do opencode.db")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Pasta dos relatorios")
    parser.add_argument("--top", type=int, default=15, help="Quantidade de sessoes no topo")
    parser.add_argument("--no-files", action="store_true", help="Nao grava CSV/JSON")
    parser.add_argument("--json", action="store_true", help="Imprime o resumo JSON no terminal")
    args = parser.parse_args()

    setup_stdout()
    db_path = Path(args.db).expanduser().resolve()
    con = connect(db_path)

    page_size = int(scalar(con, "PRAGMA page_size") or 0)
    page_count = int(scalar(con, "PRAGMA page_count") or 0)
    freelist = int(scalar(con, "PRAGMA freelist_count") or 0)
    auto_vacuum = int(scalar(con, "PRAGMA auto_vacuum") or 0)
    journal_mode = str(scalar(con, "PRAGMA journal_mode") or "?")
    live_bytes = max(0, page_count - freelist) * page_size
    free_bytes = freelist * page_size

    wal_path = Path(str(db_path) + "-wal")
    shm_path = Path(str(db_path) + "-shm")
    db_bytes = db_path.stat().st_size
    wal_bytes = wal_path.stat().st_size if wal_path.is_file() else 0
    shm_bytes = shm_path.stat().st_size if shm_path.is_file() else 0

    if not (table_exists(con, "session_v2") and table_exists(con, "session_message")):
        raise SystemExit(
            "ERRO: este banco nao tem as tabelas V2 esperadas "
            "(session_v2/session_message)."
        )

    rows = con.execute(
        """
        SELECT
            s.id,
            s.project_id,
            COALESCE(p.worktree, '') AS worktree,
            s.directory,
            s.title,
            s.parent_id,
            s.time_created,
            s.time_updated,
            s.time_archived,
            COALESCE(s.cost, 0) AS cost,
            COUNT(m.id) AS messages,
            COALESCE(SUM(LENGTH(CAST(m.data AS BLOB))), 0) AS bytes
        FROM session_v2 s
        LEFT JOIN project p ON p.id = s.project_id
        LEFT JOIN session_message m ON m.session_id = s.id
        GROUP BY s.id
        ORDER BY bytes DESC, s.time_updated DESC
        """
    ).fetchall()

    sessions = []
    for row in rows:
        item = dict(row)
        item["projeto"] = project_label(item["worktree"])
        sessions.append(item)

    v2_bytes = sum(s["bytes"] for s in sessions)
    v2_messages = sum(s["messages"] for s in sessions)
    subagents = sum(1 for s in sessions if s["parent_id"])
    archived = sum(1 for s in sessions if s["time_archived"])

    if table_exists(con, "session"):
        v1_sessions = int(scalar(con, "SELECT COUNT(*) FROM session") or 0)
        v1_in_v2 = int(
            scalar(
                con,
                """
                SELECT COUNT(*) FROM session s
                WHERE EXISTS (SELECT 1 FROM session_v2 v WHERE v.id = s.id)
                """,
            )
            or 0
        )
        v2_only = len(sessions) - v1_in_v2
    else:
        v1_sessions = 0
        v1_in_v2 = 0
        v2_only = len(sessions)

    v1_only = v1_sessions - v1_in_v2
    v1_messages = int(scalar(con, "SELECT COUNT(*) FROM message") or 0) if table_exists(con, "message") else 0
    v1_parts = int(scalar(con, "SELECT COUNT(*) FROM part") or 0) if table_exists(con, "part") else 0
    v1_message_bytes = int(
        scalar(con, "SELECT COALESCE(SUM(LENGTH(CAST(data AS BLOB))), 0) FROM message") or 0
    ) if v1_messages else 0
    v1_part_bytes = int(
        scalar(con, "SELECT COALESCE(SUM(LENGTH(CAST(data AS BLOB))), 0) FROM part") or 0
    ) if v1_parts else 0

    total_raw_bytes = v2_bytes + v1_message_bytes + v1_part_bytes

    now_ms = datetime.now(timezone.utc).timestamp() * 1000
    age_defs = [
        ("0-30 dias", 0, 30),
        ("31-60 dias", 31, 60),
        ("61-90 dias", 61, 90),
        ("91-180 dias", 91, 180),
        (">180 dias", 181, None),
    ]
    age_rows = []
    for label, low, high in age_defs:
        selected = []
        for s in sessions:
            if not s["time_updated"]:
                continue
            days = (now_ms - s["time_updated"]) / 86_400_000
            if days >= low and (high is None or days <= high):
                selected.append(s)
        age_rows.append(
            {
                "faixa": label,
                "sessoes": len(selected),
                "bytes": sum(s["bytes"] for s in selected),
            }
        )
    without_date = [s for s in sessions if not s["time_updated"]]
    if without_date:
        age_rows.append(
            {
                "faixa": "sem data",
                "sessoes": len(without_date),
                "bytes": sum(s["bytes"] for s in without_date),
            }
        )

    projects: dict[str, dict] = {}
    for s in sessions:
        key = s["worktree"] or "(sem projeto)"
        item = projects.setdefault(
            key,
            {"worktree": key, "sessoes": 0, "subagentes": 0, "bytes": 0},
        )
        item["sessoes"] += 1
        item["subagentes"] += 1 if s["parent_id"] else 0
        item["bytes"] += s["bytes"]
    project_rows = sorted(projects.values(), key=lambda x: x["bytes"], reverse=True)

    print("=== OpenCode - auditoria somente leitura ===")
    print(f"Banco:   {db_path}")
    print(
        f"Arquivo: {fmt_mb(db_bytes)} | WAL: {fmt_mb(wal_bytes)} | "
        f"SHM: {fmt_mb(shm_bytes)}"
    )
    print(
        f"Paginas: {fmt_num(page_count, 0)} x {fmt_num(page_size, 0)} bytes | "
        f"livres: {fmt_num(freelist, 0)} ({fmt_mb(free_bytes)})"
    )
    print(f"Compactado estimado: {fmt_mb(live_bytes)}")
    print(f"Journal: {journal_mode} | auto_vacuum: {auto_vacuum}")
    print()
    print(f"Sessoes V2: {len(sessions)} ({subagents} subagentes, {archived} arquivada(s))")
    print(
        f"V1 legado:  {v1_sessions} sessoes | {v1_messages} mensagens | "
        f"{v1_parts} partes"
    )
    print(
        f"IDs: {v1_in_v2} em V1+V2 | {v1_only} so V1 | {v2_only} so V2"
    )
    print()
    print("Dados por versao:")
    print(f"  V2 session_message: {fmt_mb(v2_bytes)}")
    print(f"  V1 message:         {fmt_mb(v1_message_bytes)}")
    print(f"  V1 part:            {fmt_mb(v1_part_bytes)}")
    print(f"  Total bruto:        {fmt_mb(total_raw_bytes)}")
    print()

    print("Por projeto (V2):")
    table_rows = []
    for p in project_rows:
        table_rows.append(
            [
                trunc(p["worktree"], 48),
                fmt_num(p["sessoes"], 0),
                fmt_num(p["subagentes"], 0),
                fmt_mb(p["bytes"]),
            ]
        )
    print_table(
        ["Projeto", "Sessoes", "Subag.", "Dados"],
        table_rows,
        ["l", "r", "r", "r"],
    )
    print()

    print(f"Top {args.top} sessoes por tamanho (V2):")
    top_rows = []
    for i, s in enumerate(sessions[: args.top], 1):
        top_rows.append(
            [
                str(i),
                trunc(s["title"], 42),
                trunc(s["projeto"], 24),
                fmt_ts(s["time_updated"]),
                fmt_mb(s["bytes"]),
            ]
        )
    print_table(
        ["#", "Sessao", "Projeto", "Atualizada", "Tamanho"],
        top_rows,
        ["r", "l", "l", "l", "r"],
    )
    print()

    print("Idade pela ultima atividade:")
    age_table = []
    for a in age_rows:
        age_table.append([a["faixa"], fmt_num(a["sessoes"], 0), fmt_mb(a["bytes"])])
    print_table(["Faixa", "Sessoes", "Dados"], age_table, ["l", "r", "r"])
    print()

    summary = {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "banco": str(db_path),
        "arquivo": {
            "db_bytes": db_bytes,
            "wal_bytes": wal_bytes,
            "shm_bytes": shm_bytes,
        },
        "paginas": {
            "page_size": page_size,
            "page_count": page_count,
            "freelist": freelist,
            "auto_vacuum": auto_vacuum,
            "journal_mode": journal_mode,
            "live_bytes": live_bytes,
            "free_bytes": free_bytes,
        },
        "dados": {
            "v2_bytes": v2_bytes,
            "v1_message_bytes": v1_message_bytes,
            "v1_part_bytes": v1_part_bytes,
            "total_raw_bytes": total_raw_bytes,
        },
        "sessoes": {
            "v2": len(sessions),
            "subagentes": subagents,
            "arquivadas": archived,
            "v2_mensagens": v2_messages,
            "v1": v1_sessions,
            "v1_em_v2": v1_in_v2,
            "v1_somente": v1_only,
            "v2_somente": v2_only,
            "v1_mensagens": v1_messages,
            "v1_partes": v1_parts,
        },
        "por_projeto": [
            {
                "worktree": p["worktree"],
                "sessoes": p["sessoes"],
                "subagentes": p["subagentes"],
                "bytes": p["bytes"],
                "mb": round(p["bytes"] / MB, 2),
            }
            for p in project_rows
        ],
        "top_sessoes": [
            {
                "id": s["id"],
                "titulo": s["title"],
                "projeto": s["projeto"],
                "worktree": s["worktree"],
                "criada": fmt_ts(s["time_created"]),
                "atualizada": fmt_ts(s["time_updated"]),
                "subagente": bool(s["parent_id"]),
                "arquivada": bool(s["time_archived"]),
                "mensagens": s["messages"],
                "bytes": s["bytes"],
                "mb": round(s["bytes"] / MB, 2),
            }
            for s in sessions[: args.top]
        ],
        "por_idade": [
            {
                "faixa": a["faixa"],
                "sessoes": a["sessoes"],
                "bytes": a["bytes"],
                "mb": round(a["bytes"] / MB, 2),
            }
            for a in age_rows
        ],
    }

    if not args.no_files:
        out_dir = Path(args.out).expanduser().resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        csv_path = out_dir / f"sessoes-{stamp}.csv"
        json_path = out_dir / f"resumo-{stamp}.json"

        with csv_path.open("w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=[
                    "session_id",
                    "projeto",
                    "worktree",
                    "diretorio",
                    "titulo",
                    "subagente",
                    "sessao_pai",
                    "arquivada",
                    "criada",
                    "atualizada",
                    "mensagens",
                    "bytes",
                    "mb",
                ],
            )
            writer.writeheader()
            for s in sessions:
                writer.writerow(
                    {
                        "session_id": s["id"],
                        "projeto": s["projeto"],
                        "worktree": s["worktree"],
                        "diretorio": s["directory"],
                        "titulo": s["title"],
                        "subagente": "sim" if s["parent_id"] else "nao",
                        "sessao_pai": s["parent_id"] or "",
                        "arquivada": "sim" if s["time_archived"] else "nao",
                        "criada": fmt_ts(s["time_created"]),
                        "atualizada": fmt_ts(s["time_updated"]),
                        "mensagens": s["messages"],
                        "bytes": s["bytes"],
                        "mb": round(s["bytes"] / MB, 2),
                    }
                )

        json_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print("Relatorios:")
        print(f"  CSV:  {csv_path}")
        print(f"  JSON: {json_path}")

    if args.json:
        if not args.no_files:
            print()
        print(json.dumps(summary, ensure_ascii=False, indent=2))

    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
