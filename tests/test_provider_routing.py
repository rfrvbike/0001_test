from __future__ import annotations

import logging
import unittest
from dataclasses import dataclass, field

from x_auto_ops.provider_routing import (
    SUPPORTED_ACCOUNTS,
    ProviderClients,
    ProviderMismatchError,
    assert_provider_function_match,
    check_image_need_if_enabled,
    create_image_if_enabled,
    generate_image_prompt,
    generate_post_text,
    resolve_runtime_config,
    run_quality_check,
)


BASE_SETTINGS = {
    "OPENAI_MODEL": "gpt-5.4",
    "GEMINI_MODEL": "gemini-test-model",
    "IMAGE_PROMPT_LLM_PROVIDER": "gemini",
    "QUALITY_CHECK_LLM_PROVIDER": "openai",
    "IMAGE_GENERATION_ENABLED": "true",
    "IMAGE_NEED_CHECK_ENABLED": "true",
}


@dataclass
class MockCalls:
    openai_text: list[tuple[str, str, str]] = field(default_factory=list)
    gemini_text: list[tuple[str, str, str]] = field(default_factory=list)
    images: list[tuple[str, str]] = field(default_factory=list)
    need_checks: list[str] = field(default_factory=list)

    def clients(self) -> ProviderClients:
        return ProviderClients(
            call_openai_text=self.call_openai_text,
            call_gemini_text=self.call_gemini_text,
            generate_image=self.generate_image,
            check_image_need=self.check_image_need,
        )

    def call_openai_text(self, prompt: str, model: str, account_id: str) -> str:
        self.openai_text.append((prompt, model, account_id))
        return f"openai:{account_id}:{model}:{prompt}"

    def call_gemini_text(self, prompt: str, model: str, account_id: str) -> str:
        self.gemini_text.append((prompt, model, account_id))
        return f"gemini:{account_id}:{model}:{prompt}"

    def generate_image(self, image_prompt: str, account_id: str) -> str:
        self.images.append((image_prompt, account_id))
        return f"image:{account_id}:{image_prompt}"

    def check_image_need(self, post_text: str) -> bool:
        self.need_checks.append(post_text)
        return True


class ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def settings(**overrides: str) -> dict[str, str]:
    merged = dict(BASE_SETTINGS)
    merged.update(overrides)
    return merged


class ProviderRoutingTests(unittest.TestCase):
    def test_text_provider_openai_uses_only_call_openai_text_twice_per_account(self) -> None:
        for account_id in sorted(SUPPORTED_ACCOUNTS):
            calls = MockCalls()
            config = resolve_runtime_config(
                settings(TEXT_LLM_PROVIDER="openai"),
                account_id,
            )
            for i in range(2):
                with self.subTest(account_id=account_id, iteration=i):
                    result = generate_post_text(
                        config,
                        f"post-{i}",
                        calls.clients(),
                    )
                    self.assertTrue(result.startswith(f"openai:{account_id}:gpt-5.4"))
            self.assertEqual(len(calls.openai_text), 2)
            self.assertEqual(calls.gemini_text, [])

    def test_text_provider_gemini_uses_only_call_gemini_text_twice_per_account(self) -> None:
        for account_id in sorted(SUPPORTED_ACCOUNTS):
            calls = MockCalls()
            config = resolve_runtime_config(
                settings(TEXT_LLM_PROVIDER="gemini"),
                account_id,
            )
            for i in range(2):
                with self.subTest(account_id=account_id, iteration=i):
                    result = generate_post_text(
                        config,
                        f"post-{i}",
                        calls.clients(),
                    )
                    self.assertTrue(
                        result.startswith(
                            f"gemini:{account_id}:gemini-test-model"
                        )
                    )
            self.assertEqual(calls.openai_text, [])
            self.assertEqual(len(calls.gemini_text), 2)

    def test_account_specific_routing_has_no_gemini_fixed_path(self) -> None:
        for account_id in [
            "yokaze_daily",
            "ai_side_business",
            "ai_pickup",
            "new_account_daily",
        ]:
            calls = MockCalls()
            config = resolve_runtime_config(
                settings(TEXT_LLM_PROVIDER="openai"),
                account_id,
            )
            generate_post_text(config, "account route", calls.clients())
            self.assertEqual(calls.openai_text[0][2], account_id)
            self.assertEqual(calls.gemini_text, [])

    def test_image_prompt_and_quality_providers_do_not_mix_with_text_provider(self) -> None:
        calls = MockCalls()
        config = resolve_runtime_config(
            settings(
                TEXT_LLM_PROVIDER="openai",
                IMAGE_PROMPT_LLM_PROVIDER="gemini",
                QUALITY_CHECK_LLM_PROVIDER="gemini",
            ),
            "ai_pickup",
        )

        generate_post_text(config, "body", calls.clients())
        generate_image_prompt(config, "image prompt", calls.clients())
        run_quality_check(config, "quality", calls.clients())

        self.assertEqual(len(calls.openai_text), 1)
        self.assertEqual(len(calls.gemini_text), 2)
        self.assertEqual(calls.openai_text[0][0], "body")
        self.assertEqual([call[0] for call in calls.gemini_text], ["image prompt", "quality"])

    def test_image_generation_disabled_skips_image_api_twice(self) -> None:
        calls = MockCalls()
        config = resolve_runtime_config(
            settings(
                TEXT_LLM_PROVIDER="openai",
                IMAGE_GENERATION_ENABLED="false",
            ),
            "ai_pickup",
        )
        for i in range(2):
            self.assertIsNone(
                create_image_if_enabled(config, f"image-{i}", calls.clients())
            )
        self.assertEqual(calls.images, [])

    def test_image_need_check_disabled_skips_need_check_twice(self) -> None:
        calls = MockCalls()
        config = resolve_runtime_config(
            settings(
                TEXT_LLM_PROVIDER="openai",
                IMAGE_NEED_CHECK_ENABLED="false",
            ),
            "yokaze_daily",
        )
        for i in range(2):
            self.assertIsNone(
                check_image_need_if_enabled(config, f"post-{i}", calls.clients())
            )
        self.assertEqual(calls.need_checks, [])

    def test_provider_function_mismatch_raises(self) -> None:
        with self.assertRaises(ProviderMismatchError):
            assert_provider_function_match("openai", "call_gemini_text")

    def test_provider_logs_include_provider_model_and_called_function(self) -> None:
        calls = MockCalls()
        logger = logging.getLogger("provider-routing-test")
        logger.setLevel(logging.INFO)
        handler = ListHandler()
        logger.addHandler(handler)
        try:
            config = resolve_runtime_config(
                settings(TEXT_LLM_PROVIDER="openai"),
                "new_account_daily",
            )
            generate_post_text(config, "log me", calls.clients(), logger=logger)
        finally:
            logger.removeHandler(handler)

        self.assertEqual(len(handler.records), 1)
        record = handler.records[0]
        self.assertEqual(record.provider, "openai")
        self.assertEqual(record.model, "gpt-5.4")
        self.assertEqual(record.called_function, "call_openai_text")
        self.assertEqual(record.account_id, "new_account_daily")


if __name__ == "__main__":
    unittest.main()
