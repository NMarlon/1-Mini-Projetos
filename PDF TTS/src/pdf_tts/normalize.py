"""Normalização de texto para fala em português brasileiro."""

from __future__ import annotations

import re
from typing import Any

from num2words import num2words

from pdf_tts.clean import clean_text

MONTHS = [
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
]

ORDINAL_FEMININE = {
    "primeiro": "primeira",
    "segundo": "segunda",
    "terceiro": "terceira",
    "quarto": "quarta",
    "quinto": "quinta",
    "sexto": "sexta",
    "sétimo": "sétima",
    "oitavo": "oitava",
    "nono": "nona",
    "décimo": "décima",
    "vigésimo": "vigésima",
    "trigésimo": "trigésima",
    "quadragésimo": "quadragésima",
    "quinquagésimo": "quinquagésima",
    "sexagésimo": "sexagésima",
    "centésimo": "centésima",
    "milésimo": "milésima",
}

ABBREVIATIONS = [
    (r"\bp\.\s*(?=\d)", "página "),
    (r"\bpp\.\s*(?=\d)", "páginas "),
    (r"\bpág\.\s*(?=\d)", "página "),
    (r"\bart\.\s*(?=\d)", "artigo "),
    (r"\bn[º°]\s*(?=\d)", "número "),
    (r"\b§\s*(?=\d)", "seção "),
    (r"\bp\.ex\.", "por exemplo"),
    (r"\bP\.ex\.", "por exemplo"),
    (r"\betc\.", "etcétera"),
    (r"\bvs\.", "versus"),
    (r"\bi\.e\.", "isto é"),
    (r"\be/ou\b", "e ou"),
    (r"\bDr\.", "doutor"),
    (r"\bDra\.", "doutora"),
    (r"\bSr\.", "senhor"),
    (r"\bSra\.", "senhora"),
    (r"\bProf\.", "professor"),
    (r"\bProfa\.", "professora"),
    (r"\bD&C\b", "Doutrina e Convênios"),
]


class _Protector:
    """Troca expressões já convertidas por tokens para não reprocessá-las."""

    def __init__(self) -> None:
        self.items: list[str] = []

    def protect(self, value: str) -> str:
        token = f"\x00{chr(0xE000 + len(self.items))}\x00"
        self.items.append(value)
        return token

    def restore(self, text: str) -> str:
        for index, value in enumerate(self.items):
            text = text.replace(f"\x00{chr(0xE000 + index)}\x00", value)
        return text


def _num(value: int | float) -> str:
    try:
        return num2words(int(value), lang="pt_BR")
    except (ValueError, TypeError, NotImplementedError):
        return str(value)


def _ordinal(value: int, feminine: bool = False) -> str:
    try:
        word = num2words(int(value), to="ordinal", lang="pt_BR")
    except (ValueError, TypeError, NotImplementedError):
        return str(value)
    if feminine:
        parts = [ORDINAL_FEMININE.get(part, part) for part in word.split()]
        return " ".join(parts)
    return word


def _parse_br_int(value: str) -> int:
    return int(value.replace(".", "").replace(" ", ""))


def _parse_number(value: str) -> float:
    text = value.strip().replace(" ", "")
    if not text:
        return 0.0
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        parts = text.split(",")
        if len(parts[-1]) == 3 and len(parts) > 1:
            text = text.replace(",", "")
        else:
            text = text.replace(",", ".")
    elif "." in text:
        parts = text.split(".")
        if len(parts[-1]) == 3:
            text = text.replace(".", "")
    try:
        return float(text)
    except ValueError:
        return 0.0


def _currency(value: float, unit: str) -> str:
    integer = int(value)
    cents = int(round((value - integer) * 100))
    if unit == "real":
        if integer == 0:
            return f"{_num(cents)} centavos" if cents != 1 else "um centavo"
        text = f"{_num(integer)} {'real' if integer == 1 else 'reais'}"
        if cents:
            text += f" e {_num(cents)} {'centavo' if cents == 1 else 'centavos'}"
        return text
    if integer == 0:
        return f"{_num(cents)} centavos" if cents != 1 else "um centavo"
    text = f"{_num(integer)} {'dólar' if integer == 1 else 'dólares'}"
    if cents:
        text += f" e {_num(cents)} {'centavo' if cents == 1 else 'centavos'}"
    return text


def _decimal(value: str) -> str:
    normalized = value.replace(".", ",")
    integer_part, _, fraction = normalized.partition(",")
    integer_text = _num(_parse_br_int(integer_part)) if integer_part else "zero"
    if not fraction:
        return integer_text
    if fraction.startswith("0"):
        fraction_text = " ".join(_num(int(digit)) for digit in fraction)
    else:
        fraction_text = _num(int(fraction))
    return f"{integer_text} vírgula {fraction_text}"


def _date(day: str, month: str, year: str | None) -> str:
    try:
        day_number = int(day)
        month_number = int(month)
    except ValueError:
        return f"{day}/{month}"
    if not (1 <= day_number <= 31 and 1 <= month_number <= 12):
        text = f"{_num(day_number)} dividido por {_num(month_number)}"
        if year:
            text += f" de {_num(int(year))}"
        return text
    text = f"{_num(day_number)} de {MONTHS[month_number - 1]}"
    if year:
        year_number = int(year)
        if len(year) == 2:
            year_number = 2000 + year_number if year_number <= 50 else 1900 + year_number
        text += f" de {_num(year_number)}"
    return text


def _time(hours: str, minutes: str | None) -> str:
    hour_number = int(hours)
    hour_text = _num(hour_number)
    if hour_number == 1:
        base = "uma hora"
    else:
        base = f"{hour_text} horas"
    if not minutes:
        return base
    minute_number = int(minutes)
    if minute_number == 0:
        return base
    return f"{base} e {_num(minute_number)} {'minuto' if minute_number == 1 else 'minutos'}"


def _range(start: str, end: str) -> str:
    return f"{_num(int(start))} a {_num(int(end))}"


def _apply_abbreviations(text: str) -> str:
    for pattern, replacement in ABBREVIATIONS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def _apply_symbols(text: str) -> str:
    text = re.sub(r"\bB\s*/\s*P\b", "B dividido por P", text)
    text = text.replace("&", " e ")
    text = text.replace("→", " leva a ")
    text = text.replace("+", " mais ")
    text = text.replace("=", " igual a ")
    text = text.replace("§", " seção ")
    text = text.replace("•", "; ")
    text = re.sub(r"\s*/\s*", " ou ", text)
    text = text.replace("%", " por cento ")
    return text


def strip_list_marker(text: str) -> str:
    text = re.sub(r"^\s*\d{1,2}[.)]\s+", "", text)
    text = re.sub(r"^\s*[-–—•]\s+", "", text)
    return text.strip()


def normalize_numbers(text: str) -> str:
    protector = _Protector()

    text = re.sub(
        r"R\$\s*([\d.]*\d)(?:,(\d{1,2}))?",
        lambda match: protector.protect(
            _currency(_parse_br_int(match.group(1)) + (int(match.group(2) or 0) / 100.0), "real")
        ),
        text,
    )
    text = re.sub(
        r"US\$\s*([\d.,]*\d)",
        lambda match: protector.protect(_currency(_parse_number(match.group(1)), "dollar")),
        text,
    )
    text = re.sub(
        r"\$\s*([\d.,]*\d)",
        lambda match: protector.protect(_currency(_parse_number(match.group(1)), "dollar")),
        text,
    )
    text = re.sub(
        r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b",
        lambda match: protector.protect(_date(match.group(1), match.group(2), match.group(3))),
        text,
    )
    text = re.sub(
        r"\b(\d{1,2})h(\d{2})?\b",
        lambda match: protector.protect(_time(match.group(1), match.group(2))),
        text,
    )
    text = re.sub(
        r"\b(\d{1,4})\s*[-–—]\s*(\d{1,4})\b",
        lambda match: protector.protect(_range(match.group(1), match.group(2))),
        text,
    )
    text = re.sub(
        r"\b(\d{1,3})\s*([ºª])",
        lambda match: protector.protect(_ordinal(int(match.group(1)), feminine=(match.group(2) == "ª"))),
        text,
    )
    text = re.sub(
        r"\b(\d{1,2}[.,]\d{1,2})\s*%",
        lambda match: protector.protect(_decimal(match.group(1).replace(".", ",")) + " por cento"),
        text,
    )
    text = re.sub(
        r"\b(\d+),(\d{1,3})\b",
        lambda match: protector.protect(_decimal(f"{match.group(1)},{match.group(2)}")),
        text,
    )
    text = re.sub(
        r"\b(\d+)\.(\d{1,2})(?!\d)",
        lambda match: protector.protect(f"{_num(int(match.group(1)))} ponto {_num(int(match.group(2)))}"),
        text,
    )
    text = re.sub(
        r"\b(\d{1,3}(?:\.\d{3})+)\b",
        lambda match: protector.protect(_num(int(match.group(1).replace(".", "")))),
        text,
    )
    text = re.sub(
        r"\b(\d{1,3})\s*%",
        lambda match: protector.protect(f"{_num(int(match.group(1)))} por cento"),
        text,
    )
    text = re.sub(
        r"\b(\d{1,7})\b",
        lambda match: protector.protect(_num(int(match.group(1)))),
        text,
    )
    return protector.restore(text)


def normalize_text(text: str, lexicon: dict[str, Any], kind: str = "paragraph") -> str:
    text = clean_text(text)
    if not text:
        return ""
    if kind == "list_item":
        text = strip_list_marker(text)
    text = re.sub(r"(?<=\w)_(?=\w)", " ", text)

    for item in sorted(lexicon.get("replacements", []), key=lambda item: len(item["pattern"]), reverse=True):
        try:
            flags = 0 if item.get("case_sensitive") else re.IGNORECASE
            text = re.sub(item["pattern"], item["replace"], text, flags=flags)
        except re.error:
            continue

    text = _apply_abbreviations(text)
    text = re.sub(r"(?<=\w)_(?=\w)", " ", text)
    text = re.sub(r"_{2,}", "lacuna", text)
    text = re.sub(r"(?<!\w)_{1}(?!\w)", "lacuna", text)
    text = re.sub(r"(?<=[a-záéíóúâêôãõç])\d{1,3}(?=[.,;:!?])", "", text)
    text = re.sub(r"(?<=[a-záéíóúâêôãõç])\d{1,3}(?=\s+[a-záéíóúâêôãõç])", "", text)
    text = re.sub(r"(?<=[A-Za-zÁ-ÿ]{2})(\d{1,4})", r" \1", text)
    text = text.replace("…", "...")
    text = re.sub(
        r"\b(Doutrina e Convênios|Éter|Mateus|Marcos|Lucas|João|Provérbios|Néfi|Gênesis|Êxodo|Isaías|Salmos)"
        r"\s+(\d+)\s*[:.]\s*(\d+)",
        lambda match: (
            f"{match.group(1)}, capítulo {_num(int(match.group(2)))}, "
            f"versículo {_num(int(match.group(3)))}"
        ),
        text,
    )
    text = normalize_numbers(text)
    text = _apply_symbols(text)

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([,;:])(?=[^\s\d])", r"\1 ", text)
    text = re.sub(r"\.(?=[A-Za-zÀ-ÿ])", ". ", text)
    text = re.sub(r"\.\s*:", ":", text)
    text = re.sub(r"\.{3,}", "...", text)
    text = re.sub(r"\.\s*\.\s*\.", "...", text)
    text = re.sub(r"([!?])\1+", r"\1", text)
    text = re.sub(r"([.!?][\"'”’])\.$", r"\1", text)
    text = text.strip(" ;")
    text = re.sub(r"\s{2,}", " ", text)
    if text and not re.search(r"[.!?][\"'”’]?$", text):
        text += "."
    return text
