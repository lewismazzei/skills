from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "rollover.py"
SPEC = importlib.util.spec_from_file_location("scythe_rollover", MODULE_PATH)
rollover = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(rollover)


class FakeClient:
    def __init__(self, _path: Path, *, fail_turn: bool = False, on_turn_start=None):
        self.fail_turn = fail_turn
        self.on_turn_start = on_turn_start
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return None

    def request(self, method: str, params: dict) -> dict:
        self.calls.append((method, params))
        if method == "thread/start":
            return {"model": "gpt-5.6-sol", "thread": {"id": "thread-new"}}
        if method == "thread/name/set":
            return {}
        if method == "turn/start":
            if self.on_turn_start:
                self.on_turn_start()
            if self.fail_turn:
                raise rollover.RolloverError("synthetic turn failure")
            return {"turn": {"id": "turn-new"}}
        if method == "thread/compact/start":
            return {}
        raise AssertionError(method)


def write_checkpoint(path: Path) -> None:
    path.write_text(
        "# Checkpoint\n\n<!-- Stable checkpoint: update in place. -->\n\n"
        "## Objective\n\nShip.\n\n## Frontier\n\nRollover.\n\n"
        "## Active lifecycle\n\nLucia owns workers.\n",
        encoding="utf-8",
    )


class RolloverTests(unittest.TestCase):
    def perform(self, root: Path, client: FakeClient) -> dict:
        checkpoint = root / "control-plane.md"
        registry = root / "controllers.json"
        write_checkpoint(checkpoint)
        reconciliation = {"workers": [{
            "name": "aesthetic-vista",
            "repo": "/repo",
            "status": "running",
            "worktree": "/worktree",
        }]}
        with mock.patch.object(rollover, "reconcile_workers", return_value=reconciliation):
            return rollover.perform_rollover(
                project="scythe",
                cwd=root,
                checkpoint=checkpoint,
                registry_path=registry,
                socket_path=root / "app-server.sock",
                current_thread_id="thread-old",
                client_factory=lambda _path: client,
                pet_candidates=["nimble-vista"],
                now=lambda: "2026-07-20T15:00:00Z",
            )

    def test_creates_names_and_starts_successor_without_waiting_for_completion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            client = FakeClient(root / "unused")
            report = self.perform(root, client)
            registry = json.loads((root / "controllers.json").read_text(encoding="utf-8"))

        self.assertEqual([method for method, _params in client.calls], [
            "thread/start", "thread/name/set", "turn/start",
        ])
        self.assertEqual(client.calls[1][1]["name"], "scythe/controller/nimble-vista")
        self.assertEqual(client.calls[2][1], {
            "effort": "medium",
            "input": [{"type": "text", "text": "$scythe"}],
            "serviceTier": "default",
            "threadId": "thread-new",
        })
        self.assertEqual(report["status"], "accepted")
        self.assertEqual(report["desktop_deeplink"], "codex://threads/thread-new")
        self.assertEqual(
            report["handoff_text"],
            "Controller rollover complete.\n\n"
            "New controller: `scythe/controller/nimble-vista`\n"
            "Successor thread ID: `thread-new`\n"
            "Desktop deep link: `codex://threads/thread-new`\n\n"
            "If the deep link does not open, search chats for the exact controller name.",
        )
        self.assertNotIn("](codex://", report["handoff_text"])
        project = registry["projects"]["scythe"]
        self.assertEqual(project["active"]["thread_id"], "thread-new")
        self.assertEqual(project["history"][0]["thread_id"], "thread-old")
        self.assertNotIn("pending", project)

    def test_turn_failure_leaves_current_controller_authoritative(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            client = FakeClient(root / "unused", fail_turn=True)
            with self.assertRaisesRegex(rollover.RolloverError, "synthetic turn failure"):
                self.perform(root, client)
            registry = json.loads((root / "controllers.json").read_text(encoding="utf-8"))

        project = registry["projects"]["scythe"]
        self.assertEqual(project["active"]["thread_id"], "thread-old")
        self.assertEqual(project["history"][0]["thread_id"], "thread-new")
        self.assertEqual(project["history"][0]["state"], "failed")
        self.assertNotIn("pending", project)

    def test_stale_controller_cannot_roll_over(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint = root / "control-plane.md"
            registry = root / "controllers.json"
            write_checkpoint(checkpoint)
            registry.write_text(json.dumps({
                "schema": 1,
                "projects": {"scythe": {"history": [], "active": {
                    "thread_id": "thread-authoritative",
                    "display_name": "scythe/controller/clear-maple",
                }}},
            }), encoding="utf-8")
            with mock.patch.object(rollover, "reconcile_workers", return_value={"workers": []}):
                with self.assertRaisesRegex(rollover.RolloverError, "not authoritative"):
                    rollover.perform_rollover(
                        project="scythe",
                        cwd=root,
                        checkpoint=checkpoint,
                        registry_path=registry,
                        socket_path=root / "unused.sock",
                        current_thread_id="thread-stale",
                        client_factory=lambda path: FakeClient(path),
                        pet_candidates=["warm-willow"],
                    )

    def test_unresolved_successor_blocks_a_second_rollover(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint = root / "control-plane.md"
            registry = root / "controllers.json"
            write_checkpoint(checkpoint)
            registry.write_text(json.dumps({
                "schema": 1,
                "projects": {"scythe": {
                    "history": [],
                    "active": {"thread_id": "thread-old", "state": "active"},
                    "pending": {
                        "thread_id": "thread-pending",
                        "display_name": "scythe/controller/quiet-vista",
                        "state": "starting",
                    },
                }},
            }), encoding="utf-8")
            with mock.patch.object(rollover, "reconcile_workers", return_value={"workers": []}):
                with self.assertRaisesRegex(rollover.RolloverError, "unresolved"):
                    rollover.perform_rollover(
                        project="scythe",
                        cwd=root,
                        checkpoint=checkpoint,
                        registry_path=registry,
                        socket_path=root / "unused.sock",
                        current_thread_id="thread-old",
                        client_factory=lambda _path: self.fail("client must not be opened"),
                        pet_candidates=["warm-willow"],
                    )

            persisted = json.loads(registry.read_text(encoding="utf-8"))["projects"]["scythe"]
            self.assertEqual(persisted["pending"]["thread_id"], "thread-pending")

    def test_pet_collision_chooses_a_fresh_pair_without_numbering(self) -> None:
        project = {"history": [{"pet_name": "wise-bridge"}]}
        selected = rollover.allocate_pet_name(project, ["wise-bridge", "aesthetic-vista"])
        self.assertEqual(selected, "aesthetic-vista")
        self.assertNotRegex(selected, r"-\d+$")

    def test_stale_checkpoint_fails_before_thread_creation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.md"
            write_checkpoint(path)
            old = dt.datetime.now().timestamp() - 901
            os.utime(path, (old, old))
            with self.assertRaisesRegex(rollover.RolloverError, "stale"):
                rollover.validate_checkpoint(path, rollover.MAX_CHECKPOINT_BYTES, 900)

    def test_compaction_fallback_is_asynchronous(self) -> None:
        client = FakeClient(Path("/unused"))
        report = rollover.request_compaction(
            current_thread_id="thread-old",
            socket_path=Path("/unused"),
            client_factory=lambda _path: client,
        )
        self.assertEqual(client.calls, [("thread/compact/start", {"threadId": "thread-old"})])
        self.assertEqual(report, {"status": "accepted", "thread_id": "thread-old"})


if __name__ == "__main__":
    unittest.main()
