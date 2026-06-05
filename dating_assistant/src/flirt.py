from __future__ import annotations


def allowed_flirt_level(policy: dict, stage: str, desired: int | None) -> int:
    defaults = policy.get("default_flirt_level_by_stage", {})
    allowed = int(defaults.get(stage, defaults.get("first_message", 0)))
    if desired is not None:
        allowed = min(allowed, int(desired))
    return max(0, min(allowed, 4))

