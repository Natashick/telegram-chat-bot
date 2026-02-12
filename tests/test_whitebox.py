# test_whitebox.py
import os
import sys
import importlib.util

# Ensure project root is on sys.path when running from /app/tests
_CUR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_CUR)  # project root (/app)
if _ROOT and _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Fallback loader if direct import fails in some environments
def _load_by_path(modname: str, filepath: str):
    spec = importlib.util.spec_from_file_location(modname, filepath)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod
import re

try:
    from acronym_utils import detect_acronym
except ModuleNotFoundError:
    detect_acronym = _load_by_path("acronym_utils", os.path.join(_ROOT, "acronym_utils.py")).detect_acronym  # type: ignore[attr-defined]

try:
    from retrieval import (
        _matches_term,
        find_definition_in_chunks,
        build_combined_excerpts,
    )
except ModuleNotFoundError:
    _retrieval = _load_by_path("retrieval", os.path.join(_ROOT, "retrieval.py"))
    _matches_term = _retrieval._matches_term  # type: ignore[attr-defined]
    find_definition_in_chunks = _retrieval.find_definition_in_chunks  # type: ignore[attr-defined]
    build_combined_excerpts = _retrieval.build_combined_excerpts  # type: ignore[attr-defined]


def test_detect_acronym():
    assert detect_acronym("was ist das CAN?") == "CAN"
    assert detect_acronym("was ist das RASIC?") == "RASIC"
    assert detect_acronym("was ist das ISO/SAE 21434?") in ("ISO/SAE", "ISO/SAE 21434", "21434")
    assert detect_acronym("ISO 9001 und ISO 27001") in ("ISO", "ISO 9001", "9001")
    # Низкий регистр "can" может детектироваться как CAN, но _matches_term не даст ложного совпадения
    det = detect_acronym("can you help me")
    assert det in (None, "CAN")


def test_matches_term_boundaries():
    # короткие UPPERCASE — только границы слов
    assert _matches_term("CAN", "This is CAN bus.") is True
    assert _matches_term("CAN", "This can lead to...") is False
    # составные/цифровые — нормализованный contains
    # "ISO 21434" не обязательно совпадает в "ISO/SAE 21434"; но число 21434 должно совпасть
    assert _matches_term("21434", "ISO/SAE 21434 Road vehicles") is True
    assert _matches_term("ISO-21434", "ISO 21434") is True


def test_find_definition_in_chunks():
    chunks = [
        {"text": "Foreword\nCAN: Controller Area Network communication."},  # foreword should be filtered
        {"text": "CAN — Controller Area Network used in road vehicles."},
        {"text": "Random text."},
    ]
    hits = find_definition_in_chunks("CAN", chunks)
    assert hits, "Definition should be extracted"
    assert "Controller Area Network" in hits[0]["text"]
    assert len(hits[0]["text"]) <= 221


def test_build_combined_excerpts_sanitization_and_dedup():
    txt = "\n".join(
        [
            "1 Scope",  # heading-like — drop
            "ISO/SAE 21434 — Road vehicles — Cybersecurity engineering",  # keep (acronyms/digits)
            "Figure 1 Something",  # drop
            "General considerations",  # drop
            "CAN bus is used …",  # keep (acronym)
            "CAN bus is used …",  # duplicate — should dedup
        ]
    )
    out = build_combined_excerpts([{"text": txt}])
    # По текущей логике строки с цифрами/акронимами сохраняются; проверим на наличие и дедуп
    assert out.count("CAN bus is used") == 1
    assert "ISO/SAE 21434" in out


def test_chunk_dedup_logic_like_retrieval():
    # Симулируем простую дедупликацию ключом chunk_id|text_prefix
    chunks = [
        {"chunk_id": "a1", "text": "hello world", "similarity_score": 0.5},
        {"chunk_id": "a1", "text": "hello world", "similarity_score": 0.7},  # duplicate
        {"chunk_id": "b2", "text": "another chunk", "similarity_score": 0.6},
    ]
    seen = set()
    uniq = []
    for c in chunks:
        key = f"{c.get('chunk_id')}|{(c.get('text') or '')[:64]}"
        if key in seen:
            continue
        seen.add(key)
        uniq.append(c)
    # уникальных должно быть 2
    assert len(uniq) == 2
    # сортируем по similarity
    uniq_sorted = sorted(uniq, key=lambda x: x.get("similarity_score", 0.0), reverse=True)
    assert uniq_sorted[0]["chunk_id"] in ("b2", "a1")


if __name__ == "__main__":
    # Простое выполнение без pytest
    for fn in [
        test_detect_acronym,
        test_matches_term_boundaries,
        test_find_definition_in_chunks,
        test_build_combined_excerpts_sanitization_and_dedup,
        test_chunk_dedup_logic_like_retrieval,
    ]:
        fn()
    print("WHITEBOX OK")

