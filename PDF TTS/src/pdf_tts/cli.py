"""CLI do PDF TTS."""

from __future__ import annotations

import argparse
import sys

from pdf_tts.doctor import run_doctor
from pdf_tts.segment import run_extract, run_resegment


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdf-tts",
        description="Pipeline de PDF para audiolivro em pt-BR com Edge TTS.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="Verifica Python, FFmpeg, Edge TTS, PDFs e disco.")

    for name, help_text in [
        ("extract", "Extrai e limpa o texto dos PDFs."),
        ("resegment", "Reestrutura a partir de blocks.jsonl (debug, sem reabrir PDFs)."),
        ("segment", "Normaliza e divide o texto em aulas S01..S07."),
        ("assemble", "Monta MP3/M4B/SRT a partir dos chunks sintetizados."),
        ("samples", "Gera amostras de voz."),
        ("status", "Mostra o estado do build."),
        ("all", "Executa extract + segment + build de tudo."),
    ]:
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument("--project", choices=["all", "mkt120", "com150"], default="all")
        if name in {"build", "assemble", "all"}:
            cmd.add_argument("--lesson", default=None, help="Ex.: S01")
            cmd.add_argument("--force", action="store_true", help="Re-sintetiza mesmo com cache.")
            cmd.add_argument("--resume", action="store_true", default=True, help="Retoma (padrão).")

    build = sub.add_parser("build", help="Sintetiza e monta o áudio.")
    build.add_argument("--project", choices=["all", "mkt120", "com150"], default="all")
    build.add_argument("--lesson", default=None, help="Ex.: S01")
    build.add_argument("--voice", default=None)
    build.add_argument("--rate", default=None)
    build.add_argument("--concurrency", type=int, default=None)
    build.add_argument("--force", action="store_true")
    build.add_argument("--dry-run", action="store_true")
    build.add_argument("--no-assemble", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        return run_doctor()
    if args.command == "extract":
        return run_extract(args.project)
    if args.command == "resegment":
        return run_resegment(args.project)

    print(f"'{args.command}' ainda não implementado nesta etapa.")
    print("Veja DOCS/06-TASKS.md para o próximo passo.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
