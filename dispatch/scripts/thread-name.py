#!/usr/bin/env python3
"""Set and verify a dispatch worker's Codex thread display name."""

from __future__ import annotations

import argparse
import base64
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
import time
from typing import Callable


def default_socket(env: dict[str, str] | None = None, home: Path | None = None) -> Path:
    active_env = os.environ if env is None else env
    codex_home = active_env.get("CODEX_HOME", "").strip()
    root = Path(codex_home).expanduser() if codex_home else (home or Path.home()) / ".codex"
    return root / "app-server-control" / "app-server-control.sock"


DEFAULT_SOCKET = default_socket()
THREAD_ID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
DISPLAY_NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?/worker/[a-z]+-[a-z]+$")


class ThreadNameError(RuntimeError):
    """Raised when a thread display name cannot be set and verified."""


class AppServerClient:
    """Minimal JSON-RPC client for the app-server WebSocket Unix socket."""

    def __init__(self, socket_path: Path, timeout: float = 10.0):
        self.socket_path = socket_path
        self.timeout = timeout
        self.sock: socket.socket | None = None
        self.buffer = bytearray()
        self.next_id = 1

    def __enter__(self) -> "AppServerClient":
        if not self.socket_path.exists():
            raise ThreadNameError(f"Codex app-server control socket is missing: {self.socket_path}")
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
                        "name": "dispatch_thread_namer",
                        "title": "Dispatch Thread Namer",
                        "version": "1.0.0",
                    }
                },
            })
            response = self._response(0)
            if "result" not in response:
                raise ThreadNameError("Codex app-server initialize returned no result")
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
            except Exception:
                pass
            self.sock.close()
            self.sock = None

    def request(self, method: str, params: dict) -> dict:
        request_id = self.next_id
        self.next_id += 1
        self._send_json({"method": method, "id": request_id, "params": params})
        response = self._response(request_id)
        result = response.get("result")
        return result if isinstance(result, dict) else {}

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
        )
        self.sock.sendall(request.encode("ascii"))
        response = bytearray()
        while b"\r\n\r\n" not in response:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ThreadNameError("Codex app-server closed during WebSocket handshake")
            response.extend(chunk)
            if len(response) > 64 * 1024:
                raise ThreadNameError("Codex app-server returned an oversized WebSocket handshake")
        header_bytes, remainder = bytes(response).split(b"\r\n\r\n", 1)
        self.buffer.extend(remainder)
        lines = header_bytes.decode("latin-1").split("\r\n")
        if not lines or " 101 " not in f" {lines[0]} ":
            raise ThreadNameError(
                f"Codex app-server rejected WebSocket handshake: {lines[0] if lines else 'empty response'}"
            )
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                key_name, value = line.split(":", 1)
                headers[key_name.strip().lower()] = value.strip()
        expected = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()
        ).decode("ascii")
        if headers.get("sec-websocket-accept") != expected:
            raise ThreadNameError("Codex app-server returned an invalid WebSocket accept header")

    def _recv_exact(self, size: int) -> bytes:
        assert self.sock is not None
        while len(self.buffer) < size:
            chunk = self.sock.recv(max(4096, size - len(self.buffer)))
            if not chunk:
                raise ThreadNameError("Codex app-server connection closed")
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
                raise ThreadNameError("Codex app-server closed the WebSocket")
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
                raise ThreadNameError(f"Codex app-server returned invalid JSON: {error}") from error
            if not isinstance(message, dict) or message.get("id") != request_id:
                continue
            if "error" in message:
                error = message["error"]
                detail = error.get("message") if isinstance(error, dict) else str(error)
                raise ThreadNameError(f"Codex app-server request failed: {detail}")
            return message


def validate_inputs(thread_id: str, display_name: str) -> None:
    if not THREAD_ID_RE.fullmatch(thread_id):
        raise ThreadNameError(f"invalid Codex thread id: {thread_id}")
    if not DISPLAY_NAME_RE.fullmatch(display_name):
        raise ThreadNameError(
            "display name must be <project-slug>/worker/<adjective-noun> with no numeric suffix"
        )


def set_thread_name(
    thread_id: str,
    display_name: str,
    socket_path: Path = DEFAULT_SOCKET,
    timeout: float = 10.0,
    client_factory: Callable[[Path, float], AppServerClient] = AppServerClient,
) -> dict:
    validate_inputs(thread_id, display_name)
    with client_factory(socket_path, timeout) as client:
        client.request("thread/name/set", {"threadId": thread_id, "name": display_name})
        result = client.request("thread/read", {"threadId": thread_id, "includeTurns": False})
    thread = result.get("thread") if isinstance(result, dict) else None
    actual_name = thread.get("name") if isinstance(thread, dict) else None
    if actual_name != display_name:
        raise ThreadNameError(
            f"thread name verification failed: expected {display_name!r}, received {actual_name!r}"
        )
    return {"thread_id": thread_id, "display_name": display_name}


def thread_id_from_log(value: str) -> str:
    for line in value.splitlines():
        match = re.fullmatch(r"session id:\s*([0-9a-f-]+)\s*", line, flags=re.IGNORECASE)
        if match and THREAD_ID_RE.fullmatch(match.group(1)):
            return match.group(1)
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        candidate = ""
        if isinstance(event, dict) and event.get("type") == "thread.started":
            candidate = event.get("thread_id") or event.get("threadId") or ""
        if isinstance(candidate, str) and THREAD_ID_RE.fullmatch(candidate):
            return candidate
    return ""


def wait_for_thread_id(log_path: Path, wait_seconds: float, poll_seconds: float) -> str:
    if wait_seconds <= 0 or poll_seconds <= 0:
        raise ThreadNameError("wait and poll durations must be positive")
    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            with log_path.open("rb") as handle:
                thread_id = thread_id_from_log(handle.read(64 * 1024).decode("utf-8", errors="replace"))
        except FileNotFoundError:
            thread_id = ""
        if thread_id:
            return thread_id
        if time.monotonic() >= deadline:
            raise ThreadNameError(f"Codex thread id did not appear in {log_path} within {wait_seconds:g}s")
        time.sleep(poll_seconds)


def write_sidecar(worker_dir: Path, name: str, value: str) -> None:
    worker_dir.mkdir(parents=True, exist_ok=True)
    temporary = worker_dir / f".{name}.thread-name-{os.getpid()}"
    temporary.write_text(f"{value}\n", encoding="utf-8")
    os.replace(temporary, worker_dir / name)


def refresh_worker_state(
    worker_dir: Path,
    agent_id: str = "",
    display_name: str = "",
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> None:
    if worker_dir.parent.name != "workers":
        raise ThreadNameError(f"worker directory must be <dispatch-root>/workers/<pet-name>: {worker_dir}")
    command = [str(Path(__file__).with_name("dispatch-state.zsh")), "--worker", worker_dir.name]
    if agent_id:
        command.extend(["--agent-id", agent_id])
    if display_name:
        command.extend(["--display-name", display_name])
    runner(
        command,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "CODEX_DISPATCH_HOME": str(worker_dir.parent.parent)},
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--thread-id")
    source.add_argument("--log", type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--worker-dir", type=Path)
    parser.add_argument("--socket", type=Path, default=DEFAULT_SOCKET)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--wait-seconds", type=float, default=10.0)
    parser.add_argument("--poll-seconds", type=float, default=0.05)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    worker_dir = args.worker_dir.expanduser().resolve() if args.worker_dir else None
    try:
        thread_id = args.thread_id or wait_for_thread_id(
            args.log.expanduser().resolve(),
            args.wait_seconds,
            args.poll_seconds,
        )
        if worker_dir:
            write_sidecar(worker_dir, "agent_id", thread_id)
            refresh_worker_state(worker_dir, agent_id=thread_id)
        result = set_thread_name(
            thread_id,
            args.name,
            socket_path=args.socket.expanduser().resolve(),
            timeout=args.timeout,
        )
        if worker_dir:
            write_sidecar(worker_dir, "display_name", args.name)
            (worker_dir / "thread_name_error").unlink(missing_ok=True)
            refresh_worker_state(worker_dir, agent_id=thread_id, display_name=args.name)
    except Exception as error:
        if worker_dir:
            try:
                write_sidecar(worker_dir, "thread_name_error", str(error))
                refresh_worker_state(worker_dir)
            except OSError:
                pass
        print(f"thread-name: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
