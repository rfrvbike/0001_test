from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from x_auto_ops.redaction import contains_sensitive_marker, redact_sensitive_text
from x_auto_ops.retry_queue import RetryQueue


class RedactionAndRetryQueueTests(unittest.TestCase):
    def test_redacts_required_sensitive_markers(self) -> None:
        text = (
            "API_KEY=abc TOKEN=def SECRET=ghi COOKIE=jkl "
            "AUTHORIZATION=Bearer xyz abc123secret"
        )

        redacted = redact_sensitive_text(text)

        self.assertNotIn("API_KEY", redacted)
        self.assertNotIn("TOKEN", redacted)
        self.assertNotIn("SECRET", redacted)
        self.assertNotIn("COOKIE", redacted)
        self.assertNotIn("AUTHORIZATION", redacted)
        self.assertNotIn("abc123secret", redacted)
        self.assertIn("[REDACTED]", redacted)
        self.assertFalse(contains_sensitive_marker(redacted), redacted)

    def test_retry_queue_enqueue_size_and_dequeue_ready(self) -> None:
        queue = RetryQueue()
        now = datetime(2026, 6, 1, tzinfo=timezone.utc)

        first = queue.enqueue("query one", 60, enqueue_time=now)
        second = queue.enqueue("query two", 120, enqueue_time=now, retry_count=2)

        self.assertEqual(queue.size(), 2)
        self.assertEqual(first.retry_count, 0)
        self.assertEqual(second.retry_count, 2)
        self.assertEqual(queue.dequeue_ready(now + timedelta(seconds=59)), [])
        self.assertEqual(queue.size(), 2)

        ready = queue.dequeue_ready(now + timedelta(seconds=61))

        self.assertEqual([task.query for task in ready], ["query one"])
        self.assertEqual(queue.size(), 1)
        self.assertEqual(queue.dequeue_ready(now + timedelta(seconds=121))[0].query, "query two")
        self.assertEqual(queue.size(), 0)

    def test_retry_queue_handles_multiple_immediate_tasks(self) -> None:
        queue = RetryQueue()
        now = datetime(2026, 6, 1, tzinfo=timezone.utc)
        queue.enqueue("a", 0, enqueue_time=now)
        queue.enqueue("b", None, enqueue_time=now)
        queue.enqueue("c", -5, enqueue_time=now)

        ready = queue.dequeue_ready(now)

        self.assertEqual([task.query for task in ready], ["a", "b", "c"])
        self.assertEqual(queue.size(), 0)


if __name__ == "__main__":
    unittest.main()
