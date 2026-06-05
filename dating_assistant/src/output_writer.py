from __future__ import annotations

from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def save_cli_output(
    command: str,
    markdown: str,
    target_path: str | None = None,
    now: datetime | None = None,
) -> Path:
    output_dir = ROOT / "outputs" / "local"
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / build_output_filename(command, target_path, now)
    path = _next_available_path(path)
    path.write_text(markdown, encoding="utf-8")
    return path


def build_output_filename(command: str, target_path: str | None = None, now: datetime | None = None) -> str:
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    command_part = command.replace("-", "_")
    target_part = ""
    if target_path:
        stem = Path(target_path).stem
        target_part = f"_{stem}"
    return f"{command_part}{target_part}_{timestamp}.md"


def _next_available_path(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1
