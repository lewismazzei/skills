from __future__ import annotations

import datetime as dt
import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "bootstrap.py"
SPEC = importlib.util.spec_from_file_location("scythe_bootstrap", MODULE_PATH)
bootstrap = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(bootstrap)


def usage(*, context: int, used: float, elapsed_fraction: float) -> dict:
    window_minutes = 10_080
    window = dt.timedelta(minutes=window_minutes)
    now = dt.datetime.now(dt.timezone.utc)
    reset_at = now + window * (1 - elapsed_fraction)
    return {
        "context_input_tokens": context,
        "weekly_used_percent": used,
        "weekly_window_minutes": window_minutes,
        "weekly_resets_at": reset_at.isoformat(),
    }


class PressureTests(unittest.TestCase):
    def test_context_watch_and_rollover_thresholds(self) -> None:
        self.assertEqual(bootstrap.pressure(usage(context=74_999, used=5, elapsed_fraction=0.05))["context"], "normal")
        self.assertEqual(bootstrap.pressure(usage(context=75_000, used=5, elapsed_fraction=0.05))["context"], "watch")
        self.assertEqual(bootstrap.pressure(usage(context=100_000, used=5, elapsed_fraction=0.05))["context"], "rollover")

    def test_high_usage_is_pace_aware_not_an_absolute_stop(self) -> None:
        report = bootstrap.pressure(usage(context=10_000, used=80, elapsed_fraction=0.06))
        self.assertEqual(report["weekly"], "high-burn")
        self.assertTrue(report["discretionary_model_work_allowed"])
        self.assertGreater(report["weekly_pace_ratio"], 13)

    def test_reserve_pauses_only_discretionary_model_work(self) -> None:
        report = bootstrap.pressure(usage(context=10_000, used=95, elapsed_fraction=0.95))
        self.assertEqual(report["weekly"], "reserve")
        self.assertFalse(report["discretionary_model_work_allowed"])


if __name__ == "__main__":
    unittest.main()
