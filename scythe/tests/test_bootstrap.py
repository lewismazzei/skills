from __future__ import annotations

import datetime as dt
import importlib.util
from pathlib import Path
import json
import os
import tempfile
import unittest
from unittest import mock


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
        self.assertEqual(bootstrap.pressure(usage(context=124_999, used=5, elapsed_fraction=0.05))["context"], "normal")
        self.assertEqual(bootstrap.pressure(usage(context=125_000, used=5, elapsed_fraction=0.05))["context"], "watch")
        self.assertEqual(bootstrap.pressure(usage(context=149_999, used=5, elapsed_fraction=0.05))["context"], "watch")
        self.assertEqual(bootstrap.pressure(usage(context=150_000, used=5, elapsed_fraction=0.05))["context"], "rollover")

    def test_high_usage_is_pace_aware_not_an_absolute_stop(self) -> None:
        report = bootstrap.pressure(usage(context=10_000, used=80, elapsed_fraction=0.06))
        self.assertEqual(report["weekly"], "high-burn")
        self.assertTrue(report["discretionary_model_work_allowed"])
        self.assertGreater(report["weekly_pace_ratio"], 13)

    def test_reserve_pauses_only_discretionary_model_work(self) -> None:
        report = bootstrap.pressure(usage(context=10_000, used=95, elapsed_fraction=0.95))
        self.assertEqual(report["weekly"], "reserve")
        self.assertFalse(report["discretionary_model_work_allowed"])

    def test_late_surplus_recommends_one_step_increase_next_period(self) -> None:
        report = bootstrap.pressure(usage(context=10_000, used=40, elapsed_fraction=0.9))
        self.assertEqual(report["weekly"], "surplus")
        self.assertEqual(report["next_period_adjustment"], "increase-one-step")
        self.assertGreater(report["weekly_surplus_percent_points"], 49)

    def test_early_low_usage_does_not_prematurely_increase_next_period(self) -> None:
        report = bootstrap.pressure(usage(context=10_000, used=5, elapsed_fraction=0.2))
        self.assertEqual(report["weekly"], "normal")
        self.assertEqual(report["next_period_adjustment"], "hold")


class ControllerStateTests(unittest.TestCase):
    def test_current_controller_is_authoritative(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "controllers.json"
            registry.write_text(json.dumps({
                "schema": 1,
                "projects": {"scythe": {"active": {
                    "thread_id": "thread-current",
                    "display_name": "scythe/controller/nimble-vista",
                }}},
            }), encoding="utf-8")
            with mock.patch.object(bootstrap, "CONTROLLERS", registry), mock.patch.dict(
                os.environ, {"CODEX_THREAD_ID": "thread-current"}
            ):
                report = bootstrap.controller_state()

        self.assertEqual(report["authority"], "active")
        self.assertEqual(report["active_deeplink"], "codex://threads/thread-current")

    def test_old_controller_is_superseded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "controllers.json"
            registry.write_text(json.dumps({
                "schema": 1,
                "projects": {"scythe": {"active": {
                    "thread_id": "thread-new",
                    "display_name": "scythe/controller/clear-maple",
                }}},
            }), encoding="utf-8")
            with mock.patch.object(bootstrap, "CONTROLLERS", registry), mock.patch.dict(
                os.environ, {"CODEX_THREAD_ID": "thread-old"}
            ):
                report = bootstrap.controller_state()

        self.assertEqual(report["authority"], "superseded")
        self.assertEqual(report["active"]["thread_id"], "thread-new")

    def test_executing_pending_successor_self_promotes_after_lock_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "controllers.json"
            registry.write_text(json.dumps({
                "schema": 1,
                "projects": {"scythe": {
                    "active": {"thread_id": "thread-old", "display_name": None, "state": "active"},
                    "pending": {
                        "thread_id": "thread-new",
                        "display_name": "scythe/controller/clear-maple",
                        "pet_name": "clear-maple",
                        "project": "scythe",
                        "role": "controller",
                        "state": "starting",
                    },
                    "history": [],
                }},
            }), encoding="utf-8")
            with mock.patch.object(bootstrap, "CONTROLLERS", registry), mock.patch.dict(
                os.environ, {"CODEX_THREAD_ID": "thread-new"}
            ):
                report = bootstrap.controller_state()
            persisted = json.loads(registry.read_text(encoding="utf-8"))["projects"]["scythe"]

        self.assertEqual(report["authority"], "active")
        self.assertEqual(persisted["active"]["thread_id"], "thread-new")
        self.assertEqual(persisted["history"][0]["thread_id"], "thread-old")
        self.assertNotIn("pending", persisted)

    def test_predecessor_does_not_overlap_an_unresolved_starting_successor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "controllers.json"
            registry.write_text(json.dumps({
                "schema": 1,
                "projects": {"scythe": {
                    "active": {"thread_id": "thread-old", "display_name": None, "state": "active"},
                    "pending": {
                        "thread_id": "thread-new",
                        "display_name": "scythe/controller/clear-maple",
                        "state": "starting",
                    },
                }},
            }), encoding="utf-8")
            with mock.patch.object(bootstrap, "CONTROLLERS", registry), mock.patch.dict(
                os.environ, {"CODEX_THREAD_ID": "thread-old"}
            ):
                report = bootstrap.controller_state()

        self.assertEqual(report["authority"], "handoff-in-progress")
        self.assertEqual(report["pending"]["thread_id"], "thread-new")


class ContinuationPolicyTests(unittest.TestCase):
    def test_active_controller_cannot_finish_with_status_only_when_action_remains(self) -> None:
        policy = bootstrap.continuation_policy({"authority": "active"})

        self.assertEqual(policy["mode"], "act-then-report")
        self.assertFalse(policy["status_only_allowed"])
        self.assertTrue(policy["repair_recoverable_control_plane_faults"])
        self.assertIn("execute-safe-immediate-actions", policy["required_before_final"])
        self.assertIn("confirm-async-owner-is-advancing", policy["required_before_final"])

    def test_unregistered_controller_uses_the_same_act_before_final_gate(self) -> None:
        policy = bootstrap.continuation_policy({"authority": "unregistered"})

        self.assertEqual(policy["mode"], "act-then-report")
        self.assertFalse(policy["status_only_allowed"])

    def test_non_authoritative_controller_reports_owner_without_acting(self) -> None:
        policy = bootstrap.continuation_policy({"authority": "superseded"})

        self.assertEqual(policy["mode"], "report-authoritative-controller")
        self.assertTrue(policy["status_only_allowed"])
        self.assertFalse(policy["repair_recoverable_control_plane_faults"])


if __name__ == "__main__":
    unittest.main()
