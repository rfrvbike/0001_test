from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TargetProfile:
    name_or_label: str | None = None
    age: int | None = None
    profile_text: str = ""
    hobbies: list[str] = field(default_factory=list)
    photos_memo: list[str] = field(default_factory=list)
    location_hint: str | None = None
    relationship_goal: str | None = None
    free_notes: str | None = None


@dataclass
class UserProfile:
    strong_topics: list[str] = field(default_factory=list)
    normal_topics: list[str] = field(default_factory=list)
    light_only_topics: list[str] = field(default_factory=list)
    avoid_topics: list[str] = field(default_factory=list)
    desired_impression: list[str] = field(default_factory=list)
    avoid_impression: list[str] = field(default_factory=list)
    date_preferences: dict[str, Any] = field(default_factory=dict)
    conversation_style: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationTurn:
    speaker: str
    text: str
    timestamp: str | None = None


@dataclass
class PartnerProfile:
    age: int | None = None
    profile_text: str = ""
    hobbies: list[str] = field(default_factory=list)
    photos_memo: list[str] = field(default_factory=list)
    location_hint: str | None = None
    relationship_goal: str | None = None
    free_notes: str | None = None


@dataclass
class PartnerAnalysis:
    partner_temperature: str = "unknown"
    safe_topics: list[str] = field(default_factory=list)
    light_only_topics: list[str] = field(default_factory=list)
    avoid_topics: list[str] = field(default_factory=list)
    next_strategy: str = ""
    last_suggested_message: str = ""


@dataclass
class PendingSuggestion:
    suggestion_id: str
    purpose: str
    text: str
    created_at: str
    status: str = "pending"
    safety_result: str = "OK"
    source: str = ""
    sent_at: str | None = None
    discarded_at: str | None = None
    outcome_status: str = "未確認"
    outcome_memo: str = ""
    outcome_updated_at: str | None = None


@dataclass
class SentRecord:
    sent_id: str
    source_type: str
    text: str
    sent_at: str
    source_suggestion_id: str | None = None
    outcome_status: str = "未確認"
    outcome_memo: str = ""
    outcome_updated_at: str | None = None


@dataclass
class PartnerNote:
    text: str
    created_at: str | None = None


@dataclass
class ActivityEvent:
    event_id: str
    event_type: str
    created_at: str
    summary: str
    related_id: str | None = None


@dataclass
class MessageState:
    last_user_message: str = ""
    last_partner_message: str = ""
    last_suggested_message: str = ""
    last_sent_at: str | None = None
    last_received_at: str | None = None
    awaiting_user_action: bool = False
    awaiting_partner_reply: bool = False
    next_action: str = ""


@dataclass
class PartnerRecord:
    partner_id: str
    display_name: str
    app_name: str = ""
    status: str = "new_profile"
    created_at: str = ""
    updated_at: str = ""
    profile: PartnerProfile = field(default_factory=PartnerProfile)
    conversation: list[ConversationTurn] = field(default_factory=list)
    analysis: PartnerAnalysis = field(default_factory=PartnerAnalysis)
    pending_suggestions: list[PendingSuggestion] = field(default_factory=list)
    sent_records: list[SentRecord] = field(default_factory=list)
    message_state: MessageState = field(default_factory=MessageState)
    notes: list[PartnerNote] = field(default_factory=list)
    activity_log: list[ActivityEvent] = field(default_factory=list)


@dataclass
class TimelineEvent:
    created_at: str | None
    actor: str
    event_type: str
    summary: str
    text: str | None = None
    related_id: str | None = None


@dataclass
class GenerationRequest:
    target_profile: TargetProfile
    user_profile: UserProfile
    conversation_history: list[ConversationTurn] = field(default_factory=list)
    purpose: str = "first_message"
    desired_flirt_level: int | None = None
    current_stage: str = "first_message"


@dataclass
class GenerationResult:
    partner_analysis: str
    compatibility_topics: list[str]
    safe_topics: list[str]
    light_only_topics: list[str]
    avoid_topics: list[str]
    recommended_strategy: str
    message_candidates: list[str]
    best_message: str
    invite_suggestion: str | None
    flirt_allowed_level: int
    safety_notes: list[str]
    ng_examples: list[str]
    partner_temperature: str = "unknown"
