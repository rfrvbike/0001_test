from __future__ import annotations

from .models import ConversationTurn


class SafetyReviewer:
    def __init__(self, policy: dict):
        self.policy = policy
        self.banned_terms = self._collect_banned_terms(policy)

    def review(self, message: str, history: list[ConversationTurn] | None = None) -> dict[str, object]:
        notes: list[str] = []
        ng_examples: list[str] = []
        status = "OK"
        matched = [term for term in self.banned_terms if term and term in message]
        if matched:
            status = "NG"
            notes.append(f"禁止表現に近い語句があります: {', '.join(matched[:5])}")
            ng_examples.extend(matched[:5])
        if message.count("？") + message.count("?") >= 3:
            status = "修正推奨" if status == "OK" else status
            notes.append("質問が多すぎます。1つの文面につき質問は1つまでにしてください。")
        if len(message) > 180:
            status = "修正推奨" if status == "OK" else status
            notes.append("文面が長めです。短く自然に整えると安全です。")
        if history is not None and not history and any(term in message for term in ["会いませんか", "行きませんか", "飲みに行き"]):
            status = "修正推奨" if status == "OK" else status
            notes.append("初回から誘う文面は避ける設定です。")
        return {
            "status": status,
            "notes": notes or ["安全チェックOK。送信前に人間が最終確認してください。"],
            "ng_examples": ng_examples,
        }

    def _collect_banned_terms(self, data: object) -> list[str]:
        terms: list[str] = []
        if isinstance(data, dict):
            for key, value in data.items():
                if key == "banned" and isinstance(value, list):
                    terms.extend(str(item) for item in value)
                else:
                    terms.extend(self._collect_banned_terms(value))
        elif isinstance(data, list):
            for item in data:
                terms.extend(self._collect_banned_terms(item))
        return terms

