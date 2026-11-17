"""Limpeza de texto extraído de PDF."""

from __future__ import annotations

import re

LIGATURES = {
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
    "\ufb05": "st",
    "\ufb06": "st",
}

PUA_RANGES = (
    (0xE000, 0xF8FF),
    (0xF0000, 0xFFFFD),
    (0x100000, 0x10FFFD),
)

ZERO_WIDTH = "\u200b\u200c\u200d\u200e\u200f\ufeff\u00ad"
SPACE_CHARS = "\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u202f\u205f\u3000"

SKIP_LINE_PATTERNS = [
    re.compile(r"^This publication is currently unlisted", re.IGNORECASE),
    re.compile(r"^Filter content", re.IGNORECASE),
    re.compile(r"^Acesso gratuito em", re.IGNORECASE),
    re.compile(r"^Clique aqui para ver as respostas\.?$", re.IGNORECASE),
    re.compile(r"^https?://\S+$", re.IGNORECASE),
    re.compile(r"^www\.\S+$", re.IGNORECASE),
]

# Texto pequeno que é apenas crédito/fonte, não conteúdo.
SMALL_PRINT_DROP_PATTERNS = [
    re.compile(r"^(Fonte|Atributo|Fotografia|Copyright|©|CC BY|Wikimedia|Pexels|Pixabay|Unsplash|D&C)\b", re.IGNORECASE),
    re.compile(r"^O conteúdo foi adaptado", re.IGNORECASE),
    re.compile(r"^Este material foi adaptado", re.IGNORECASE),
]

SECTION_PATTERNS = [
    ("sxx", re.compile(r"^S0\d\b")),
    ("introduction", re.compile(r"^Introdução\b")),
    ("conclusion", re.compile(r"^Conclusão\b")),
    ("summary", re.compile(r"^Resumo\b")),
    ("vocabulary", re.compile(r"^(Lista de Vocabulário|Vocabulário|Glossário)\b")),
    ("study_tips", re.compile(r"^Dicas de [Ee]studo\b")),
    ("exercises", re.compile(r"^Exercícios\b")),
    ("quiz", re.compile(r"^Verificação de Conhecimento\b")),
    ("project", re.compile(r"^Projeto Final\b")),
    ("case_study", re.compile(r"^Estudo de [Cc]aso\b")),
    ("discussion", re.compile(r"^Discussão\b")),
    ("task", re.compile(r"^Tarefa\b")),
    ("spiritual", re.compile(r"^(A Mão do Senhor|Mantenha o Ím[ée]to Espiritual)\b")),
    ("references", re.compile(r"^(Referências|Bibliografia)\b")),
]

CAPTION_RE = re.compile(r"^(Imagem|Figura|Tabela|Quadro|Gráfico)\s*\d", re.IGNORECASE)
WEEK_RE = re.compile(r"^Semana\s*0?(\d+)\s*[:\-–—]", re.IGNORECASE)


def remove_pua(text: str) -> str:
    chars = []
    for char in text:
        code = ord(char)
        if any(start <= code <= end for start, end in PUA_RANGES):
            continue
        chars.append(char)
    return "".join(chars)


def clean_text(text: str) -> str:
    """Normaliza caracteres e espaços, preservando pontuação e conteúdo."""
    for source, target in LIGATURES.items():
        text = text.replace(source, target)
    text = remove_pua(text)
    for char in ZERO_WIDTH:
        text = text.replace(char, "")
    for char in SPACE_CHARS:
        text = text.replace(char, " ")
    text = text.replace("\r", "\n")
    text = text.replace("\t", " ")
    # Caracteres de controle (exceto newline)
    text = "".join(ch for ch in text if ch == "\n" or ord(ch) >= 32)
    text = re.sub(r"[ ]{2,}", " ", text)
    text = re.sub(r"\s*\n\s*", " ", text)
    return text.strip()


def clean_cell(text: str | None, is_label: bool = False) -> str:
    if not text:
        return ""
    raw = str(text)
    if is_label:
        joined = raw.replace("\n", " ")
    else:
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        if not lines:
            return ""
        parts = [lines[0].lstrip("-–—• ").strip()]
        for line in lines[1:]:
            if line.startswith(("-", "–", "—", "•")):
                parts.append("; " + line.lstrip("-–—• ").strip())
            else:
                parts.append(" " + line)
        joined = "".join(parts)
    text = clean_text(joined)
    text = text.replace("//", "/")
    text = re.sub(r"\s*;\s*", "; ", text)
    text = re.sub(r";\s*;+", ";", text)
    text = re.sub(r"(^|;)\s*[\-–—•]\s*", r"\1 ", text)
    return text.strip(" ;")


def strip_urls(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bwww\.\S+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b[\w.+-]+@[\w.-]+\.\w+\b", "", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def is_skip_line(text: str) -> bool:
    stripped = text.strip()
    return any(pattern.search(stripped) for pattern in SKIP_LINE_PATTERNS)


def is_caption(text: str) -> bool:
    return bool(CAPTION_RE.match(text.strip()))


def is_small_print_drop(text: str) -> bool:
    stripped = text.strip()
    return any(pattern.search(stripped) for pattern in SMALL_PRINT_DROP_PATTERNS)


def strip_attribution(text: str) -> str:
    """Remove créditos/licenças de legendas, preservando o conteúdo."""
    text = re.sub(r"\s*\bCC BY[^.]*\.?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*\bWikimedia Commons[^.]*\.?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*(Fonte:\s*\S+.*|Atributo:.*|Pexels[^.]*\.?|Pixabay[^.]*\.?|Unsplash[^.]*\.?)$", "", text, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", text).strip(" .-")


def is_section_heading(text: str) -> tuple[bool, str]:
    stripped = text.strip()
    for name, pattern in SECTION_PATTERNS:
        if pattern.match(stripped):
            return True, name
    if WEEK_RE.match(stripped):
        return True, "week"
    return False, ""


def is_week_title(text: str) -> bool:
    return bool(WEEK_RE.match(text.strip()))


def is_page_number(text: str) -> bool:
    stripped = text.strip()
    return bool(re.fullmatch(r"\d{1,4}", stripped))


def is_url_only(text: str) -> bool:
    stripped = text.strip()
    return bool(re.fullmatch(r"(https?://\S+|www\.\S+)", stripped, flags=re.IGNORECASE))


def has_letter(text: str) -> bool:
    return any(char.isalpha() for char in text)


def normalize_heading_key(text: str) -> str:
    text = clean_text(text).lower()
    text = re.sub(r"[^a-z0-9áàâãéêíóôõúç]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def join_lines(lines: list[str]) -> str:
    """Junta linhas de um mesmo bloco, resolvendo hifenização de quebra."""
    cleaned = [clean_text(line) for line in lines if clean_text(line)]
    if not cleaned:
        return ""
    result = cleaned[0]
    for line in cleaned[1:]:
        if result.endswith("-") and line[:1].islower():
            prefix = result[:-1].split()[-1].lower() if result[:-1].split() else ""
            keep_hyphen = prefix in {
                "e",
                "pré",
                "pós",
                "bem",
                "mal",
                "auto",
                "micro",
                "macro",
                "anti",
                "co",
                "re",
                "sub",
                "super",
                "ultra",
                "vice",
                "ex",
                "sem",
                "pró",
            } or re.match(r"^(lo|la|los|las|me|te|se|nos|vos|lhe|lhes|o|a|os|as)\b", line, re.IGNORECASE)
            if keep_hyphen:
                result = result + line
            else:
                result = result[:-1] + line
        else:
            result = result + " " + line
    return re.sub(r"\s{2,}", " ", result).strip()


def reference_score(text: str) -> int:
    """Heurística para identificar linhas de bibliografia/referência."""
    score = 0
    stripped = text.strip()
    if re.match(r"^\d{1,2}\s", stripped):
        score += 1
    if re.search(r"\b(19|20)\d{2}\b", stripped):
        score += 2
    if re.search(r"Conferência Geral", stripped, re.IGNORECASE):
        score += 2
    if re.search(
        r"\b(Journal|Press|Publishing|University|SAGE|Pearson|Allyn|Bacon|Routledge|McGraw)\b",
        stripped,
        re.IGNORECASE,
    ):
        score += 2
    if re.search(r"\b(pág|pp?\.|ed\.|vol\.|no\.|ISBN|trans\.|Eds?\.)\b", stripped, re.IGNORECASE):
        score += 1
    if re.search(r"https?://", stripped):
        score += 1
    if re.search(r"^[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+,\s+[A-Z]\.", stripped):
        score += 2
    if re.search(
        r"^(\d{1,2}\s+)?(Éter|Mateus|Marcos|Lucas|João|Gênesis|Êxodo|Isaías|Salmos)\s+\d+[:.]\d+",
        stripped,
        re.IGNORECASE,
    ):
        score += 3
    if re.match(r"^\d{1,2}\s*$", stripped):
        score += 1
    return score


def looks_like_reference(text: str) -> bool:
    stripped = text.strip()
    if re.match(
        r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.\s*\d{1,2},?\s*(19|20)\d{2}\)?\.?$",
        stripped,
        re.IGNORECASE,
    ):
        return True
    if len(stripped) > 300:
        return False
    score = reference_score(stripped)
    starts_number = bool(re.match(r"^\d{1,2}\s", stripped))
    # Entradas numeradas de bibliografia são referências mesmo com vários pontos.
    if starts_number and score >= 3:
        return True
    # Um parágrafo com duas ou mais frases é conteúdo, não uma entrada de bibliografia.
    if len(re.findall(r"[.!?]\s+", stripped)) >= 2:
        return False
    return score >= 4 and len(stripped) <= 250


def collapse_blank_lines(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text)
