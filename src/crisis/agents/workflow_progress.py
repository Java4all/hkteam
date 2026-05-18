"""Optional callbacks while a specialist workflow runs (for SSE / UI updates)."""

from __future__ import annotations

from collections.abc import Callable

SpecialistStepCallback = Callable[[str], None]
