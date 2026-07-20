from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "thread-name.py"
SPEC = importlib.util.spec_from_file_location("dispatch_thread_name", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class FakeClient:
    def __init__(self, socket_path: Path, timeout: float):
        self.socket_path = socket_path
        self.timeout = timeout
        self.calls: list[tuple[str, dict]] = []
        self.name = ""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return None

    def request(self, method: str, params: dict) -> dict:
        self.calls.append((method, params))
        if method == "thread/name/set":
            self.name = params["name"]
            return {}
        if method == "thread/read":
            return {"thread": {"name": self.name}}
        raise AssertionError(method)


class ThreadNameTests(unittest.TestCase):
    def test_control_socket_honors_codex_home(self):
        self.assertEqual(
            MODULE.default_socket({"CODEX_HOME": "/srv/codex"}, home=Path("/home/ignored")),
            Path("/srv/codex/app-server-control/app-server-control.sock"),
        )
        self.assertEqual(
            MODULE.default_socket({}, home=Path("/home/lewis")),
            Path("/home/lewis/.codex/app-server-control/app-server-control.sock"),
        )

    def test_sets_and_verifies_clean_worker_display_name(self):
        instances: list[FakeClient] = []

        def factory(socket_path: Path, timeout: float) -> FakeClient:
            client = FakeClient(socket_path, timeout)
            instances.append(client)
            return client

        result = MODULE.set_thread_name(
            "019f8016-c8e5-7ae0-8935-6e332c13f90a",
            "scythe/worker/aesthetic-vista",
            socket_path=Path("/tmp/control.sock"),
            timeout=3.0,
            client_factory=factory,
        )

        self.assertEqual(result["display_name"], "scythe/worker/aesthetic-vista")
        self.assertEqual(instances[0].calls, [
            (
                "thread/name/set",
                {
                    "threadId": "019f8016-c8e5-7ae0-8935-6e332c13f90a",
                    "name": "scythe/worker/aesthetic-vista",
                },
            ),
            (
                "thread/read",
                {
                    "threadId": "019f8016-c8e5-7ae0-8935-6e332c13f90a",
                    "includeTurns": False,
                },
            ),
        ])

    def test_parses_human_and_jsonl_startup_logs(self):
        thread_id = "019f8016-c8e5-7ae0-8935-6e332c13f90a"
        self.assertEqual(MODULE.thread_id_from_log(f"session id: {thread_id}\n"), thread_id)
        self.assertEqual(
            MODULE.thread_id_from_log(json.dumps({"type": "thread.started", "thread_id": thread_id})),
            thread_id,
        )
        self.assertEqual(MODULE.thread_id_from_log("not started\n"), "")

    def test_sidecar_persistence_feeds_dispatch_state(self):
        with tempfile.TemporaryDirectory() as directory:
            worker_dir = Path(directory) / "workers" / "aesthetic-vista"
            MODULE.write_sidecar(worker_dir, "agent_id", "019f8016-c8e5-7ae0-8935-6e332c13f90a")
            MODULE.write_sidecar(worker_dir, "display_name", "scythe/worker/aesthetic-vista")
            self.assertEqual(
                (worker_dir / "agent_id").read_text(encoding="utf-8").strip(),
                "019f8016-c8e5-7ae0-8935-6e332c13f90a",
            )
            self.assertEqual(
                (worker_dir / "display_name").read_text(encoding="utf-8").strip(),
                "scythe/worker/aesthetic-vista",
            )

            calls = []
            MODULE.refresh_worker_state(
                worker_dir,
                agent_id="019f8016-c8e5-7ae0-8935-6e332c13f90a",
                display_name="scythe/worker/aesthetic-vista",
                runner=lambda *args, **kwargs: calls.append((args, kwargs)),
            )
            self.assertEqual(calls[0][0][0][-6:], [
                "--worker",
                "aesthetic-vista",
                "--agent-id",
                "019f8016-c8e5-7ae0-8935-6e332c13f90a",
                "--display-name",
                "scythe/worker/aesthetic-vista",
            ])
            self.assertEqual(calls[0][1]["env"]["CODEX_DISPATCH_HOME"], directory)

    def test_refuses_numbered_pet_name(self):
        with self.assertRaisesRegex(MODULE.ThreadNameError, "no numeric suffix"):
            MODULE.validate_inputs(
                "019f8016-c8e5-7ae0-8935-6e332c13f90a",
                "scythe/worker/wise-bridge-2",
            )

    def test_refuses_malformed_thread_id(self):
        with self.assertRaisesRegex(MODULE.ThreadNameError, "invalid Codex thread id"):
            MODULE.validate_inputs("thread-1", "scythe/worker/wise-bridge")

    def test_detached_helper_persists_its_own_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            dispatch_root = Path(directory) / "dispatch"
            worker_dir = dispatch_root / "workers" / "wise-bridge"
            worker_dir.mkdir(parents=True)
            result = subprocess.run(
                [
                    "python3",
                    str(SCRIPT),
                    "--thread-id",
                    "019f8016-c8e5-7ae0-8935-6e332c13f90a",
                    "--name",
                    "scythe/worker/wise-bridge",
                    "--worker-dir",
                    str(worker_dir),
                    "--socket",
                    str(Path(directory) / "missing.sock"),
                ],
                capture_output=True,
                text=True,
                env={**os.environ, "CODEX_DISPATCH_HOME": str(dispatch_root)},
            )
            self.assertEqual(result.returncode, 1)
            state = json.loads((worker_dir / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["agent_id"], "019f8016-c8e5-7ae0-8935-6e332c13f90a")
            self.assertIn("control socket is missing", state["thread_name_error"])


if __name__ == "__main__":
    unittest.main()
