"""Build safe X recent-search query strings without calling external APIs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


DEFAULT_MAX_QUERY_LENGTH = 512
DEFAULT_LANGUAGE = "ja"


class QueryBuildError(ValueError):
    """Raised when a recent-search query cannot be built safely."""


@dataclass(frozen=True)
class RecentSearchQuery:
    query: str
    source_genre: str
    search_terms: tuple[str, ...]
    target_accounts: tuple[str, ...]
    exclude_keywords: tuple[str, ...]
    language: str = DEFAULT_LANGUAGE

    def __str__(self) -> str:
        return self.query


def build_recent_search_query(
    config: Mapping[str, Any] | Any,
    *,
    max_length: int = DEFAULT_MAX_QUERY_LENGTH,
) -> RecentSearchQuery:
    """Build an X recent-search query from genre config.

    The builder only formats local config. It does not read credentials and does
    not perform network requests.
    """

    source_genre = _text(_get(config, "source_genre") or _get(config, "id") or _get(config, "genre"))
    search_terms = _dedupe(_as_list(_get(config, "search_queries") or _get(config, "keywords")))
    target_accounts = _dedupe(_clean_account(account) for account in _as_list(_get(config, "target_accounts")))
    exclude_keywords = _dedupe(_as_list(_get(config, "exclude_keywords")))
    language = _clean_language(_get(config, "lang") or _get(config, "language") or DEFAULT_LANGUAGE)

    if not search_terms and not target_accounts:
        raise QueryBuildError("recent search query requires search_queries, keywords, or target_accounts")

    parts: list[str] = []
    if search_terms:
        formatted_terms = [_format_term(term) for term in search_terms]
        parts.append(f"({' OR '.join(formatted_terms)})" if len(formatted_terms) > 1 else formatted_terms[0])

    if target_accounts:
        account_terms = [f"from:{account}" for account in target_accounts]
        parts.append(f"({' OR '.join(account_terms)})" if len(account_terms) > 1 else account_terms[0])

    parts.extend(f"-{_format_term(keyword)}" for keyword in exclude_keywords)

    if language:
        parts.append(f"lang:{language}")

    query = " ".join(parts).strip()
    if not query:
        raise QueryBuildError("recent search query is empty")
    if len(query) > max_length:
        raise QueryBuildError(f"recent search query is too long: {len(query)} > {max_length}")

    return RecentSearchQuery(
        query=query,
        source_genre=source_genre,
        search_terms=tuple(search_terms),
        target_accounts=tuple(target_accounts),
        exclude_keywords=tuple(exclude_keywords),
        language=language,
    )


def _get(config: Mapping[str, Any] | Any, key: str) -> Any:
    if isinstance(config, Mapping):
        return config.get(key)
    return getattr(config, key, None)


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    result: list[str] = []
    for item in value:
        text = _text(item)
        if text:
            result.append(text)
    return result


def _dedupe(values: Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = _text(value)
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result


def _clean_account(value: Any) -> str:
    account = _text(value).lstrip("@")
    allowed = [char for char in account if char.isascii() and (char.isalnum() or char == "_")]
    return "".join(allowed)


def _clean_language(value: Any) -> str:
    language = _text(value)
    allowed = [char for char in language if char.isascii() and (char.isalnum() or char == "-")]
    return "".join(allowed)


def _format_term(value: str) -> str:
    term = value.strip()
    if not term:
        return ""
    escaped = term.replace('"', '\\"')
    if any(char.isspace() for char in escaped):
        return f'"{escaped}"'
    return escaped


def _text(value: Any) -> str:
    return str(value or "").strip()
