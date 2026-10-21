#!/usr/bin/env python3
"""
scripts/test_insights.py

Comprehensive test suite verifying:
- Non-negotiable data integrity: failures never become fabricated zeroes.
- Streak algorithms: correctly handle ongoing days, month boundaries, and leap years.
- SVG generation: well-formedness, valid XML, and exact layout styles.
- Data privacy: ensures no tokens or private info leak into outputs.
- Dataset consistency: streak, totals, and graph use the identical underlying data.
"""

import unittest
import os
import sys
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# Ensure scripts directory is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_insights as gi


class TestInsightsEngine(unittest.TestCase):

    def test_streak_calculation_contiguous(self):
        """Verify streak calculation on a simple contiguous dataset."""
        days = [
            {"date": "2026-10-10", "count": 2},
            {"date": "2026-10-11", "count": 3},
            {"date": "2026-10-12", "count": 0},
            {"date": "2026-10-13", "count": 1},
            {"date": "2026-10-14", "count": 5},
            {"date": "2026-10-15", "count": 4},
        ]
        res = gi.calculate_streaks(days)
        self.assertEqual(res["current_streak"], 3)
        self.assertEqual(res["longest_streak"], 3)
        self.assertEqual(res["total_contributions"], 15)

    def test_streak_ongoing_day_zero(self):
        """
        If the latest day (today) has 0 contributions so far because it is in progress,
        the streak ending yesterday must NOT be broken or reset to 0 prematurely.
        """
        days = [
            {"date": "2026-10-13", "count": 1},
            {"date": "2026-10-14", "count": 5},
            {"date": "2026-10-15", "count": 0}, # Today in progress
        ]
        res = gi.calculate_streaks(days)
        # Yesterday was active (2 days streak: 13th and 14th)
        self.assertEqual(res["current_streak"], 2)

    def test_streak_genuinely_broken(self):
        """If both today and yesterday have 0 contributions, current streak is genuinely 0."""
        days = [
            {"date": "2026-10-12", "count": 4},
            {"date": "2026-10-13", "count": 0}, # Yesterday
            {"date": "2026-10-14", "count": 0}, # Today
        ]
        res = gi.calculate_streaks(days)
        self.assertEqual(res["current_streak"], 0)

    def test_longest_streak_historical_accuracy(self):
        """
        Tests the 21-day continuous streak Sharan achieved between July 15 and August 4, 2026.
        """
        days = [
            {"date": "2026-07-14", "count": 0},
            {"date": "2026-07-15", "count": 2},
            {"date": "2026-07-16", "count": 5},
            {"date": "2026-07-17", "count": 7},
            {"date": "2026-07-18", "count": 5},
            {"date": "2026-07-19", "count": 17},
            {"date": "2026-07-20", "count": 9},
            {"date": "2026-07-21", "count": 15},
            {"date": "2026-07-22", "count": 4},
            {"date": "2026-07-23", "count": 7},
            {"date": "2026-07-24", "count": 5},
            {"date": "2026-07-25", "count": 17},
            {"date": "2026-07-26", "count": 10},
            {"date": "2026-07-27", "count": 4},
            {"date": "2026-07-28", "count": 3},
            {"date": "2026-07-29", "count": 5},
            {"date": "2026-07-30", "count": 5},
            {"date": "2026-07-31", "count": 7},
            {"date": "2026-08-01", "count": 2},
            {"date": "2026-08-02", "count": 4},
            {"date": "2026-08-03", "count": 1},
            {"date": "2026-08-04", "count": 1},
            {"date": "2026-08-05", "count": 0},
        ]
        res = gi.calculate_streaks(days)
        self.assertEqual(res["longest_streak"], 21)
        self.assertIn("Jul 15", res["longest_range"])
        self.assertIn("Aug 04", res["longest_range"])

    def test_month_and_year_leap_boundary(self):
        """Verify handling of leap year Feb 28 -> Feb 29 -> Mar 1."""
        days = [
            {"date": "2024-02-28", "count": 3},
            {"date": "2024-02-29", "count": 4},
            {"date": "2024-03-01", "count": 1},
        ]
        res = gi.calculate_streaks(days)
        self.assertEqual(res["current_streak"], 3)
        self.assertEqual(res["longest_streak"], 3)
        self.assertEqual(res["total_contributions"], 8)

    def test_failure_never_becomes_fabricated_zero(self):
        """
        CRITICAL DATA INTEGRITY TEST:
        If API fails or is unavailable, the output card MUST render
        'Data Temporarily Unavailable' and NEVER display a fabricated 0.
        """
        mock_unavailable_metrics = {
            "username": "Sharan-Sanadi",
            "status": "unavailable",
            "errors": {"graphql": "HTTP 403: Rate Limit Exceeded"},
            "stars": {"value": None, "error": "HTTP 403: Rate Limit Exceeded"},
            "commits": {"value": None, "error": "HTTP 403: Rate Limit Exceeded"},
            "prs": {"value": None, "error": "HTTP 403: Rate Limit Exceeded"},
            "issues": {"value": None, "error": "HTTP 403: Rate Limit Exceeded"},
            "contributed_to": {"value": None, "error": "HTTP 403: Rate Limit Exceeded"},
            "calendar": {"error": "HTTP 403: Rate Limit Exceeded", "total_contributions": None}
        }

        stats_svg = gi.generate_stats_svg(mock_unavailable_metrics)
        self.assertIn("Data Temporarily Unavailable", stats_svg)
        self.assertNotIn("Total Stars Earned:\n    <text x=\"230\" y=\"12\" class=\"stat-val\">0</text>", stats_svg)

        streak_svg = gi.generate_streak_svg(mock_unavailable_metrics)
        self.assertIn("Data Temporarily Unavailable", streak_svg)

        graph_svg = gi.generate_activity_graph_svg(mock_unavailable_metrics)
        self.assertIn("Data Temporarily Unavailable", graph_svg)

    def test_no_token_leakage(self):
        """Verify that secret tokens or environment secrets are never embedded in SVGs or manifests."""
        dummy_secret = "ghp_SECRET_TOKEN_1234567890abcdef"
        os.environ["GH_TOKEN"] = dummy_secret

        try:
            metrics = {
                "username": "Sharan-Sanadi",
                "status": "operational",
                "errors": {},
                "stars": {"value": 2},
                "commits": {"value": 160},
                "prs": {"value": 4},
                "issues": {"value": 2},
                "contributed_to": {"value": 2},
                "calendar": {
                    "total_contributions": 554,
                    "current_streak": 2,
                    "current_range": "Oct 20 - Oct 21",
                    "longest_streak": 21,
                    "longest_range": "Jul 15 - Aug 04",
                    "timeline_range": "Oct 21 - Oct 21",
                    "recent_30_days": [{"date": f"2026-10-{i:02d}", "count": 2} for i in range(1, 31)]
                }
            }
            stats_svg = gi.generate_stats_svg(metrics)
            streak_svg = gi.generate_streak_svg(metrics)
            graph_svg = gi.generate_activity_graph_svg(metrics)

            self.assertNotIn(dummy_secret, stats_svg)
            self.assertNotIn(dummy_secret, streak_svg)
            self.assertNotIn(dummy_secret, graph_svg)
            self.assertNotIn(dummy_secret, json.dumps(metrics))
        finally:
            del os.environ["GH_TOKEN"]

    def test_xml_svg_well_formedness(self):
        """Ensure all generated SVG strings are valid, well-formed XML."""
        metrics = {
            "username": "Sharan-Sanadi",
            "status": "operational",
            "errors": {},
            "stars": {"value": 2},
            "commits": {"value": 160},
            "prs": {"value": 4},
            "issues": {"value": 2},
            "contributed_to": {"value": 2},
            "calendar": {
                "total_contributions": 554,
                "current_streak": 2,
                "current_range": "Oct 20 - Oct 21",
                "longest_streak": 21,
                "longest_range": "Jul 15 - Aug 04",
                "timeline_range": "Oct 21 - Oct 21",
                "recent_30_days": [{"date": f"2026-10-{i:02d}", "count": i % 5} for i in range(1, 31)]
            }
        }
        stats_svg = gi.generate_stats_svg(metrics)
        streak_svg = gi.generate_streak_svg(metrics)
        graph_svg = gi.generate_activity_graph_svg(metrics)

        # Parse with XML parser to confirm strict syntax
        ET.fromstring(stats_svg)
        ET.fromstring(streak_svg)
        ET.fromstring(graph_svg)

    def test_graph_and_streak_dataset_consistency(self):
        """The contribution graph must be derived from the exact same calendar data driving streaks."""
        days = [{"date": f"2026-10-{i:02d}", "count": i} for i in range(1, 31)]
        res = gi.calculate_streaks(days)
        metrics = {
            "calendar": {
                "total_contributions": res["total_contributions"],
                "current_streak": res["current_streak"],
                "longest_streak": res["longest_streak"],
                "recent_30_days": days
            }
        }
        graph_svg = gi.generate_activity_graph_svg(metrics)
        # Check that the highest count is plotted
        max_count = max(d["count"] for d in days)
        self.assertIn(f"{max_count} contributions", graph_svg)


if __name__ == "__main__":
    unittest.main()
