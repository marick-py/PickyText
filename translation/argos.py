"""
Argos Translate local fallback (optional install).
Install: pip install argostranslate
"""
from __future__ import annotations


def translate_sync(text: str, source: str, target: str) -> str:
    try:
        from argostranslate import package, translate
    except ImportError as exc:
        raise RuntimeError(
            "argostranslate is not installed. "
            "Install it with: pip install argostranslate"
        ) from exc

    installed = translate.get_installed_languages()

    # Argos does not support "auto" detection — fall back to English
    if source == "auto":
        source = "en"

    src_lang = next((l for l in installed if l.code == source), None)
    if src_lang is None:
        raise ValueError(f"Argos: source language '{source}' not installed.")
    translation = src_lang.get_translation(target)
    if translation is None:
        raise ValueError(f"Argos: no translation model for '{source}' → '{target}'.")
    return translation.translate(text)
