from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path
from typing import Any, TypeVar

from .models import ConversationTurn, TargetProfile, UserProfile

T = TypeVar("T")

ROOT = Path(__file__).resolve().parents[1]

try:
    import yaml as _pyyaml
except ModuleNotFoundError:  # pragma: no cover - depends on optional local setup
    _pyyaml = None


def load_yaml(path: str | Path) -> dict[str, Any]:
    text = Path(path).read_text(encoding="utf-8")
    if _pyyaml is not None:
        data = _pyyaml.safe_load(text)
    else:
        data = parse_simple_yaml(text)
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def dump_yaml(data: dict[str, Any]) -> str:
    if _pyyaml is not None:
        return _pyyaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    return _dump_simple_yaml(data)


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
        if value == "[]":
            return []
        if value == "{}":
            return {}
        if len(value) >= 2 and value[0] == value[-1] == '"':
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value.strip("\"")
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
                elif (pair := _split_unquoted_mapping_value(item)) is not None:
                    key, value = pair
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


def _split_unquoted_mapping_value(text: str) -> tuple[str, str] | None:
    in_single = False
    in_double = False
    escaped = False
    for index, char in enumerate(text):
        if escaped:
            escaped = False
            continue
        if char == "\\" and in_double:
            escaped = True
            continue
        if char == "'" and not in_double:
            in_single = not in_single
            continue
        if char == '"' and not in_single:
            in_double = not in_double
            continue
        if char == ":" and not in_single and not in_double:
            return text[:index], text[index + 1 :]
    return None


def _dump_simple_yaml(data: dict[str, Any]) -> str:
    lines: list[str] = []
    for key, value in data.items():
        if isinstance(value, list):
            if value:
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {_format_scalar(item)}")
            else:
                lines.append(f"{key}: []")
        elif isinstance(value, str) and "\n" in value:
            lines.append(f"{key}: |")
            lines.extend(f"  {line}" for line in value.splitlines())
        else:
            lines.append(f"{key}: {_format_scalar(value)}")
    return "\n".join(lines) + "\n"


def _format_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


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
