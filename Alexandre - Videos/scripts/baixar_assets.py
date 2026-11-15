"""Baixa assets livres (Wikimedia Commons) e registra os créditos.

Uso:
    python scripts/baixar_assets.py            # baixa o que falta
    python scripts/baixar_assets.py --forcar   # baixa tudo de novo

Gera/atualiza `assets/CREDITOS.md` com autor + licença de cada arquivo
(obrigatório quando a licença é CC BY — regra do projeto: só CC0/CC BY, sem
material com direitos reservados).
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "AlexandreVideosPipeline/1.0 (projeto local de clips)"}

# (título no Commons, destino relativo à raiz do projeto)
MANIFEST = [
    ("File:72844 lonemonk approx-800-laughter-and-clapter-1.wav",
     "assets/sfx/risada.wav"),
    ("File:F1-Race-Crowd-Applause-Air-Horns.wav",
     "assets/sfx/aplausos_airhorn.wav"),
    ("File:Drum Roll Intro.ogg", "assets/sfx/drumroll.ogg"),
    ("File:Sonic-boom-massive-sound.ogg", "assets/sfx/boom.ogg"),
    ("File:Loyalty Freak Music - 03 - After Party.ogg",
     "assets/music/after_party.ogg"),
]

API = "https://commons.wikimedia.org/w/api.php"


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def metadados(titulo: str) -> dict:
    q = urllib.parse.urlencode({
        "action": "query", "titles": titulo, "prop": "imageinfo",
        "iiprop": "extmetadata", "format": "json",
    })
    data = json.loads(get(f"{API}?{q}").decode("utf-8"))
    page = next(iter(data["query"]["pages"].values()))
    em = page["imageinfo"][0]["extmetadata"]

    def v(chave: str) -> str:
        raw = em.get(chave, {}).get("value", "")
        raw = re.sub(r"<[^>]+>", "", raw)
        return html.unescape(raw).strip()

    return {"titulo": titulo, "autor": v("Artist") or "desconhecido",
            "licenca": v("LicenseShortName") or "desconhecida",
            "url": em.get("LicenseUrl", {}).get("value", ""),
            "pagina": f"https://commons.wikimedia.org/wiki/"
                      f"{urllib.parse.quote(titulo.replace(' ', '_'))}"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--forcar", action="store_true")
    args = ap.parse_args()

    creditos = ["# Créditos de assets (licenças)", "",
                "> Gerado por `scripts/baixar_assets.py`. Só material CC0/CC BY.",
                "", "| Arquivo | Autor | Licença | Fonte |", "|---|---|---|---|"]
    falhas = []
    for titulo, destino in MANIFEST:
        alvo = ROOT / destino
        alvo.parent.mkdir(parents=True, exist_ok=True)
        if alvo.exists() and not args.forcar:
            print(f"já existe: {destino}")
        else:
            url = ("https://commons.wikimedia.org/wiki/Special:FilePath/"
                   + urllib.parse.quote(titulo.replace(" ", "_")))
            try:
                blob = get(url)
                alvo.write_bytes(blob)
                print(f"baixado: {destino} ({len(blob)} bytes)")
            except Exception as e:  # noqa: BLE001
                print(f"FALHA {destino}: {e}")
                falhas.append(destino)
                continue
        try:
            m = metadados(titulo)
            lic = f"[{m['licenca']}]({m['url']})" if m["url"] else m["licenca"]
            creditos.append(f"| `{destino}` | {m['autor']} | {lic} | "
                            f"[Commons]({m['pagina']}) |")
        except Exception as e:  # noqa: BLE001
            print(f"AVISO: metadados de {titulo}: {e}")

    (ROOT / "assets" / "CREDITOS.md").write_text("\n".join(creditos) + "\n",
                                                 encoding="utf-8")
    print(f"OK -> assets/CREDITOS.md ({len(creditos) - 5} itens)")
    if falhas:
        sys.exit(f"falhas: {falhas}")


if __name__ == "__main__":
    main()
