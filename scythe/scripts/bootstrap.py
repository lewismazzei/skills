#!/usr/bin/env python3
"""Read-only Scythe control-plane bootstrap and usage-pressure probe."""

from __future__ import annotations

import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time


HOME = Path.home()
SCYTHE_ROOT = Path(os.environ.get("SCYTHE_ROOT", "/home/lewis/projects/scythe")).resolve()
LUCIA_ROOT = Path(os.environ.get("LUCIA_ROOT", "/home/lewis/projects/lucia")).resolve()
CODEX_HOME = Path(os.environ.get("CODEX_HOME", str(HOME / ".codex"))).resolve()
CHECKPOINT = SCYTHE_ROOT / ".codex" / "control-plane.md"
WORKERS_ROOT = CODEX_HOME / "dispatch" / "workers"
CONTROLLERS = CODEX_HOME / "scythe" / "controllers.json"
TARGET_REPOS = {str(SCYTHE_ROOT), str(LUCIA_ROOT)}


def read_json_with_retry(path: Path) -> dict:
    for attempt in range(3):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            if attempt < 2:
                time.sleep(0.02)
    return {}


def read_sidecar(worker_dir: Path, name: str) -> str:
    try:
        return (worker_dir / name).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def worker_states() -> list[dict]:
    if not WORKERS_ROOT.is_dir():
        return []
    workers = []
    for worker_dir in sorted(WORKERS_ROOT.iterdir()):
        if not worker_dir.is_dir():
            continue
        state = read_json_with_retry(worker_dir / "state.json")
        repo = state.get("repo") or read_sidecar(worker_dir, "repo")
        if repo not in TARGET_REPOS:
            continue
        status = state.get("status") or read_sidecar(worker_dir, "status")
        if status not in {"running", "recovering", "ready", "blocked"}:
            continue
        workers.append(
            {
                "name": state.get("name") or worker_dir.name,
                "status": status,
                "repo": repo,
                "worktree": state.get("worktree") or read_sidecar(worker_dir, "worktree"),
                "updated_at": state.get("updated_at") or read_sidecar(worker_dir, "updated_at"),
            }
        )
    return workers


def atomic_write_json(path: Path, value: dict) -> None:
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
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def promote_pending_controller(registry: dict, project: dict, active: dict, pending: dict) -> dict:
    activated_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    successor = dict(pending)
    successor.pop("worker_snapshot", None)
    successor["state"] = "active"
    successor["activated_at"] = activated_at
    successor["source"] = "successor-self-promotion"
    predecessor = dict(active)
    predecessor["state"] = "retired"
    predecessor["retired_at"] = activated_at
    predecessor["successor_thread_id"] = successor.get("thread_id")
    project.setdefault("history", []).append(predecessor)
    project["active"] = successor
    project.pop("pending", None)
    project["updated_at"] = activated_at
    atomic_write_json(CONTROLLERS, registry)
    return successor


def controller_state() -> dict:
    thread_id = os.environ.get("CODEX_THREAD_ID", "").strip()
    report = {"registry": str(CONTROLLERS), "thread_id": thread_id or None, "authority": "unregistered"}
    if not CONTROLLERS.is_file():
        return report
    lock_path = CONTROLLERS.with_suffix(CONTROLLERS.suffix + ".lock")
    with lock_path.open("a+", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        registry = read_json_with_retry(CONTROLLERS)
        project = ((registry.get("projects") or {}).get("scythe") or {})
        active = project.get("active") if isinstance(project, dict) else None
        pending = project.get("pending") if isinstance(project, dict) else None
        if (
            thread_id
            and isinstance(active, dict)
            and isinstance(pending, dict)
            and pending.get("thread_id") == thread_id
            and pending.get("state") == "starting"
        ):
            active = promote_pending_controller(registry, project, active, pending)
            pending = None
    if not isinstance(active, dict):
        report["authority"] = "invalid-registry"
        return report
    report["active"] = {
        "display_name": active.get("display_name"),
        "thread_id": active.get("thread_id"),
    }
    if thread_id and active.get("thread_id") == thread_id:
        if isinstance(pending, dict) and pending.get("state") == "starting":
            report["authority"] = "handoff-in-progress"
            report["pending"] = {
                "display_name": pending.get("display_name"),
                "thread_id": pending.get("thread_id"),
            }
        else:
            report["authority"] = "active"
    elif thread_id and isinstance(pending, dict) and pending.get("thread_id") == thread_id:
        report["authority"] = "pending"
        report["pending"] = {
            "display_name": pending.get("display_name"),
            "state": pending.get("state"),
        }
    else:
        report["authority"] = "superseded"
    if active.get("thread_id"):
        report["active_deeplink"] = f"codex://threads/{active['thread_id']}"
    return report


def continuation_policy(controller: dict) -> dict:
    authority = controller.get("authority")
    if authority in {"active", "unregistered"}:
        return {
            "mode": "act-then-report",
            "status_only_allowed": False,
            "repair_recoverable_control_plane_faults": True,
            "required_before_final": [
                "execute-safe-immediate-actions",
                "repair-recoverable-control-plane-faults",
                "confirm-async-owner-is-advancing",
                "persist-updated-frontier",
            ],
            "stop_only_when": [
                "no-safe-synchronous-action-remains",
                "lucia-owns-confirmed-asynchronous-next-action",
                "authority-or-explicit-approval-boundary",
            ],
        }
    return {
        "mode": "report-authoritative-controller",
        "status_only_allowed": True,
        "repair_recoverable_control_plane_faults": False,
        "required_before_final": ["report-active-controller"],
        "stop_only_when": ["authority-boundary"],
    }


def candidate_sessions() -> list[Path]:
    sessions = CODEX_HOME / "sessions"
    if not sessions.is_dir():
        return []
    thread_id = os.environ.get("CODEX_THREAD_ID", "").strip()
    if thread_id:
        exact = list(sessions.rglob(f"*{thread_id}*.jsonl"))
        if exact:
            return sorted(exact, key=lambda path: path.stat().st_mtime, reverse=True)
    return sorted(sessions.rglob("*.jsonl"), key=lambda path: path.stat().st_mtime, reverse=True)[:50]


def latest_usage() -> dict:
    for session in candidate_sessions():
        latest = None
        try:
            with session.open(encoding="utf-8") as handle:
                for line in handle:
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    payload = record.get("payload", {})
                    if record.get("type") == "event_msg" and payload.get("type") == "token_count":
                        latest = record
        except OSError:
            continue
        if latest:
            payload = latest.get("payload", {})
            info = payload.get("info") or {}
            last = info.get("last_token_usage") or {}
            primary = ((payload.get("rate_limits") or {}).get("primary") or {})
            resets_at = primary.get("resets_at")
            reset_iso = None
            if isinstance(resets_at, (int, float)):
                reset_iso = dt.datetime.fromtimestamp(resets_at, tz=dt.timezone.utc).isoformat()
            return {
                "session": str(session),
                "timestamp": latest.get("timestamp"),
                "context_input_tokens": last.get("input_tokens"),
                "context_total_tokens": last.get("total_tokens"),
                "model_context_window": info.get("model_context_window"),
                "weekly_used_percent": primary.get("used_percent"),
                "weekly_window_minutes": primary.get("window_minutes"),
                "weekly_resets_at": reset_iso,
            }
    return {}


def pressure(usage: dict) -> dict:
    context = usage.get("context_input_tokens")
    weekly = usage.get("weekly_used_percent")
    window_minutes = usage.get("weekly_window_minutes")
    reset_text = usage.get("weekly_resets_at")
    context_state = "unknown"
    if isinstance(context, (int, float)):
        context_state = "rollover" if context >= 150_000 else "watch" if context >= 125_000 else "normal"
    elapsed_percent = None
    pace_ratio = None
    projected_percent = None
    if isinstance(weekly, (int, float)) and isinstance(window_minutes, (int, float)) and reset_text:
        try:
            reset_at = dt.datetime.fromisoformat(reset_text)
            window_seconds = float(window_minutes) * 60
            start_at = reset_at - dt.timedelta(seconds=window_seconds)
            elapsed = (dt.datetime.now(dt.timezone.utc) - start_at).total_seconds()
            elapsed_fraction = min(1.0, max(1 / window_seconds, elapsed / window_seconds))
            elapsed_percent = elapsed_fraction * 100
            pace_ratio = (float(weekly) / 100) / elapsed_fraction
            projected_percent = min(999.0, float(weekly) / elapsed_fraction)
        except (TypeError, ValueError):
            pass
    weekly_state = "unknown"
    next_period_adjustment = "hold"
    if isinstance(weekly, (int, float)):
        if weekly >= 95:
            weekly_state = "reserve"
        elif pace_ratio is not None and pace_ratio > 2:
            weekly_state = "high-burn"
            next_period_adjustment = "decrease-one-step"
        elif pace_ratio is not None and pace_ratio > 1.25:
            weekly_state = "elevated"
            next_period_adjustment = "decrease-one-step"
        elif elapsed_percent is not None and elapsed_percent >= 75 and pace_ratio is not None and pace_ratio < 0.75:
            weekly_state = "surplus"
            next_period_adjustment = "increase-one-step"
        else:
            weekly_state = "normal"
    surplus_points = None
    if elapsed_percent is not None and isinstance(weekly, (int, float)):
        surplus_points = max(0.0, elapsed_percent - float(weekly))
    return {
        "context": context_state,
        "weekly": weekly_state,
        "weekly_elapsed_percent": round(elapsed_percent, 1) if elapsed_percent is not None else None,
        "weekly_pace_ratio": round(pace_ratio, 2) if pace_ratio is not None else None,
        "weekly_projected_percent_at_reset": round(projected_percent, 1) if projected_percent is not None else None,
        "weekly_surplus_percent_points": round(surplus_points, 1) if surplus_points is not None else None,
        "next_period_adjustment": next_period_adjustment,
        "rollover_recommended": context_state == "rollover",
        "discretionary_model_work_allowed": weekly_state != "reserve",
    }


def service_state(unit: str) -> dict:
    try:
        result = subprocess.run(
            ["systemctl", "show", unit, "--property=ActiveState,SubState,MainPID", "--no-pager"],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"unit": unit, "active": "unknown"}
    fields = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    return {
        "unit": unit,
        "active": fields.get("ActiveState", "unknown"),
        "substate": fields.get("SubState", "unknown"),
        "pid": int(fields.get("MainPID", "0") or 0),
    }


def main() -> None:
    usage = latest_usage()
    controller = controller_state()
    report = {
        "schema": 1,
        "checkpoint": {"path": str(CHECKPOINT), "exists": CHECKPOINT.is_file()},
        "controller": controller,
        "continuation": continuation_policy(controller),
        "roots": {"scythe": str(SCYTHE_ROOT), "lucia": str(LUCIA_ROOT)},
        "usage": usage,
        "pressure": pressure(usage),
        "workers": worker_states(),
        "watchers": [
            service_state("lucia-lucia-watch.service"),
            service_state("lucia-scythe-watch.service"),
        ],
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
