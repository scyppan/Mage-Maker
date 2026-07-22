import unittest

from mage_maker.timeline_events import (
    normalize_timeline_event,
    normalize_timeline_events,
    timeline_event_summary,
)


class TimelineEventTests(unittest.TestCase):
    def test_events_are_normalized_and_sorted_by_partial_dates(self):
        events = normalize_timeline_events(
            [
                {
                    "event_id": "later",
                    "event_type": "relocated",
                    "detail": "London",
                    "date": "2001-4",
                    "note": "A move.",
                },
                {
                    "event_id": "earlier",
                    "event_type": "started_school",
                    "detail": "Hogwarts",
                    "date": "1998",
                    "note": "First year.",
                },
                {
                    "event_id": "unknown",
                    "event_type": "custom",
                    "detail": "Undated memory",
                    "date": "",
                    "note": "",
                },
            ]
        )
        self.assertEqual(["earlier", "later", "unknown"], [event["event_id"] for event in events])
        self.assertEqual("2001-04", events[1]["date"])

    def test_common_event_summaries_include_the_detail(self):
        self.assertEqual(
            "Started at Hogwarts school!",
            timeline_event_summary(
                {"event_type": "started_school", "detail": "Hogwarts"}
            ),
        )
        self.assertEqual(
            "Relocated to Hogsmeade",
            timeline_event_summary(
                {"event_type": "relocated", "detail": "Hogsmeade"}
            ),
        )
        self.assertEqual(
            "Had a child!",
            timeline_event_summary(
                {"event_type": "had_child", "detail": "Horace"}
            ),
        )

    def test_custom_event_requires_a_description(self):
        with self.assertRaisesRegex(ValueError, "needs an event description"):
            normalize_timeline_event(
                {
                    "event_type": "custom",
                    "detail": "",
                    "date": "2000",
                }
            )

    def test_invalid_calendar_date_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "valid calendar date"):
            normalize_timeline_event(
                {
                    "event_type": "got_married",
                    "detail": "Partner",
                    "date": "2000-02-31",
                }
            )


if __name__ == "__main__":
    unittest.main()
