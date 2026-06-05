from __future__ import annotations

from .models import TargetProfile


def analyze_profile(target: TargetProfile) -> str:
    clues: list[str] = []
    if target.hobbies:
        clues.append(f"プロフィール上は{', '.join(target.hobbies[:3])}に触れやすい印象です。")
    if target.photos_memo:
        clues.append(f"写真メモからは{_clean_photo_memo(target.photos_memo[0])}が読み取れます。")
    if target.relationship_goal:
        clues.append(f"関係性の希望は「{target.relationship_goal}」です。")
    if target.free_notes:
        clues.append("補足メモには、距離感と安全性に関する注意があります。")
    return " ".join(clues) or "プロフィール情報が少ないため、最初は軽く丁寧に入るのが安全です。"


def _clean_photo_memo(photo: str) -> str:
    for suffix in ["がある", "写真がある"]:
        if photo.endswith(suffix):
            return photo[: -len(suffix)] or photo
    return photo
