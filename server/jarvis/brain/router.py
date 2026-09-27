"""Deterministic model router: picks the fast / smart / deep tier for each request."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from jarvis.config import BrainConfig, ModelConfig, Tier


@dataclass(frozen=True)
class Route:
    tier: Tier
    model: ModelConfig
    reason: str


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    return re.sub(r"\s+", " ", text).strip()


class ModelRouter:
    def __init__(self, config: BrainConfig) -> None:
        self._models = config.models
        self._router = config.router
        self._deep = [_normalize(t) for t in self._router.deep_triggers]
        self._smart = [_normalize(t) for t in self._router.smart_triggers]

    def route(self, text: str) -> Route:
        norm = _normalize(text)
        for trigger in self._deep:
            if trigger in norm:
                return self._pick("deep", f"trigger '{trigger}'")
        for trigger in self._smart:
            if re.search(rf"\b{re.escape(trigger)}", norm):
                return self._pick("smart", f"trigger '{trigger}'")
        words = len(norm.split())
        if words >= self._router.smart_min_words:
            return self._pick("smart", f"{words} parole")
        return self._pick("fast", "richiesta breve")

    def _pick(self, tier: Tier, reason: str) -> Route:
        # Degrade gracefully if a tier is not configured.
        candidates: tuple[Tier, ...] = (tier, "smart", "fast", "deep")
        for candidate in candidates:
            if candidate in self._models:
                return Route(tier=candidate, model=self._models[candidate], reason=reason)
        raise ValueError("no model configured in brain.models")
