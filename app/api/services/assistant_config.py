"""
Assistant role configuration persistence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

CONFIG_PATH: Path = Path(__file__).resolve().parents[2] / "config.json"
DEFAULT_CONFIG: Dict[str, str] = {"name": "Assistant", "persona": ""}


def _ensure_file_exists() -> None:
    """Ensure the config file exists with default content."""
    if CONFIG_PATH.exists():
        return
    CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2), encoding="utf-8")


def load_assistant_config() -> Dict[str, str]:
    """
    Load assistant role configuration from disk.

    :return: Dict with keys name/persona.
    """
    _ensure_file_exists()
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        name = str(data.get("name") or DEFAULT_CONFIG["name"])
        persona = str(data.get("persona") or DEFAULT_CONFIG["persona"])
        return {"name": name, "persona": persona}
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_assistant_config(name: str | None = None, persona: str | None = None) -> Dict[str, str]:
    """
    Persist assistant role configuration.

    :param name: Optional new assistant name.
    :param persona: Optional new persona description.
    :return: Saved configuration.
    """
    cfg = load_assistant_config()
    if name is not None:
        cfg["name"] = name
    if persona is not None:
        cfg["persona"] = persona
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return cfg





