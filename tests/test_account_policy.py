from __future__ import annotations

import unittest

from x_auto_ops.account_policy import (
    AI_SIDE_BUSINESS_POLICY,
    NEW_ACCOUNT_DAILY_POLICY,
    YOKAZE_DAILY_POLICY,
    get_account_prompt_policy,
)


class AccountPolicyTests(unittest.TestCase):
    def test_new_account_daily_policy_is_account_specific(self) -> None:
        self.assertIs(
            get_account_prompt_policy("new_account_daily"),
            NEW_ACCOUNT_DAILY_POLICY,
        )
        self.assertIs(
            get_account_prompt_policy("yokaze_daily"),
            YOKAZE_DAILY_POLICY,
        )
        self.assertIs(
            get_account_prompt_policy("ai_side_business"),
            AI_SIDE_BUSINESS_POLICY,
        )
        self.assertIs(
            get_account_prompt_policy("ai_pickup"),
            AI_SIDE_BUSINESS_POLICY,
        )

    def test_yokaze_daily_policy_locks_specific_wound_direction(self) -> None:
        prompt = YOKAZE_DAILY_POLICY.text_generation_prompt
        quality = YOKAZE_DAILY_POLICY.quality_check_prompt
        image_direction = YOKAZE_DAILY_POLICY.image_prompt_direction

        for required in [
            "Prioritize love themes about 70%",
            "Each post must target a concrete wound",
            "Show one specific scene",
            "Speak the hidden feeling",
            "Do not preach, explain, or sound like self-help",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, prompt)
        self.assertIn("avoid copying reference posts", quality)
        self.assertIn("No text, no typography, no labels", image_direction)

    def test_new_account_daily_text_prompt_locks_mature_daily_direction(self) -> None:
        prompt = NEW_ACCOUNT_DAILY_POLICY.text_generation_prompt

        for required in [
            "not a plain diary account",
            "stylish, mature everyday account",
            "Casual everyday moments: 10-20%",
            "Stylish mature everyday posts: 40-60%",
            "Stronger mature aftertaste: 20-30%",
            "2-4 natural sentences",
            "Slightly sensual but not explicit",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, prompt)

    def test_new_account_daily_quality_check_rejects_plain_life_logs(self) -> None:
        prompt = NEW_ACCOUNT_DAILY_POLICY.quality_check_prompt

        self.assertIn("more than a plain event report", prompt)
        self.assertIn("avoid ending as only a life log", prompt)
        self.assertIn("stylish, mature everyday atmosphere", prompt)
        self.assertIn("image decision protecting the text's aftertaste", prompt)

    def test_new_account_daily_image_policy_prefers_text_only_when_mood_is_complete(self) -> None:
        image_need = NEW_ACCOUNT_DAILY_POLICY.image_need_check_prompt
        image_direction = NEW_ACCOUNT_DAILY_POLICY.image_prompt_direction

        self.assertIn("Recommend text_only", image_need)
        self.assertIn("writing already completes the mood", image_need)
        self.assertIn("Recommend image", image_need)
        self.assertIn("Night rooms, rain, lighting, coffee", image_need)
        self.assertIn("No people, no faces, no text", image_direction)
        self.assertIn("no typography", image_direction)
        self.assertIn("no infographic", image_direction)

    def test_ai_side_business_policy_locks_work_improvement_direction(self) -> None:
        prompt = AI_SIDE_BUSINESS_POLICY.text_generation_prompt

        for required in [
            "not a suspicious side-hustle account",
            "non-engineer practitioner",
            "ChatGPT, Claude, Gemini, Codex",
            "Use Codex as the default tool",
            "Empathy / noticing: 30-40%",
            "Practice log: 25-30%",
            "AI tool topic: 15-20%",
            "Practical work know-how: 15-20%",
            "Direction / mild urgency: 5-10%",
            "Diagram-worthy: 5-10%",
            "Never end as plain AI news",
            "Small AI-use hint rule",
            "Keep it to one hint per post",
            "GPT projects for separating entry points",
            "Codex for small processing rules",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, prompt)

    def test_ai_side_business_quality_check_rejects_tool_news_and_cursor_practice(self) -> None:
        prompt = AI_SIDE_BUSINESS_POLICY.quality_check_prompt

        self.assertIn("non-engineers using AI to lighten work", prompt)
        self.assertIn("avoid easy-money claims", prompt)
        self.assertIn("plain news or tool comparison", prompt)
        self.assertIn("prefer Codex over Cursor", prompt)
        self.assertIn("natural on X", prompt)
        self.assertIn("avoid ending as only abstract reflection", prompt)
        self.assertIn("one small AI-use hint", prompt)
        self.assertIn("not so detailed that the", prompt)
        self.assertIn("avoid cramming multiple hints", prompt)

    def test_ai_side_business_image_policy_is_strict_about_save_value(self) -> None:
        image_need = AI_SIDE_BUSINESS_POLICY.image_need_check_prompt
        image_direction = AI_SIDE_BUSINESS_POLICY.image_prompt_direction

        self.assertIn("does an image increase save value", image_need)
        self.assertIn("Recommend text_only", image_need)
        self.assertIn("short AI tool topic", image_need)
        self.assertIn("A hint alone does not make an", image_need)
        self.assertIn("Recommend image", image_need)
        self.assertIn("before/after comparison", image_need)
        self.assertIn("Prefer text_only unless", image_need)
        self.assertIn("clean, practical diagram", image_direction)
        self.assertIn("non-engineers using AI at work", image_direction)


if __name__ == "__main__":
    unittest.main()
