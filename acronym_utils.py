# acronym_utils.py
import re
from typing import Optional, List, Tuple

# Stoppwortliste für DE+EN, damit Ausdrücke wie "was / ist / der" und ähnliche nicht als solche erfasst werden.
ACRONYM_STOP = {
    # DE
    "was", "ist", "das", "der", "die", "und", "ein", "eine", "mit", "im", "in",
    "de", "en", "von",
    # EN
    "what", "is", "are", "was", "were",
    "the", "and", "for", "to", "of", "or", "an", "a",
    "on", "in", "at", "by", "with",
    "please", "explain", "define", "about",
}

# Eine Reihe eindeutig „wichtiger“ Begriffe (CAN, OEM, CAL, RASIC, ISO/SAE usw.).
PREFERRED_TERMS = {
    "CAN", "CAN-FD", "OEM", "RASIC", "CAL", "ISO", "SAE",
}


def detect_acronym(text: str) -> Optional[str]:
    """
    Gibt das wahrscheinlichste Schlüsselwort/die wahrscheinlichste Abkürzung (in Großbuchstaben) aus dem Text zurück.
    Gleiche Logik für die Abfrage und die Vektorspeicherung:
        - Ignoriert Sonderwörter (was, ist, der, war, und, ist, ...)
        - Gibt einen Bonus:
        * für das Vorhandensein von Ziffern (21434)
        * für GROSSBUCHSTABEN (CAN, OEM)
        * für bevorzugte Begriffe (CAN, CAN-FD, OEM, RASIC, CAL, ISO, SAE)
        - Bei Punktgleichheit wird der Wert links neben der Frage ausgewählt.
    """
    if not text:
        return None

    tokens = re.findall(r"\b[A-Za-zÄÖÜäöüß0-9\-/]{2,20}\b", text)
    if not tokens:
        return None

    candidates: List[Tuple[int, int, str]] = []  # (score, index, TERM)

    for idx, tok in enumerate(tokens):
        norm = tok.upper()
        if norm.lower() in ACRONYM_STOP:
            continue

        score = 0

        # 1) Begriffe mit Zahlen (21434, ISO/SAE 21434) – wichtige Standards
        if any(ch.isdigit() for ch in norm):
            score += 2

        # 2) Vollständig großgeschriebene – typische Abkürzungen: CAN, OEM, CAL, RASIC
        if norm.isupper():
            score += 1

        # 3) Eindeutig wichtige Auto-Terme – großer Bonus
        if norm in PREFERRED_TERMS:
            score += 3

        candidates.append((score, idx, norm))

    if not candidates:
        return None

    # Sortieren: zuerst nach Score (absteigend), bei Gleichstand nach Position (je weiter LINKS, desto besser)
    candidates.sort(key=lambda x: (-x[0], x[1]))
    best_score, _, best_term = candidates[0]

    # Wenn alle Kandidaten Score=0 haben, sind es nur normale Wörter → besser None zurückgeben
    if best_score <= 0:
        return None

    return best_term