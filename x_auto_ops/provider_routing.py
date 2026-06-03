"""Provider resolution and routing for text-related automation tasks.

This module keeps GUI/env-like settings, resolved providers, and called
functions aligned. It never calls real external APIs by itself; provider
functions must be injected by the caller.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Mapping


SUPPORTED_ACCOUNTS = frozenset(
    {"yokaze_daily", "ai_side_business", "ai_pickup", "new_account_daily"}
)
SUPPORTED_PROVIDERS = frozenset({"openai", "gemini"})


class ProviderConfigError(ValueError):
    """Raised when provider settings are missing or invalid."""


class ProviderMismatchError(RuntimeError):
    """Raised when the resolved provider and called function disagree."""


ProviderFunction = Callable[[str, str, str], str]
ImageFunction = Callable[[str, str], str]
NeedCheckFunction = Callable[[str], bool]


@dataclass(frozen=True)
class RuntimeConfig:
    account_id: str
    text_provider: str
    text_model: str
    image_prompt_provider: str
    image_prompt_model: str
    quality_check_provider: str
    quality_check_model: str
    image_generation_enabled: bool
    image_need_check_enabled: bool


@dataclass
class ProviderClients:
    call_openai_text: ProviderFunction
    call_gemini_text: ProviderFunction
    generate_image: ImageFunction | None = None
    check_image_need: NeedCheckFunction | None = None


def _blocked_text_call(prompt: str, model: str, account_id: str) -> str:
    raise RuntimeError(
        "Real provider clients are not configured. Inject a mock or an approved "
        "client before calling provider functions."
    )


DEFAULT_BLOCKED_CLIENTS = ProviderClients(
    call_openai_text=_blocked_text_call,
    call_gemini_text=_blocked_text_call,
)


def resolve_runtime_config(
    settings: Mapping[str, Any],
    account_id: str,
) -> RuntimeConfig:
    """Resolve GUI/env-like settings into a single runtime config."""

    if account_id not in SUPPORTED_ACCOUNTS:
        raise ProviderConfigError(f"Unsupported account_id: {account_id}")

    text_provider = _provider(settings, "TEXT_LLM_PROVIDER")
    image_prompt_provider = _provider(
        settings,
        "IMAGE_PROMPT_LLM_PROVIDER",
        default=text_provider,
    )
    quality_check_provider = _provider(
        settings,
        "QUALITY_CHECK_LLM_PROVIDER",
        default=text_provider,
    )

    return RuntimeConfig(
        account_id=account_id,
        text_provider=text_provider,
        text_model=_model_for(settings, text_provider),
        image_prompt_provider=image_prompt_provider,
        image_prompt_model=_model_for(settings, image_prompt_provider),
        quality_check_provider=quality_check_provider,
        quality_check_model=_model_for(settings, quality_check_provider),
        image_generation_enabled=_bool_setting(
            settings,
            "IMAGE_GENERATION_ENABLED",
            default=True,
        ),
        image_need_check_enabled=_bool_setting(
            settings,
            "IMAGE_NEED_CHECK_ENABLED",
            default=True,
        ),
    )


def generate_post_text(
    config: RuntimeConfig,
    prompt: str,
    clients: ProviderClients,
    logger: logging.Logger | None = None,
) -> str:
    """Generate post body text using only TEXT_LLM_PROVIDER."""

    return _call_text_provider(
        provider=config.text_provider,
        model=config.text_model,
        account_id=config.account_id,
        prompt=prompt,
        clients=clients,
        called_function_prefix="call",
        public_function="generate_post_text",
        logger=logger,
    )


def generate_image_prompt(
    config: RuntimeConfig,
    prompt: str,
    clients: ProviderClients,
    logger: logging.Logger | None = None,
) -> str:
    """Generate an image prompt without reading TEXT_LLM_PROVIDER."""

    return _call_text_provider(
        provider=config.image_prompt_provider,
        model=config.image_prompt_model,
        account_id=config.account_id,
        prompt=prompt,
        clients=clients,
        called_function_prefix="call",
        public_function="generate_image_prompt",
        logger=logger,
    )


def run_quality_check(
    config: RuntimeConfig,
    prompt: str,
    clients: ProviderClients,
    logger: logging.Logger | None = None,
) -> str:
    """Run text quality checks without reading TEXT_LLM_PROVIDER."""

    return _call_text_provider(
        provider=config.quality_check_provider,
        model=config.quality_check_model,
        account_id=config.account_id,
        prompt=prompt,
        clients=clients,
        called_function_prefix="call",
        public_function="run_quality_check",
        logger=logger,
    )


def create_image_if_enabled(
    config: RuntimeConfig,
    image_prompt: str,
    clients: ProviderClients,
    logger: logging.Logger | None = None,
) -> str | None:
    """Create an image only when IMAGE_GENERATION_ENABLED is true."""

    if not config.image_generation_enabled:
        _log_provider_call(
            logger,
            provider="disabled",
            model="disabled",
            called_function="create_image_if_enabled",
            account_id=config.account_id,
            purpose="image_generation_skipped",
        )
        return None
    if clients.generate_image is None:
        raise RuntimeError("generate_image client is not configured")
    _log_provider_call(
        logger,
        provider="image",
        model="configured-image-client",
        called_function="generate_image",
        account_id=config.account_id,
        purpose="image_generation",
    )
    return clients.generate_image(image_prompt, config.account_id)


def check_image_need_if_enabled(
    config: RuntimeConfig,
    post_text: str,
    clients: ProviderClients,
    logger: logging.Logger | None = None,
) -> bool | None:
    """Run image need checks only when IMAGE_NEED_CHECK_ENABLED is true."""

    if not config.image_need_check_enabled:
        _log_provider_call(
            logger,
            provider="disabled",
            model="disabled",
            called_function="check_image_need_if_enabled",
            account_id=config.account_id,
            purpose="image_need_check_skipped",
        )
        return None
    if clients.check_image_need is None:
        raise RuntimeError("check_image_need client is not configured")
    _log_provider_call(
        logger,
        provider="quality",
        model=config.quality_check_model,
        called_function="check_image_need",
        account_id=config.account_id,
        purpose="image_need_check",
    )
    return clients.check_image_need(post_text)


def assert_provider_function_match(provider: str, called_function: str) -> None:
    """Fail fast when provider and low-level function disagree."""

    expected = _called_function_for(provider)
    if called_function != expected:
        raise ProviderMismatchError(
            f"provider={provider} must call {expected}, got {called_function}"
        )


def _call_text_provider(
    provider: str,
    model: str,
    account_id: str,
    prompt: str,
    clients: ProviderClients,
    called_function_prefix: str,
    public_function: str,
    logger: logging.Logger | None,
) -> str:
    called_function = f"{called_function_prefix}_{provider}_text"
    assert_provider_function_match(provider, called_function)
    _log_provider_call(
        logger,
        provider=provider,
        model=model,
        called_function=called_function,
        account_id=account_id,
        purpose=public_function,
    )
    if provider == "openai":
        return clients.call_openai_text(prompt, model, account_id)
    if provider == "gemini":
        return clients.call_gemini_text(prompt, model, account_id)
    raise ProviderConfigError(f"Unsupported provider: {provider}")


def _called_function_for(provider: str) -> str:
    normalized = provider.lower().strip()
    if normalized not in SUPPORTED_PROVIDERS:
        raise ProviderConfigError(f"Unsupported provider: {provider}")
    return f"call_{normalized}_text"


def _provider(
    settings: Mapping[str, Any],
    key: str,
    default: str | None = None,
) -> str:
    raw = settings.get(key, default)
    if raw is None:
        raise ProviderConfigError(f"Missing required provider setting: {key}")
    provider = str(raw).strip().lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise ProviderConfigError(f"{key} has unsupported provider: {raw}")
    return provider


def _model_for(settings: Mapping[str, Any], provider: str) -> str:
    if provider == "openai":
        key = "OPENAI_MODEL"
    elif provider == "gemini":
        key = "GEMINI_MODEL"
    else:
        raise ProviderConfigError(f"Unsupported provider: {provider}")
    value = str(settings.get(key, "")).strip()
    if not value:
        raise ProviderConfigError(f"Missing required model setting: {key}")
    return value


def _bool_setting(
    settings: Mapping[str, Any],
    key: str,
    default: bool,
) -> bool:
    raw = settings.get(key, default)
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, int):
        return bool(raw)
    value = str(raw).strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ProviderConfigError(f"{key} must be boolean-like, got: {raw}")


def _log_provider_call(
    logger: logging.Logger | None,
    *,
    provider: str,
    model: str,
    called_function: str,
    account_id: str,
    purpose: str,
) -> None:
    if logger is None:
        return
    logger.info(
        "provider_call",
        extra={
            "provider": provider,
            "model": model,
            "called_function": called_function,
            "account_id": account_id,
            "purpose": purpose,
        },
    )
