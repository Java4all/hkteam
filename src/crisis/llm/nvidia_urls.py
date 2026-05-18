from __future__ import annotations

from urllib.parse import urlparse

HOSTED_CLOUD_BASE = "https://integrate.api.nvidia.com/v1"
_HOSTED_HOSTS = frozenset({"integrate.api.nvidia.com", "ai.api.nvidia.com"})


def is_hosted_nim_url(base_url: str) -> bool:
    try:
        return urlparse(base_url).netloc in _HOSTED_HOSTS
    except Exception:
        return False
