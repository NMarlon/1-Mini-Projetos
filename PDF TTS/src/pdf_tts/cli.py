"""CLI do PDF TTS."""

from __future__ import annotations

import argparse
import sys

from pdf_tts.assemble import run_assemble
from pdf_tts.build import BuildOptions, run_all, run_build, run_samples, run_status
from pdf_tts.doctor import run_doctor
from pdf_tts.lessons import run_segment
from pdf_tts.segment import run_extract, run_resegment
from pdf_tts.verify import run_verify


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
        ("verify", "Verifica MP3/M4B/SRT/capítulos/loudness."),
        ("all", "Executa extract + segment + build + verify de tudo."),
    ]:
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument("--project", choices=["all", "mkt120", "com150"], default="all")
        if name in {"build", "assemble", "all", "verify"}:
            cmd.add_argument("--lesson", default=None, help="Ex.: S01")
        if name in {"build", "assemble", "all"}:
            cmd.add_argument("--force", action="store_true", help="Re-sintetiza mesmo com cache.")
            cmd.add_argument("--resume", action="store_true", default=True, help="Retoma (padrão).")
        if name == "all":
            cmd.add_argument("--voice", default=None)
            cmd.add_argument("--rate", default=None)
            cmd.add_argument("--concurrency", type=int, default=None)
        if name == "verify":
            cmd.add_argument("--no-loudness", action="store_true")
            cmd.add_argument("--no-silence", action="store_true")

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
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        return run_doctor()
    if args.command == "extract":
        return run_extract(args.project)
    if args.command == "resegment":
        return run_resegment(args.project)
    if args.command == "segment":
        return run_segment(args.project)
    if args.command == "build":
        return run_build(
            BuildOptions(
                project=args.project,
                lesson=args.lesson,
                voice=args.voice,
                rate=args.rate,
                concurrency=args.concurrency,
                force=args.force,
                dry_run=args.dry_run,
                no_assemble=args.no_assemble,
            )
        )
    if args.command == "status":
        return run_status(args.project)
    if args.command == "samples":
        return run_samples()
    if args.command == "assemble":
        return run_assemble(args.project, args.lesson)
    if args.command == "verify":
        return run_verify(
            args.project,
            lesson=args.lesson,
            check_loudness=not args.no_loudness,
            check_silence=not args.no_silence,
        )
    if args.command == "all":
        return run_all(
            args.project,
            lesson=args.lesson,
            voice=args.voice,
            rate=args.rate,
            concurrency=args.concurrency,
        )

    print(f"'{args.command}' ainda não implementado nesta etapa.")
    print("Veja DOCS/06-TASKS.md para o próximo passo.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
