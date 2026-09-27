"""Build the system prompt: a stable persona block plus a per-turn context block."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from jarvis.config import UserConfig

_WEEKDAYS = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
_MONTHS = [
    "gennaio",
    "febbraio",
    "marzo",
    "aprile",
    "maggio",
    "giugno",
    "luglio",
    "agosto",
    "settembre",
    "ottobre",
    "novembre",
    "dicembre",
]


def format_datetime_it(now: datetime) -> str:
    return (
        f"{_WEEKDAYS[now.weekday()]} {now.day} {_MONTHS[now.month - 1]} {now.year}, ore {now:%H:%M}"
    )


class Persona:
    def __init__(self, template_path: Path, user: UserConfig) -> None:
        self._user = user
        template = template_path.read_text(encoding="utf-8")
        user_ref = f"{user.title} {user.name}".strip() if user.name else user.title
        self._persona = template.format(title=user.title, user_ref=user_ref)

    @property
    def text(self) -> str:
        return self._persona

    def context_block(self, now: datetime | None = None, extra: list[str] | None = None) -> str:
        now = now or datetime.now(ZoneInfo(self._user.timezone))
        lines = [
            "## Contesto attuale",
            f"- Data e ora: {format_datetime_it(now)} ({self._user.timezone})",
            f"- Posizione: {self._user.location}",
        ]
        lines.extend(f"- {item}" for item in extra or [])
        return "\n".join(lines)

    def system_blocks(
        self, now: datetime | None = None, extra: list[str] | None = None
    ) -> list[dict[str, Any]]:
        # The persona is stable and cached; the volatile context goes after the breakpoint.
        return [
            {"type": "text", "text": self._persona, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": self.context_block(now, extra)},
        ]
