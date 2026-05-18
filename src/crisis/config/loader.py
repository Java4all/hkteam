from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

from crisis.settings import settings

_ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):

        def repl(m: re.Match[str]) -> str:
            key = m.group(1)
            if key in os.environ:
                return os.environ[key]
            _map = {
                "NIM_CLOUD_BASE_URL": "nim_cloud_base_url",
                "NIM_LOCAL_BASE_URL": "nim_local_base_url",
                "NVIDIA_API_KEY": "nvidia_api_key",
            }
            attr = _map.get(key)
            if attr:
                return str(getattr(settings, attr, "") or "")
            return ""

        return _ENV_PATTERN.sub(repl, value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return _expand_env(yaml.safe_load(f) or {})


def load_llm_profile(profile: str | None = None) -> dict[str, Any]:
    name = profile or settings.llm_profile
    path = settings.configs_dir / "llm" / f"{name}.yaml"
    return _load_yaml(path)


def load_routing_config() -> dict[str, Any]:
    base = settings.configs_dir / "smart_routing"
    return {
        "category_map": _load_yaml(base / "category_map.yaml"),
        "dependencies": _load_yaml(base / "dependencies.yaml"),
    }
