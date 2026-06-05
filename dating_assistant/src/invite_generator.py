from __future__ import annotations

from .models import GenerationRequest


def maybe_generate_invite(request: GenerationRequest, temperature: str) -> str | None:
    if request.current_stage in {"first_message", "early_chat"}:
        return None
    if temperature not in {"good", "very_good"}:
        return None
    places = request.user_profile.date_preferences.get("good_first_date_places", ["カフェ"])
    place = places[0] if places else "カフェ"
    return f"話していてもう少しゆっくり話してみたいなと思いました。よかったら今度、軽く{place}でも行きませんか？もちろん無理なければで大丈夫です。"

