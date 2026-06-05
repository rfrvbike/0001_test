from __future__ import annotations

from .models import GenerationResult


def format_result(result: GenerationResult) -> str:
    invite = result.invite_suggestion or "今回は出さない"
    sections = [
        ("相手の印象", result.partner_analysis),
        ("あなたとの相性が良い話題", _bullets(result.compatibility_topics)),
        ("軽く触れるだけの話題", _bullets(result.light_only_topics)),
        ("避けた方がいい話題", _bullets(result.avoid_topics)),
        ("推奨戦略", result.recommended_strategy),
        ("メッセージ候補", _numbered(result.message_candidates)),
        ("一番おすすめ", result.best_message),
        ("おすすめ理由", "自然にプロフィールへ触れていて、質問が1つで返しやすいです。"),
        ("会話の次の流れ", "1. 相手の返信を待つ\n2. 共通話題を1つ広げる\n3. 温度感が上がったら軽い誘いを検討する"),
        ("誘い方", invite),
        ("相手の温度感", result.partner_temperature),
        ("色気・冗談の許可レベル", str(result.flirt_allowed_level)),
        ("使ってよい軽い表現", "話していて楽しいです / 雰囲気が合いそうです"),
        ("NG表現", _bullets(result.ng_examples)),
        ("安全チェック結果", _bullets(result.safety_notes)),
    ]
    return "\n\n".join(f"【{title}】\n{body}" for title, body in sections)


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- なし"


def _numbered(items: list[str]) -> str:
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, 1))
