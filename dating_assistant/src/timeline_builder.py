from __future__ import annotations

from .models import PartnerRecord, TimelineEvent

MIRRORED_ACTIVITY_TYPES = {"turn_added", "suggestion_sent", "suggestion_discarded", "note_added"}


def build_timeline_events(record: PartnerRecord) -> list[TimelineEvent]:
    events: list[TimelineEvent] = []
    suggestions_by_id = {suggestion.suggestion_id: suggestion for suggestion in record.pending_suggestions}
    logged_suggestion_creations = {
        activity.related_id for activity in record.activity_log if activity.event_type == "suggestion_created"
    }
    for turn in record.conversation:
        actor = "user" if turn.speaker == "user" else "partner"
        prefix = "送信" if actor == "user" else "受信"
        events.append(TimelineEvent(turn.timestamp, actor, "turn", prefix, turn.text))

    for suggestion in record.pending_suggestions:
        if suggestion.status == "sent":
            summary = f"候補送信済み: {suggestion.suggestion_id}"
            created_at = suggestion.sent_at or suggestion.created_at
        elif suggestion.status == "discarded":
            summary = f"候補破棄: {suggestion.suggestion_id}"
            created_at = suggestion.discarded_at or suggestion.created_at
        else:
            if suggestion.suggestion_id in logged_suggestion_creations:
                continue
            summary = f"返信候補生成: {suggestion.suggestion_id} / pending"
            created_at = suggestion.created_at
        events.append(TimelineEvent(created_at, "system", f"suggestion_{suggestion.status}", summary, suggestion.text, suggestion.suggestion_id))

    for note in record.notes:
        events.append(TimelineEvent(note.created_at, "system", "note", f"メモ追加: {note.text}" if note.created_at else f"メモ: {note.text}"))

    for activity in record.activity_log:
        if activity.event_type not in MIRRORED_ACTIVITY_TYPES:
            summary = activity.summary
            text = None
            if activity.event_type == "suggestion_created" and activity.related_id:
                summary = f"{summary}: {activity.related_id} / pending"
                suggestion = suggestions_by_id.get(activity.related_id)
                text = suggestion.text if suggestion else None
            events.append(
                TimelineEvent(activity.created_at, "system", activity.event_type, summary, text=text, related_id=activity.related_id)
            )
    return sorted(events, key=lambda event: (event.created_at is None, event.created_at or ""))


def format_timeline(record: PartnerRecord, limit: int | None = 30, verbose: bool = False) -> str:
    events = build_timeline_events(record)
    if limit is not None:
        events = events[-limit:]
    lines = []
    for event in events:
        timestamp = event.created_at or "時刻なし"
        detail = event.summary
        if event.text:
            detail += f": {_truncate(event.text, verbose)}"
        lines.append(f"{timestamp}  {event.actor:<7}  {detail}")
    history = "\n".join(lines) if lines else "- 履歴なし"
    return (
        "【タイムライン】\n"
        f"partner_id: {record.partner_id}\n"
        f"display_name: {record.display_name}\n"
        f"status: {record.status}\n"
        f"partner_temperature: {record.analysis.partner_temperature}\n"
        f"next_action: {record.message_state.next_action or '-'}\n\n"
        f"【履歴】\n{history}"
    )


def _truncate(text: str, verbose: bool) -> str:
    max_length = 500 if verbose else 100
    compact = " ".join(text.split())
    return compact if len(compact) <= max_length else compact[: max_length - 3] + "..."
