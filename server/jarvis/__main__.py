"""Entry point: `uv run jarvis` or `python -m jarvis`."""

from __future__ import annotations

import argparse
import asyncio
import sys

from jarvis.app import build_jarvis
from jarvis.config import load_secrets, load_settings
from jarvis.interfaces.cli import Cli
from jarvis.logging_setup import setup_logging


def main() -> int:
    parser = argparse.ArgumentParser(prog="jarvis", description="J.A.R.V.I.S.")
    parser.add_argument(
        "--quiet-model", action="store_true", help="non mostrare quale modello risponde"
    )
    args = parser.parse_args()

    settings = load_settings()
    setup_logging(
        settings.logging.level,
        settings.resolve(settings.logging.file) if settings.logging.file else None,
    )
    secrets = load_secrets()
    if not secrets.anthropic_api_key:
        print(
            "Manca ANTHROPIC_API_KEY: copi .env.example in .env e inserisca la chiave.",
            file=sys.stderr,
        )
        return 1

    jarvis = build_jarvis(settings, api_key=secrets.anthropic_api_key)
    asyncio.run(Cli(jarvis, show_model=not args.quiet_model).run())
    return 0


if __name__ == "__main__":
    sys.exit(main())
