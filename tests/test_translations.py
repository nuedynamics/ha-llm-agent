"""Every translation has exactly the English keys and the same placeholders."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

import pytest

ROOT = Path(__file__).parent.parent / "custom_components" / "llm_agent"
PANEL = ROOT / "www" / "i18n"
PANEL_LANGS = re.findall(
    r'"([a-zA-Z-]+)"',
    re.search(
        r"LANGUAGES = \[([^\]]*)\]",
        (Path(__file__).parent.parent / "frontend" / "src" / "i18n.ts").read_text(),
    ).group(1),
)
PLACEHOLDER = re.compile(r"\{(\w+)\}")


def _flat(data: Any, prefix: str = "") -> dict[str, str]:
    if isinstance(data, dict):
        out: dict[str, str] = {}
        for key, value in data.items():
            out.update(_flat(value, f"{prefix}{key}."))
        return out
    return {prefix.rstrip("."): data}


def _check(english: dict[str, str], other: dict[str, str], name: str) -> None:
    assert set(other) == set(english), (
        f"{name}: missing {sorted(set(english) - set(other))[:5]}, "
        f"extra {sorted(set(other) - set(english))[:5]}"
    )
    for key, text in english.items():
        assert isinstance(other[key], str) and other[key].strip(), f"{name}: {key} is empty"
        assert sorted(PLACEHOLDER.findall(other[key])) == sorted(PLACEHOLDER.findall(text)), (
            f"{name}: {key} placeholders differ"
        )


def test_panel_languages_listed_match_files() -> None:
    files = {p.stem for p in PANEL.glob("*.json")} - {"en"}
    assert files == set(PANEL_LANGS)


@pytest.mark.parametrize("lang", PANEL_LANGS)
def test_panel_translation_matches_english(lang: str) -> None:
    english = json.loads((PANEL / "en.json").read_text())
    _check(english, json.loads((PANEL / f"{lang}.json").read_text()), f"panel {lang}")


@pytest.mark.parametrize("lang", PANEL_LANGS)
def test_settings_translation_matches_english(lang: str) -> None:
    english = _flat(json.loads((ROOT / "strings.json").read_text()))
    other = _flat(json.loads((ROOT / "translations" / f"{lang}.json").read_text()))
    _check(english, other, f"settings {lang}")


def test_english_settings_file_matches_strings() -> None:
    assert json.loads((ROOT / "translations" / "en.json").read_text()) == json.loads(
        (ROOT / "strings.json").read_text()
    )
