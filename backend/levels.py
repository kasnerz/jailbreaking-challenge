import os
from pathlib import Path
from typing import Any, Dict, List

import yaml

_BASE = Path(__file__).parent.parent / "config"
_levels_data: List[Dict] = []
_secrets: Dict[str, str] = {}


def _load():
    global _levels_data, _secrets

    levels_path = _BASE / "levels.yaml"
    secrets_path = _BASE / "secrets.yaml"

    with open(levels_path) as f:
        _levels_data = yaml.safe_load(f)["levels"]

    if secrets_path.exists():
        with open(secrets_path) as f:
            _secrets = yaml.safe_load(f)["secrets"]
    else:
        # Fallback for development when secrets.yaml doesn't exist
        _secrets = {level["id"]: "placeholder" for level in _levels_data}


def get_levels_public() -> List[Dict[str, Any]]:
    """Return public level metadata — no secret words."""
    return [
        {
            "id": lvl["id"],
            "name": lvl["name"],
            "description": lvl["description"],
            "emoji": lvl.get("emoji", ""),
        }
        for lvl in _levels_data
    ]


def build_system_prompt(level_id: str) -> str:
    """Build system prompt with secret word injected."""
    level = next((l for l in _levels_data if l["id"] == level_id), None)
    if not level:
        raise ValueError(f"Unknown level: {level_id}")

    secret = _secrets.get(level_id, "placeholder")
    return level["system_prompt"].format(secret_word=secret)


def get_secret(level_id: str) -> str:
    """Get the secret word for success detection (server-side only)."""
    return _secrets.get(level_id, "placeholder")


def get_valid_level_ids() -> List[str]:
    return [lvl["id"] for lvl in _levels_data]


# Load on import
_load()
