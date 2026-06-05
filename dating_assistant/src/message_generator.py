from __future__ import annotations

from .models import GenerationRequest

BRIDGE_TOPICS = {"旅行", "自然", "遠出", "お酒", "飲み", "美容", "ファッション"}


def generate_messages(request: GenerationRequest, common: list[str], light: list[str], flirt_level: int) -> list[str]:
    target = request.target_profile
    topic = _choose_main_topic(common, light, target.hobbies)
    bridge = _choose_bridge_topic(target.hobbies)
    photo = target.photos_memo[0] if target.photos_memo else None

    candidates = [
        f"はじめまして。プロフィールを見て、{topic}の話ができそうで気になりました。最近よかったものってありますか？",
        f"はじめまして。{topic}が好きなんですね。自分も話しやすい話題なので、まずはゆるく話せたら嬉しいです。",
        "はじめまして。休日の過ごし方が少し近そうで、話してみたいなと思いました。最近はどんな過ごし方が多いですか？",
    ]
    if photo:
        candidates.insert(0, _photo_message(photo, topic, bridge))
    if bridge and bridge != topic:
        candidates.append(f"はじめまして。{bridge}の話も気になりました。詳しすぎるわけではないのですが、{topic}の話からゆるく聞けたら嬉しいです。")
    if flirt_level >= 1:
        candidates.append(f"{topic}の話、なんだか自然に話せそうで少し楽しみです。")
    return [_trim(candidate, 160) for candidate in candidates]


def generate_reply(
    request: GenerationRequest,
    common: list[str],
    flirt_level: int,
    reply_policy: dict | None = None,
    partner_temperature: str = "normal",
) -> list[str]:
    latest_partner = next((turn.text for turn in reversed(request.conversation_history) if turn.speaker == "partner"), "")
    policy = reply_policy or {}
    short_max = policy.get("fallback", {}).get("short_reply", {}).get("max_length", 12)
    if len(latest_partner.strip()) <= int(short_max):
        candidates = _short_reply_candidates(common, policy)
        topic = common[0] if common else "その話"
    else:
        topic_key, topic = select_reply_topic(request, common, policy)
        candidates = _reply_candidates(topic_key, topic, policy, partner_temperature)
    style = policy.get("temperature_style", {}).get(partner_temperature, {})
    if flirt_level >= 1 and style.get("allow_light_flirt", False):
        candidates.append(f"{topic}の話、自然に続けられそうでちょっと嬉しいです。")
    return [_trim(candidate, 160) for candidate in candidates]


def _reply_candidates(topic_key: str, topic: str, policy: dict, partner_temperature: str) -> list[str]:
    definition = policy.get("topic_keywords", {}).get(topic_key, {})
    acknowledgments = definition.get("acknowledgment_examples", [])
    empathies = definition.get("empathy_examples", [])
    questions = definition.get("safe_question_examples", [])
    if acknowledgments and questions:
        return [
            _compose_reply(
                _pick(acknowledgments, index, f"{topic}の話いいですね。"),
                _pick(empathies, index, "無理なく話せる話題で嬉しいです。"),
                _pick(questions, index, "最近よかったものはありますか？"),
                policy,
                partner_temperature,
                index,
            )
            for index in range(3)
        ]
    acknowledgement = f"{topic}の話いいですね。" if topic != "その話" else "それ、いいですね。"
    return [
        f"{acknowledgement}自分も少し気になりました。最近特によかったものはありますか？",
        f"{acknowledgement}無理なく話せる話題で嬉しいです。普段はどんな感じで楽しむことが多いですか？",
        f"{acknowledgement}自分もゆっくり聞いてみたいです。おすすめがあれば教えてください。",
    ]


def select_reply_topic(request: GenerationRequest, common: list[str], policy: dict) -> tuple[str, str]:
    definitions = policy.get("topic_keywords", {})
    priority = policy.get("priority_order", list(definitions))
    latest_partner = next((turn.text for turn in reversed(request.conversation_history) if turn.speaker == "partner"), "")
    history_texts = [turn.text for turn in request.conversation_history[:-1]]
    scored: list[tuple[int, int, str, str]] = []
    for topic_key, definition in definitions.items():
        keywords = definition.get("keywords", [])
        display_name = definition.get("display_name", topic_key)
        if display_name in request.user_profile.avoid_topics:
            continue
        score = 0
        if any(keyword in latest_partner for keyword in keywords):
            score += 3
        score += sum(1 for text in history_texts if any(keyword in text for keyword in keywords))
        if display_name in request.user_profile.strong_topics or display_name in request.user_profile.normal_topics:
            score += 1
        if display_name in request.user_profile.light_only_topics:
            score -= 1
        if score > 0:
            scored.append((score, -priority.index(topic_key) if topic_key in priority else -len(priority), topic_key, display_name))
    if scored:
        scored.sort(reverse=True)
        _, _, topic_key, display_name = scored[0]
        return topic_key, display_name
    partner_text = latest_partner
    for topic in common:
        if topic in partner_text:
            return "fallback", topic
    return "fallback", common[0] if common else "その話"


def _short_reply_candidates(common: list[str], policy: dict) -> list[str]:
    fallback_questions = policy.get("fallback", {}).get("short_reply", {}).get("safe_question_examples", [])
    safe_topic = next((topic for topic in ["カフェ", "ご飯", "映画", "休日"] if topic in common), None)
    if safe_topic:
        return [
            f"いいですね。{safe_topic}の話も気になっていました。{_safe_question(fallback_questions, '最近はどんな感じで楽しむことが多いですか？')}",
            f"そうなんですね。{safe_topic}は自分も話しやすいです。{_safe_question(fallback_questions, '休日に楽しむことが多いですか？', 1)}",
            f"ありがとうございます。{safe_topic}について、最近よかったものがあれば聞いてみたいです。",
        ]
    return [
        "いいですね。ゆっくり話せる感じが好きです。休日は外に出る日と家で過ごす日、どちらが多いですか？",
        "そうなんですね。無理なく話せる雰囲気で嬉しいです。最近よかったことはありますか？",
        "ありがとうございます。少しずつ話せたら嬉しいです。休日はどんなふうに過ごすことが多いですか？",
    ]


def _safe_question(questions: list[str], fallback: str, index: int = 0) -> str:
    if not questions:
        return fallback
    return questions[index % len(questions)]


def _pick(items: list[str], index: int, fallback: str) -> str:
    return items[index % len(items)] if items else fallback


def _compose_reply(
    acknowledgment: str,
    empathy: str,
    question: str,
    policy: dict,
    partner_temperature: str,
    index: int,
) -> str:
    style = policy.get("temperature_style", {}).get(partner_temperature, {})
    max_sentences = int(style.get("max_sentences", 3))
    parts = [acknowledgment]
    if max_sentences >= 3:
        if style.get("allow_warmth") and index == 1 and style.get("warm_phrases"):
            parts.append(_pick(style["warm_phrases"], index, empathy))
        else:
            parts.append(empathy)
    parts.append(question)
    return "".join(parts[:max_sentences])


def _choose_main_topic(common: list[str], light: list[str], hobbies: list[str]) -> str:
    preferred = ["カフェ", "ご飯", "映画", "休日", "買い物", "食べ物"]
    for topic in preferred:
        if topic in common or topic in hobbies:
            return topic
    for topic in common:
        if topic not in BRIDGE_TOPICS:
            return topic
    for topic in light:
        if topic not in BRIDGE_TOPICS:
            return topic
    return common[0] if common else (light[0] if light else (hobbies[0] if hobbies else "プロフィール"))


def _choose_bridge_topic(hobbies: list[str]) -> str | None:
    return next((topic for topic in hobbies if topic in BRIDGE_TOPICS), None)


def _photo_message(photo: str, topic: str, bridge: str | None) -> str:
    photo_subject = _clean_photo_memo(photo)
    if bridge in {"美容", "ファッション"}:
        return f"はじめまして。プロフィールを見て、雰囲気が素敵だなと思いました。{topic}の話も好きですか？"
    if bridge in {"旅行", "自然", "遠出"}:
        return f"はじめまして。{photo_subject}が印象に残りました。旅行は詳しすぎないのですが、休日はカフェやご飯も好きですか？"
    if bridge in {"お酒", "飲み"}:
        return f"はじめまして。{photo_subject}が楽しそうで気になりました。ご飯やお店の話、よかったらゆるく話したいです。"
    return f"はじめまして。プロフィールを見て、{photo_subject}が素敵だなと思いました。{topic}も好きなんですか？"


def _clean_photo_memo(photo: str) -> str:
    for suffix in ["がある", "写真がある"]:
        if photo.endswith(suffix):
            return photo[: -len(suffix)] or photo
    return photo


def _trim(text: str, max_len: int) -> str:
    return text if len(text) <= max_len else text[: max_len - 1] + "…"
