import unittest

from src.models import ActivityEvent, ConversationTurn, PartnerNote, PartnerRecord, PendingSuggestion
from src.partner_store import partner_from_mapping
from src.timeline_builder import build_timeline_events, format_timeline


class PartnerTimelineTests(unittest.TestCase):
    def build_partner(self):
        return PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            conversation=[
                ConversationTurn("user", "u" * 160, "2026-06-05T10:02:00+09:00"),
                ConversationTurn("partner", "partner reply", "2026-06-05T10:03:00+09:00"),
            ],
            pending_suggestions=[
                PendingSuggestion("suggestion_001", "reply", "pending text", "2026-06-05T10:04:00+09:00"),
                PendingSuggestion(
                    "suggestion_002", "reply", "sent text", "2026-06-05T10:05:00+09:00", status="sent", sent_at="2026-06-05T10:06:00+09:00"
                ),
                PendingSuggestion(
                    "suggestion_003",
                    "reply",
                    "discarded text",
                    "2026-06-05T10:07:00+09:00",
                    status="discarded",
                    discarded_at="2026-06-05T10:08:00+09:00",
                ),
            ],
            notes=[PartnerNote("note text", "2026-06-05T10:09:00+09:00"), PartnerNote("old note")],
            activity_log=[
                ActivityEvent("event_001", "partner_created", "2026-06-05T10:01:00+09:00", "partnerを作成"),
                ActivityEvent("event_002", "status_updated", "2026-06-05T10:10:00+09:00", "status: new_profile -> chatting"),
            ],
        )

    def test_builds_all_sources_in_created_at_order(self):
        events = build_timeline_events(self.build_partner())
        summaries = [event.summary for event in events]
        self.assertIn("送信", summaries)
        self.assertIn("受信", summaries)
        self.assertIn("返信候補生成: suggestion_001 / pending", summaries)
        self.assertIn("候補送信済み: suggestion_002", summaries)
        self.assertIn("候補破棄: suggestion_003", summaries)
        self.assertIn("partnerを作成", summaries)
        self.assertEqual(events[-1].created_at, None)
        dated = [event.created_at for event in events if event.created_at]
        self.assertEqual(dated, sorted(dated))

    def test_limit_and_verbose(self):
        partner = self.build_partner()
        limited = format_timeline(partner, limit=2)
        self.assertEqual(len(limited.split("【履歴】\n", 1)[1].splitlines()), 2)
        normal = format_timeline(partner, limit=None, verbose=False)
        verbose = format_timeline(partner, limit=None, verbose=True)
        self.assertIn("...", normal)
        self.assertIn("u" * 160, verbose)

    def test_old_partner_without_activity_log_and_structured_notes_loads(self):
        partner = partner_from_mapping({"partner_id": "partner_001", "display_name": "old", "notes": ["legacy note"]})
        self.assertEqual(partner.activity_log, [])
        self.assertEqual(partner.notes[0].text, "legacy note")
        self.assertIn("時刻なし", format_timeline(partner))

    def test_logged_suggestion_shows_created_and_sent_events(self):
        partner = PartnerRecord(
            partner_id="partner_001",
            display_name="sample",
            pending_suggestions=[
                PendingSuggestion(
                    "suggestion_001", "reply", "text", "2026-06-05T10:01:00+09:00", status="sent", sent_at="2026-06-05T10:02:00+09:00"
                )
            ],
            activity_log=[
                ActivityEvent(
                    "event_001",
                    "suggestion_created",
                    "2026-06-05T10:01:00+09:00",
                    "返信候補を生成",
                    "suggestion_001",
                )
            ],
        )
        output = format_timeline(partner)
        self.assertIn("返信候補を生成: suggestion_001 / pending", output)
        self.assertIn("候補送信済み: suggestion_001", output)


if __name__ == "__main__":
    unittest.main()
