from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .atomic_io import atomic_write_text
from .models import ConversationTurn


def save_history(path: str | Path, turns: list[ConversationTurn]) -> None:
    target = Path(path)
    atomic_write_text(target, json.dumps([asdict(turn) for turn in turns], ensure_ascii=False, indent=2))

