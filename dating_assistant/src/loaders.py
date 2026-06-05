from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from typing import Any, TypeVar

from .models import ConversationTurn, TargetProfile, UserProfile

T = TypeVar("T")

ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: str | Path) -> dict[str, Any]:
    data = parse_simple_yaml(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def parse_simple_yaml(text: str) -> Any:
    """Parse the small YAML subset used by this project without external deps."""
    raw_lines = text.splitlines()
    lines = [
        (len(line) - len(line.lstrip(" ")), line.strip())
        for line in raw_lines
        if line.strip() and not line.lstrip().startswith("#")
    ]

    def scalar(value: str) -> Any:
        if value in {"true", "false"}:
            return value == "true"
        if value in {"null", "None"}:
            return None
        try:
            return int(value)
        except ValueError:
            return value.strip("\"'")

    def parse_block(index: int, indent: int) -> tuple[Any, int]:
        if index >= len(lines):
            return {}, index
        if lines[index][1].startswith("- "):
            result: list[Any] = []
            while index < len(lines) and lines[index][0] == indent and lines[index][1].startswith("- "):
                item = lines[index][1][2:]
                index += 1
                if not item:
                    child, index = parse_block(index, indent + 2)
                    result.append(child)
                elif ":" in item:
                    key, value = item.split(":", 1)
                    entry = {key.strip(): scalar(value.strip()) if value.strip() else {}}
                    if index < len(lines) and lines[index][0] > indent:
                        child, index = parse_block(index, lines[index][0])
                        if isinstance(child, dict):
                            entry.update(child)
                    result.append(entry)
                else:
                    result.append(scalar(item))
            return result, index

        result: dict[str, Any] = {}
        while index < len(lines) and lines[index][0] == indent:
            content = lines[index][1]
            if ":" not in content:
                index += 1
                continue
            key, value = content.split(":", 1)
            key = key.strip()
            value = value.strip()
            index += 1
            if value == "|":
                block_lines: list[str] = []
                while index < len(raw_lines):
                    original = raw_lines[index]
                    if original.strip() and len(original) - len(original.lstrip(" ")) <= indent:
                        break
                    block_lines.append(original[indent + 2 :] if len(original) >= indent + 2 else "")
                    index += 1
                result[key] = "\n".join(block_lines).strip()
            elif value:
                result[key] = scalar(value)
            else:
                child, index = parse_block(index, lines[index][0] if index < len(lines) else indent + 2)
                result[key] = child
        return result, index

    parsed, _ = parse_block(0, lines[0][0] if lines else 0)
    return parsed


def load_config(name: str) -> dict[str, Any]:
    return load_yaml(ROOT / "config" / name)


def _from_mapping(cls: type[T], data: dict[str, Any]) -> T:
    allowed = {field.name for field in fields(cls)}
    return cls(**{key: value for key, value in data.items() if key in allowed})


def load_target_profile(path: str | Path) -> TargetProfile:
    return _from_mapping(TargetProfile, load_yaml(path))


def load_user_profile(path: str | Path | None = None) -> UserProfile:
    data = load_yaml(path or ROOT / "config" / "user_profile.yaml")
    basic = data.get("basic_profile", {})
    return UserProfile(
        strong_topics=data.get("strong_topics", []),
        normal_topics=data.get("normal_topics", []),
        light_only_topics=data.get("light_only_topics", []),
        avoid_topics=data.get("avoid_topics", []),
        desired_impression=basic.get("desired_impression", []),
        avoid_impression=basic.get("avoid_impression", []),
        date_preferences=data.get("date_preferences", {}),
        conversation_style=data.get("conversation_style", {}),
    )


def load_conversation(path: str | Path | None) -> list[ConversationTurn]:
    if not path:
        return []
    data = load_yaml(path)
    turns = data.get("turns", data.get("conversation", []))
    return [_from_mapping(ConversationTurn, turn) for turn in turns]
