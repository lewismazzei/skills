#!/usr/bin/env python3
"""Create and activate a fresh Scythe controller through Codex app-server."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import socket
import struct
import subprocess
import sys
import tempfile
from typing import Callable, Iterable


HOME = Path.home()
CODEX_HOME = Path(os.environ.get("CODEX_HOME", str(HOME / ".codex"))).resolve()
SCYTHE_ROOT = Path(os.environ.get("SCYTHE_ROOT", "/home/lewis/projects/scythe")).resolve()
CHECKPOINT = SCYTHE_ROOT / ".codex" / "control-plane.md"
REGISTRY = CODEX_HOME / "scythe" / "controllers.json"
CONTROL_SOCKET = CODEX_HOME / "app-server-control" / "app-server-control.sock"
BOOTSTRAP = Path(__file__).with_name("bootstrap.py")
DEFAULT_MODEL = "gpt-5.6-sol"
DEFAULT_EFFORT = "xhigh"
DEFAULT_SERVICE_TIER = "default"  # Standard service in Codex UI terminology.
MAX_CHECKPOINT_BYTES = 16 * 1024
MAX_CHECKPOINT_AGE_SECONDS = 15 * 60
CHECKPOINT_HEADINGS = (
    "Objective",
    "Frontier",
    "Active lifecycle",
    "Active exceptions",
    "Exact next actions",
    "Boundaries",
    "Durable sources",
)

ADJECTIVES = (
    "amber", "brisk", "calm", "cedar", "clear", "clever", "copper", "crisp",
    "deft", "eager", "gentle", "golden", "honest", "lucid", "lucky", "mellow",
    "nimble", "quiet", "rapid", "steady", "tidy", "vivid", "warm", "wise",
)
NOUNS = (
    "anchor", "atlas", "beacon", "bridge", "canyon", "comet", "compass", "harbor",
    "lantern", "maple", "meadow", "mint", "orbit", "pebble", "pixel", "quartz",
    "ribbon", "summit", "valley", "velvet", "vista", "willow",
)


class RolloverError(RuntimeError):
    """A fail-closed rollover error."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate_slug(value: str, label: str) -> str:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
        raise RolloverError(f"invalid {label}: {value!r}; expected lowercase kebab-case")
    return value


def display_name(project: str, role: str, pet_name: str) -> str:
    return f"{validate_slug(project, 'project')}/{validate_slug(role, 'role')}/{validate_slug(pet_name, 'pet name')}"


def successor_handoff_text(*, controller_name: str, thread_id: str) -> str:
    deeplink = f"codex://threads/{thread_id}"
    return (
        "Controller rollover complete.\n\n"
        f"New controller: `{controller_name}`\n"
        f"Successor thread ID: `{thread_id}`\n"
        f"Desktop deep link: `{deeplink}`\n\n"
        "If the deep link does not open, search chats for the exact controller name."
    )


def all_pet_names() -> list[str]:
    return [f"{adjective}-{noun}" for adjective in ADJECTIVES for noun in NOUNS]


def reserved_pet_names(project_state: dict) -> set[str]:
    records = [project_state.get("active"), project_state.get("pending")]
    records.extend(project_state.get("history") or [])
    return {
        record.get("pet_name")
        for record in records
        if isinstance(record, dict) and isinstance(record.get("pet_name"), str)
    }


def allocate_pet_name(project_state: dict, candidates: Iterable[str] | None = None) -> str:
    used = reserved_pet_names(project_state)
    available = list(candidates) if candidates is not None else all_pet_names()
    if candidates is None:
        secrets.SystemRandom().shuffle(available)
    for candidate in available:
        validate_slug(candidate, "pet name")
        if candidate not in used:
            return candidate
    raise RolloverError("pet-name namespace exhausted; refusing a numbered suffix")


def atomic_write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            temp_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, path)
    except OSError as error:
        raise RolloverError(f"controller registry update failed: {error}") from error
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def read_registry(path: Path) -> dict:
    if not path.exists():
        return {"schema": 1, "projects": {}}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RolloverError(f"controller registry is unreadable: {error}") from error
    if not isinstance(value, dict) or value.get("schema") != 1 or not isinstance(value.get("projects"), dict):
        raise RolloverError("controller registry has an unsupported schema")
    return value


def validate_checkpoint(path: Path, max_bytes: int, max_age_seconds: int) -> dict:
    try:
        stat = path.stat()
        content = path.read_text(encoding="utf-8")
    except OSError as error:
        raise RolloverError(f"stable checkpoint is unavailable: {error}") from error
    if stat.st_size > max_bytes:
        raise RolloverError(f"stable checkpoint is {stat.st_size} bytes; limit is {max_bytes}")
    age_seconds = max(0, int(dt.datetime.now().timestamp() - stat.st_mtime))
    if age_seconds > max_age_seconds:
        raise RolloverError(
            f"stable checkpoint is stale ({age_seconds}s old); refresh it before rollover"
        )
    if "<!-- Stable checkpoint:" not in content:
        raise RolloverError("stable checkpoint is malformed: missing stable checkpoint marker")
    headings = re.findall(r"^## (.+?)\s*$", content, flags=re.MULTILINE)
    if headings != list(CHECKPOINT_HEADINGS) or "[Verified, historical]" in content:
        raise RolloverError(
            "stable checkpoint does not satisfy the current-state contract"
        )
    action_match = re.search(
        r"^## Exact next actions\s*$\n(.*?)(?=^## |\Z)",
        content,
        flags=re.MULTILINE | re.DOTALL,
    )
    action_numbers = (
        [int(value) for value in re.findall(r"^(\d+)\.\s+", action_match.group(1), flags=re.MULTILINE)]
        if action_match
        else []
    )
    if not action_numbers or action_numbers != list(range(1, len(action_numbers) + 1)):
        raise RolloverError(
            "stable checkpoint does not satisfy the current-state contract"
        )
    return {"path": str(path), "bytes": stat.st_size, "age_seconds": age_seconds}


def reconcile_workers(bootstrap_path: Path, cwd: Path) -> dict:
    try:
        result = subprocess.run(
            [sys.executable, str(bootstrap_path)],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RolloverError(f"Lucia reconciliation failed: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        raise RolloverError(f"Lucia reconciliation failed: {detail}")
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RolloverError(f"Lucia reconciliation returned invalid JSON: {error}") from error
    if not isinstance(report, dict) or not isinstance(report.get("workers"), list):
        raise RolloverError("Lucia reconciliation omitted canonical worker state")
    return report


class AppServerClient:
    """Minimal JSON-RPC-over-WebSocket client for the local Unix control socket."""

    def __init__(self, socket_path: Path, timeout: float = 10.0):
        self.socket_path = socket_path
        self.timeout = timeout
        self.sock: socket.socket | None = None
        self.buffer = bytearray()
        self.next_id = 1

    def __enter__(self) -> "AppServerClient":
        if not self.socket_path.exists():
            raise RolloverError(f"Codex app-server control socket is missing: {self.socket_path}")
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect(str(self.socket_path))
            self.sock = sock
            self._handshake()
            self._send_json({
                "method": "initialize",
                "id": 0,
                "params": {
                    "clientInfo": {
                        "name": "scythe_rollover",
                        "title": "Scythe Rollover",
                        "version": "1.0.0",
                    }
                },
            })
            response = self._response(0)
            if "result" not in response:
                raise RolloverError("Codex app-server initialize returned no result")
            self._send_json({"method": "initialized", "params": {}})
            return self
        except Exception:
            sock.close()
            self.sock = None
            raise

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.sock is not None:
            try:
                self._send_frame(b"", opcode=0x8)
            except OSError:
                pass
            self.sock.close()
            self.sock = None

    def request(self, method: str, params: dict) -> dict:
        request_id = self.next_id
        self.next_id += 1
        self._send_json({"method": method, "id": request_id, "params": params})
        response = self._response(request_id)
        if "error" in response:
            error = response["error"]
            message = error.get("message") if isinstance(error, dict) else str(error)
            raise RolloverError(f"Codex app-server {method} failed: {message}")
        result = response.get("result")
        if not isinstance(result, dict):
            raise RolloverError(f"Codex app-server {method} returned no result")
        return result

    def _handshake(self) -> None:
        assert self.sock is not None
        key = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
        request = (
            "GET / HTTP/1.1\r\n"
            "Host: localhost\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        ).encode("ascii")
        self.sock.sendall(request)
        while b"\r\n\r\n" not in self.buffer:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RolloverError("Codex app-server closed during WebSocket handshake")
            self.buffer.extend(chunk)
        header_bytes, remainder = bytes(self.buffer).split(b"\r\n\r\n", 1)
        self.buffer = bytearray(remainder)
        lines = header_bytes.decode("latin-1").split("\r\n")
        if not lines or " 101 " not in f" {lines[0]} ":
            raise RolloverError(f"Codex app-server rejected WebSocket handshake: {lines[0] if lines else 'empty response'}")
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                key_name, value = line.split(":", 1)
                headers[key_name.strip().lower()] = value.strip()
        expected = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()
        ).decode("ascii")
        if headers.get("sec-websocket-accept") != expected:
            raise RolloverError("Codex app-server returned an invalid WebSocket accept header")

    def _recv_exact(self, size: int) -> bytes:
        assert self.sock is not None
        while len(self.buffer) < size:
            chunk = self.sock.recv(max(4096, size - len(self.buffer)))
            if not chunk:
                raise RolloverError("Codex app-server connection closed")
            self.buffer.extend(chunk)
        value = bytes(self.buffer[:size])
        del self.buffer[:size]
        return value

    def _send_frame(self, payload: bytes, opcode: int = 0x1) -> None:
        assert self.sock is not None
        first = 0x80 | opcode
        length = len(payload)
        if length < 126:
            header = bytes((first, 0x80 | length))
        elif length < 65536:
            header = bytes((first, 0x80 | 126)) + struct.pack("!H", length)
        else:
            header = bytes((first, 0x80 | 127)) + struct.pack("!Q", length)
        mask = secrets.token_bytes(4)
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        self.sock.sendall(header + mask + masked)

    def _recv_message(self) -> str:
        fragments = bytearray()
        started = False
        while True:
            first, second = self._recv_exact(2)
            final = bool(first & 0x80)
            opcode = first & 0x0F
            masked = bool(second & 0x80)
            length = second & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._recv_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._recv_exact(8))[0]
            mask = self._recv_exact(4) if masked else b""
            payload = self._recv_exact(length)
            if masked:
                payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
            if opcode == 0x8:
                raise RolloverError("Codex app-server closed the WebSocket")
            if opcode == 0x9:
                self._send_frame(payload, opcode=0xA)
                continue
            if opcode == 0xA:
                continue
            if opcode == 0x1:
                fragments = bytearray(payload)
                started = True
            elif opcode == 0x0 and started:
                fragments.extend(payload)
            else:
                continue
            if final:
                return fragments.decode("utf-8")

    def _send_json(self, message: dict) -> None:
        self._send_frame(json.dumps(message, separators=(",", ":")).encode("utf-8"))

    def _response(self, request_id: int) -> dict:
        while True:
            try:
                message = json.loads(self._recv_message())
            except json.JSONDecodeError as error:
                raise RolloverError(f"Codex app-server returned invalid JSON: {error}") from error
            if isinstance(message, dict) and message.get("id") == request_id:
                if "error" in message:
                    error = message["error"]
                    detail = error.get("message") if isinstance(error, dict) else str(error)
                    raise RolloverError(f"Codex app-server request failed: {detail}")
                return message


def controller_record(*, project: str, thread_id: str, pet_name: str | None, state: str, now: str) -> dict:
    return {
        "activated_at": now,
        "display_name": display_name(project, "controller", pet_name) if pet_name else None,
        "pet_name": pet_name,
        "project": project,
        "role": "controller",
        "state": state,
        "thread_id": thread_id,
    }


def request_compaction(
    *,
    current_thread_id: str,
    socket_path: Path,
    client_factory: Callable[[Path], AppServerClient] | None = None,
) -> dict:
    if not current_thread_id:
        raise RolloverError("CODEX_THREAD_ID is missing; refusing an unowned compaction")
    factory = client_factory or (lambda path: AppServerClient(path))
    with factory(socket_path) as client:
        client.request("thread/compact/start", {"threadId": current_thread_id})
    return {"status": "accepted", "thread_id": current_thread_id}


def perform_rollover(
    *,
    project: str,
    cwd: Path,
    checkpoint: Path,
    registry_path: Path,
    socket_path: Path,
    current_thread_id: str,
    model: str = DEFAULT_MODEL,
    effort: str = DEFAULT_EFFORT,
    service_tier: str = DEFAULT_SERVICE_TIER,
    max_checkpoint_bytes: int = MAX_CHECKPOINT_BYTES,
    max_checkpoint_age_seconds: int = MAX_CHECKPOINT_AGE_SECONDS,
    bootstrap_path: Path = BOOTSTRAP,
    client_factory: Callable[[Path], AppServerClient] | None = None,
    pet_candidates: Iterable[str] | None = None,
    now: Callable[[], str] = utc_now,
) -> dict:
    project = validate_slug(project, "project")
    if not current_thread_id:
        raise RolloverError("CODEX_THREAD_ID is missing; refusing an unowned rollover")
    checkpoint_evidence = validate_checkpoint(checkpoint, max_checkpoint_bytes, max_checkpoint_age_seconds)
    reconciliation = reconcile_workers(bootstrap_path, cwd)
    workers = reconciliation.get("workers") or []
    worker_snapshot = [
        {
            "name": worker.get("name"),
            "repo": worker.get("repo"),
            "status": worker.get("status"),
            "worktree": worker.get("worktree"),
        }
        for worker in workers
        if isinstance(worker, dict)
    ]

    registry_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = registry_path.with_suffix(registry_path.suffix + ".lock")
    factory = client_factory or (lambda path: AppServerClient(path))
    with lock_path.open("a+", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        registry = read_registry(registry_path)
        project_state = registry["projects"].setdefault(project, {"history": []})
        active = project_state.get("active")
        if active is None:
            active = controller_record(
                project=project,
                thread_id=current_thread_id,
                pet_name=None,
                state="active",
                now=now(),
            )
            active["source"] = "adopted-at-first-rollover"
            project_state["active"] = active
            atomic_write_json(registry_path, registry)
        elif not isinstance(active, dict) or active.get("thread_id") != current_thread_id:
            owner = active.get("thread_id") if isinstance(active, dict) else "unknown"
            owner_name = active.get("display_name") if isinstance(active, dict) else None
            raise RolloverError(
                f"current thread is not authoritative; active controller is {owner_name or owner} ({owner})"
            )
        unresolved = project_state.get("pending")
        if isinstance(unresolved, dict):
            unresolved_id = unresolved.get("thread_id") or "unknown"
            unresolved_name = unresolved.get("display_name") or unresolved_id
            raise RolloverError(
                f"controller handoff is unresolved for {unresolved_name} ({unresolved_id}); refusing a second successor"
            )

        pet_name = allocate_pet_name(project_state, pet_candidates)
        successor_name = display_name(project, "controller", pet_name)
        started_at = now()
        with factory(socket_path) as client:
            thread_result = client.request(
                "thread/start",
                {
                    "allowProviderModelFallback": False,
                    "cwd": str(cwd),
                    "model": model,
                    "personality": "pragmatic",
                    "serviceTier": service_tier,
                },
            )
            thread = thread_result.get("thread")
            successor_thread_id = thread.get("id") if isinstance(thread, dict) else None
            if not isinstance(successor_thread_id, str) or not successor_thread_id:
                raise RolloverError("Codex app-server thread/start returned no thread id")
            pending = controller_record(
                project=project,
                thread_id=successor_thread_id,
                pet_name=pet_name,
                state="starting",
                now=started_at,
            )
            pending["predecessor_thread_id"] = current_thread_id
            pending["worker_snapshot"] = worker_snapshot
            project_state["pending"] = pending
            atomic_write_json(registry_path, registry)

            try:
                actual_model = thread_result.get("model")
                if actual_model != model:
                    raise RolloverError(f"Codex created successor with {actual_model!r}, expected {model!r}")
                client.request("thread/name/set", {"threadId": successor_thread_id, "name": successor_name})
                turn_result = client.request(
                    "turn/start",
                    {
                        "effort": effort,
                        "input": [{"type": "text", "text": "$scythe"}],
                        "serviceTier": service_tier,
                        "threadId": successor_thread_id,
                    },
                )
                turn = turn_result.get("turn")
                turn_id = turn.get("id") if isinstance(turn, dict) else None
                if not isinstance(turn_id, str) or not turn_id:
                    raise RolloverError("Codex app-server turn/start returned no turn id")
            except Exception as error:
                failed = dict(pending)
                failed["state"] = "failed"
                failed["failed_at"] = now()
                failed["error"] = str(error)
                project_state.setdefault("history", []).append(failed)
                project_state.pop("pending", None)
                atomic_write_json(registry_path, registry)
                raise

            activated_at = now()
            successor = dict(pending)
            successor.pop("worker_snapshot", None)
            successor["state"] = "active"
            successor["activated_at"] = activated_at
            successor["turn_id"] = turn_id
            predecessor = dict(active)
            predecessor["state"] = "retired"
            predecessor["retired_at"] = activated_at
            predecessor["successor_thread_id"] = successor_thread_id
            history = project_state.setdefault("history", [])
            history.append(predecessor)
            project_state["active"] = successor
            project_state.pop("pending", None)
            project_state["updated_at"] = activated_at
            atomic_write_json(registry_path, registry)

    return {
        "checkpoint": checkpoint_evidence,
        "desktop_deeplink": f"codex://threads/{successor_thread_id}",
        "display_name": successor_name,
        "effort": effort,
        "handoff_text": successor_handoff_text(
            controller_name=successor_name,
            thread_id=successor_thread_id,
        ),
        "model": model,
        "pet_name": pet_name,
        "project": project,
        "registry": str(registry_path),
        "service_tier": service_tier,
        "status": "accepted",
        "thread_id": successor_thread_id,
        "turn_id": turn_id,
        "worker_snapshot": worker_snapshot,
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--project", default="scythe")
    value.add_argument("--cwd", type=Path, default=SCYTHE_ROOT)
    value.add_argument("--checkpoint", type=Path, default=CHECKPOINT)
    value.add_argument("--registry", type=Path, default=REGISTRY)
    value.add_argument("--socket", type=Path, default=CONTROL_SOCKET)
    value.add_argument("--model", default=DEFAULT_MODEL)
    value.add_argument("--effort", default=DEFAULT_EFFORT)
    value.add_argument("--service-tier", default=DEFAULT_SERVICE_TIER)
    value.add_argument("--max-checkpoint-bytes", type=int, default=MAX_CHECKPOINT_BYTES)
    value.add_argument("--max-checkpoint-age-seconds", type=int, default=MAX_CHECKPOINT_AGE_SECONDS)
    value.add_argument(
        "--compact-current",
        action="store_true",
        help="Request asynchronous compaction of the current authoritative thread instead of rollover.",
    )
    return value


def main() -> int:
    args = parser().parse_args()
    current_thread_id = os.environ.get("CODEX_THREAD_ID", "").strip()
    try:
        report = request_compaction(
            current_thread_id=current_thread_id,
            socket_path=args.socket.resolve(),
        )
    except RolloverError as error:
        print(json.dumps({"status": "failed", "error": str(error)}, sort_keys=True))
        return 1
    report["controller_thread_policy"] = "permanent"
    report["successor_created"] = False
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
