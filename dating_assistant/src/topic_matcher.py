from __future__ import annotations

from .models import TargetProfile, UserProfile


def _contains(text: str, topic: str) -> bool:
    return topic.casefold() in text.casefold()


def match_topics(target: TargetProfile, user: UserProfile, topic_scores: dict[str, int]) -> dict[str, list[str]]:
    target_text = "\n".join(
        [
            target.profile_text,
            " ".join(target.hobbies),
            " ".join(target.photos_memo),
            target.free_notes or "",
        ]
    )
    mentioned = [topic for topic in topic_scores if _contains(target_text, topic)]
    for hobby in target.hobbies:
        if hobby not in mentioned:
            mentioned.append(hobby)

    common: list[str] = []
    light: list[str] = []
    avoid: list[str] = []
    deep_caution: list[str] = []

    for topic in mentioned:
        score = topic_scores.get(topic, 0)
        if topic in user.avoid_topics or score <= 1:
            avoid.append(topic)
        elif topic in user.light_only_topics or score in (2, 3):
            light.append(topic)
        elif topic in user.strong_topics or topic in user.normal_topics or score >= 4:
            common.append(topic)
        else:
            deep_caution.append(topic)

    return {
        "common": _dedupe(common),
        "light": _dedupe(light),
        "avoid": _dedupe(avoid),
        "deep_caution": _dedupe(deep_caution),
    }


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result

