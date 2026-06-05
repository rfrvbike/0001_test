from __future__ import annotations

import json
import os
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .loaders import load_yaml
from .models import (
    ActivityEvent,
    ConversationTurn,
    MessageState,
    PartnerAnalysis,
    PartnerNote,
    PartnerProfile,
    PartnerRecord,
    PendingSuggestion,
)

ROOT = Path(__file__).resolve().parents[1]
PARTNER_FILE_RE = re.compile(r"^partner_(\d+)\.yaml$")


def get_partner_dir() -> Path:
    override = os.environ.get("DATING_ASSISTANT_PARTNER_DIR")
    path = Path(override) if override else ROOT / "data" / "local" / "partners"
    path.mkdir(parents=True, exist_ok=True)
    return path


def generate_next_partner_id() -> str:
    numbers = [
        int(match.group(1))
        for path in get_partner_dir().glob("partner_*.yaml")
        if (match := PARTNER_FILE_RE.match(path.name))
    ]
    return f"partner_{max(numbers, default=0) + 1:03d}"


def partner_exists(partner_id: str) -> bool:
    return _partner_path(partner_id).exists()


def save_partner(partner: PartnerRecord, allow_overwrite: bool = False) -> Path:
    path = _partner_path(partner.partner_id)
    if path.exists() and not allow_overwrite:
        raise FileExistsError(f"Partner already exists: {partner.partner_id}")
    data = asdict(partner)
    for turn in data["conversation"]:
        turn["created_at"] = turn.pop("timestamp")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_partner(partner_id: str) -> PartnerRecord:
    path = _partner_path(partner_id)
    if not path.exists():
        raise FileNotFoundError(f"Partner not found: {partner_id}")
    return partner_from_mapping(_load_mapping(path))


def list_partners() -> list[PartnerRecord]:
    return [partner_from_mapping(_load_mapping(path)) for path in sorted(get_partner_dir().glob("partner_*.yaml"))]


def partner_from_mapping(data: dict[str, Any]) -> PartnerRecord:
    profile = PartnerProfile(**_known_fields(PartnerProfile, data.get("profile", {})))
    analysis = PartnerAnalysis(**_known_fields(PartnerAnalysis, data.get("analysis", {})))
    message_state = MessageState(**_known_fields(MessageState, data.get("message_state", {})))
    raw_suggestions = data.get("pending_suggestions", [])
    suggestions = [
        PendingSuggestion(**_known_fields(PendingSuggestion, suggestion))
        for suggestion in raw_suggestions
        if isinstance(suggestion, dict)
    ]
    notes = [
        PartnerNote(text=note) if isinstance(note, str) else PartnerNote(**_known_fields(PartnerNote, note))
        for note in data.get("notes", [])
        if isinstance(note, (str, dict))
    ]
    activity_log = [
        ActivityEvent(**_known_fields(ActivityEvent, event))
        for event in data.get("activity_log", [])
        if isinstance(event, dict)
    ]
    turns = []
    for turn in data.get("conversation", []):
        turn_data = dict(turn)
        turn_data["timestamp"] = turn_data.pop("created_at", turn_data.get("timestamp"))
        turns.append(ConversationTurn(**_known_fields(ConversationTurn, turn_data)))
    return PartnerRecord(
        partner_id=str(data["partner_id"]),
        display_name=str(data.get("display_name", "")),
        app_name=str(data.get("app_name", "")),
        status=str(data.get("status", "new_profile")),
        created_at=str(data.get("created_at", "")),
        updated_at=str(data.get("updated_at", "")),
        profile=profile,
        conversation=turns,
        analysis=analysis,
        pending_suggestions=suggestions,
        message_state=message_state,
        notes=notes,
        activity_log=activity_log,
    )


def load_partner_file(path: str | Path) -> PartnerRecord:
    return partner_from_mapping(_load_mapping(Path(path)))


def _load_mapping(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = load_yaml(path)
    if not isinstance(data, dict):
        raise ValueError(f"Partner YAML root must be a mapping: {path}")
    return data


def _known_fields(cls, data: dict[str, Any]) -> dict[str, Any]:
    names = cls.__dataclass_fields__.keys()
    return {key: value for key, value in data.items() if key in names}


def _partner_path(partner_id: str) -> Path:
    if not re.fullmatch(r"partner_\d+", partner_id):
        raise ValueError(f"Invalid partner id: {partner_id}")
    return get_partner_dir() / f"{partner_id}.yaml"
