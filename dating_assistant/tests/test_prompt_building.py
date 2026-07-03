from src.loaders import load_config
from src.claude_generator import _build_system_prompt, _parse_candidates
from src.models import ConversationTurn, PartnerAnalysis, PartnerProfile, PartnerRecord
import unittest


def _make_partner(conversation=None, temperature="normal"):
    return PartnerRecord(
        partner_id="partner_test",
        display_name="テスト相手",
        profile=PartnerProfile(profile_text="よろしくお願いします"),
        conversation=list(conversation or []),
        analysis=PartnerAnalysis(partner_temperature=temperature),
    )


class PromptBuildingTest(unittest.TestCase):
    def test_user_profile_is_loadable(self):
        profile = load_config("user_profile.yaml")

        self.assertIn("strong_topics", profile)
        self.assertIn("conversation_style", profile)

    def test_flirt_and_safety_policies_are_loadable(self):
        self.assertIn("default_flirt_level_by_stage", load_config("flirt_policy.yaml"))
        self.assertIn("safety_checks", load_config("safety_policy.yaml"))


class ReplyPromptDifferentiationTest(unittest.TestCase):
    def test_three_candidate_roles_are_present(self):
        prompt = _build_system_prompt(_make_partner(), tone="自然", objectives=[])

        # A: 3候補それぞれに異なる役割（話題×戦略）が割り当てられていること
        self.assertIn("候補1：共感・深掘り", prompt)
        self.assertIn("候補2：新規話題・ユーモア", prompt)
        self.assertIn("候補3：柔軟", prompt)
        # 3候補が重複しないという必須制約が明示されていること
        self.assertIn("話題も戦略も互いに重複させないこと", prompt)

    def test_opening_lines_must_differ(self):
        # 書き出し（冒頭の一文）も候補ごとに変える制約が明示されていること
        prompt = _build_system_prompt(_make_partner(), tone="自然", objectives=[])

        self.assertIn("書き出し（冒頭の一文）の表現も互いに変える", prompt)

    def test_history_beyond_ten_items_is_included(self):
        # B(a): 直近10件制限の撤廃。11件以上前の発言もプロンプトに含まれること
        conversation = [
            ConversationTurn(speaker="partner", text="古い発言マーカー0番目")
        ]
        for i in range(1, 15):
            conversation.append(ConversationTurn(speaker="user", text=f"自分の発言{i}"))
            conversation.append(ConversationTurn(speaker="partner", text=f"相手の発言{i}"))

        prompt = _build_system_prompt(_make_partner(conversation), tone="自然", objectives=[])

        self.assertIn("古い発言マーカー0番目", prompt)

    def test_previously_asked_questions_are_listed(self):
        # B(b): 自分の「？」付き発言が「既に聞いた質問」セクションに入ること
        conversation = [
            ConversationTurn(speaker="user", text="休日は何してますか？"),
            ConversationTurn(speaker="partner", text="映画を見たりします"),
            ConversationTurn(speaker="user", text="いいですね"),
        ]
        prompt = _build_system_prompt(_make_partner(conversation), tone="自然", objectives=[])

        self.assertIn("既に聞いた質問（3候補いずれも繰り返し禁止）", prompt)
        self.assertIn("休日は何してますか？", prompt)

    def test_no_question_section_when_no_questions_asked(self):
        conversation = [
            ConversationTurn(speaker="user", text="こんにちは"),
            ConversationTurn(speaker="partner", text="こんにちは"),
        ]
        prompt = _build_system_prompt(_make_partner(conversation), tone="自然", objectives=[])

        self.assertNotIn("既に聞いた質問（3候補いずれも繰り返し禁止）", prompt)

    def test_temperature_high_pushes_forward(self):
        # C: 温度感が良いときは候補2・3を踏み込む方向へ寄せる指示が入ること
        prompt = _build_system_prompt(_make_partner(temperature="very_good"), tone="自然", objectives=[])

        self.assertIn("相手の温度感", prompt)
        self.assertIn("とても良い", prompt)
        self.assertIn("一歩踏み込む", prompt)

    def test_temperature_low_stays_light(self):
        prompt = _build_system_prompt(_make_partner(temperature="low"), tone="自然", objectives=[])

        self.assertIn("軽め・返信しやすい", prompt)


class ParseCandidatesTest(unittest.TestCase):
    def test_three_candidates_are_split(self):
        text = "候補1:\nこんにちは\n\n候補2:\n最近どう？\n\n候補3:\n今度会おう"
        candidates = _parse_candidates(text)

        self.assertEqual(len(candidates), 3)
        self.assertEqual(candidates[0], "こんにちは")
        self.assertEqual(candidates[2], "今度会おう")

    def test_shortfall_returns_available_only(self):
        # D: 3件揃わない場合は取れた分だけ返す（件数で不足を検知できる）
        text = "候補1:\nこんにちは\n\n候補2:\n最近どう？"
        candidates = _parse_candidates(text)

        self.assertEqual(len(candidates), 2)

    def test_malformed_response_falls_back_to_single(self):
        candidates = _parse_candidates("形式が崩れた応答")

        self.assertEqual(len(candidates), 1)


if __name__ == "__main__":
    unittest.main()
