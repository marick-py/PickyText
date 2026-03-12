DEFAULTS: dict = {
    # Hotkey
    "hotkey": "ctrl+shift+d",  # win+* requires admin on some Windows configs

    # Screenshot
    "capture_monitor": "active",  # always the monitor where the cursor is

    # OCR
    "ocr_engine": "windows",        # "windows" | "tesseract"
    "ocr_source_language": "auto",  # BCP-47 or "auto"
    "tesseract_path": "",           # auto-detected if empty

    # Translation
    "translation_endpoint": "https://translate.emptyhead.dev",
    "translation_api_key": "68b2dbaf-17cd-4aac-bba4-4a33535304a1",
    "translation_source_language": "auto",
    "translation_target_language": "en",
    "translation_fallback": "argos",  # "argos" | "none"

    # UI
    "theme": "dark",          # "dark" | "light"
    "overlay_size_pct": 80,   # % of monitor

    # History
    "history_enabled": True,
    "history_max_length": 10,
    "history_save_images": True,

    # Updates
    "check_updates_on_startup": True,

    # Startup
    "start_with_windows": False,
}

# BCP-47 → Tesseract lang code mapping
TESSERACT_LANG_MAP: dict[str, str] = {
    "en":      "eng",
    "fr":      "fra",
    "de":      "deu",
    "es":      "spa",
    "it":      "ita",
    "pt":      "por",
    "ja":      "jpn",
    "zh-Hans": "chi_sim",
    "zh-Hant": "chi_tra",
    "ko":      "kor",
    "ar":      "ara",
    "ru":      "rus",
    "nl":      "nld",
    "pl":      "pol",
    "sv":      "swe",
    "tr":      "tur",
    "uk":      "ukr",
    "hi":      "hin",
    "vi":      "vie",
    "th":      "tha",
    "id":      "ind",
}
