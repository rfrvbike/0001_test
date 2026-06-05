from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import ConversationTurn


def save_history(path: str | Path, turns: list[ConversationTurn]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps([asdict(turn) for turn in turns], ensure_ascii=False, indent=2), encoding="utf-8")

