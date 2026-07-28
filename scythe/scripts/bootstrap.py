#!/usr/bin/env python3
"""Read-only Scythe control-plane bootstrap and usage-pressure probe."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import time


HOME = Path.home()
SCYTHE_ROOT = Path(os.environ.get("SCYTHE_ROOT", "/home/lewis/projects/scythe")).resolve()
LUCIA_ROOT = Path(os.environ.get("LUCIA_ROOT", "/home/lewis/projects/lucia")).resolve()
CODEX_HOME = Path(os.environ.get("CODEX_HOME", str(HOME / ".codex"))).resolve()
CHECKPOINT = SCYTHE_ROOT / ".codex" / "control-plane.md"
WORKERS_ROOT = CODEX_HOME / "dispatch" / "workers"
CONTROLLERS = CODEX_HOME / "scythe" / "controllers.json"
TARGET_REPOS = {str(SCYTHE_ROOT), str(LUCIA_ROOT)}
MAX_CHECKPOINT_BYTES = 16 * 1024
CHECKPOINT_HEADINGS = (
    "Objective",
    "Frontier",
    "Active lifecycle",
    "Active exceptions",
    "Exact next actions",
    "Boundaries",
    "Durable sources",
)
AUTHORITATIVE_CONTROLLER = re.compile(
    r"Controller `[^`]+` is authoritative at thread `([^`]+)`"
)


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


def controller_state() -> dict:
    thread_id = os.environ.get("CODEX_THREAD_ID", "").strip()
    report = {"registry": str(CONTROLLERS), "thread_id": thread_id or None, "authority": "unregistered"}
    if not CONTROLLERS.is_file():
        return report
    registry = read_json_with_retry(CONTROLLERS)
    project = ((registry.get("projects") or {}).get("scythe") or {})
    active = project.get("active") if isinstance(project, dict) else None
    pending = project.get("pending") if isinstance(project, dict) else None
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


def checkpoint_state(
    path: Path = CHECKPOINT,
    controller: dict | None = None,
    *,
    max_bytes: int = MAX_CHECKPOINT_BYTES,
) -> dict:
    report = {
        "path": str(path),
        "exists": path.is_file(),
        "max_bytes": max_bytes,
        "status": "missing",
        "violations": [],
    }
    if not path.is_file():
        return report
    try:
        payload = path.read_bytes()
        content = payload.decode("utf-8")
        stat = path.stat()
    except (OSError, UnicodeDecodeError) as error:
        report["status"] = "malformed"
        report["violations"] = [f"unreadable:{error}"]
        return report
    report["bytes"] = len(payload)
    report["age_seconds"] = max(0, int(time.time() - stat.st_mtime))
    violations: list[str] = []
    if len(payload) > max_bytes:
        violations.append("oversize")

    headings = re.findall(r"^## (.+?)\s*$", content, flags=re.MULTILINE)
    report["headings"] = headings
    for heading in CHECKPOINT_HEADINGS:
        if heading not in headings:
            violations.append(f"missing-heading:{heading}")
    for heading in headings:
        if heading not in CHECKPOINT_HEADINGS:
            violations.append(f"unexpected-heading:{heading}")
    if "[Verified, historical]" in content:
        violations.append("historical-content")

    claims = AUTHORITATIVE_CONTROLLER.findall(content)
    report["authoritative_controller_claims"] = claims
    active = (controller or {}).get("active") or {}
    expected_thread_id = active.get("thread_id")
    if (controller or {}).get("authority") in {"active", "handoff-in-progress"}:
        if len(claims) != 1:
            violations.append(f"authoritative-controller-count:{len(claims)}")
        elif expected_thread_id and claims[0] != expected_thread_id:
            violations.append(f"authoritative-controller-mismatch:{claims[0]}")

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
    report["next_action_numbers"] = action_numbers
    if not action_numbers:
        violations.append("missing-next-actions")
    elif action_numbers != list(range(1, len(action_numbers) + 1)):
        violations.append("noncontiguous-next-actions")

    report["violations"] = list(dict.fromkeys(violations))
    if any(value.startswith(("missing-heading:", "unreadable:")) for value in violations):
        report["status"] = "malformed"
    else:
        report["status"] = "stale" if violations else "healthy"
    return report


def continuation_policy(
    controller: dict,
    checkpoint: dict | None = None,
    *,
    request: str = "continue",
) -> dict:
    if request == "status":
        return {
            "mode": "read-only-status",
            "status_only_allowed": True,
            "mutations_allowed": False,
            "repair_recoverable_control_plane_faults": False,
            "required_before_final": ["report-observed-state"],
            "stop_only_when": ["observed-state-reported"],
        }
    authority = controller.get("authority")
    if authority in {"active", "unregistered"}:
        required = [
            "execute-safe-immediate-actions",
            "repair-recoverable-control-plane-faults",
            "confirm-async-owner-is-advancing",
            "persist-updated-frontier",
        ]
        if checkpoint is not None and checkpoint.get("status") != "healthy":
            required.append("reconcile-checkpoint-hygiene")
        return {
            "mode": "act-then-report",
            "status_only_allowed": False,
            "mutations_allowed": True,
            "repair_recoverable_control_plane_faults": True,
            "required_before_final": required,
            "stop_only_when": [
                "no-safe-synchronous-action-remains",
                "lucia-owns-confirmed-asynchronous-next-action",
                "authority-or-explicit-approval-boundary",
            ],
        }
    return {
        "mode": "report-authoritative-controller",
        "status_only_allowed": True,
        "mutations_allowed": False,
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
        context_state = "native-compaction" if context >= 150_000 else "watch" if context >= 125_000 else "normal"
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
        "rollover_recommended": False,
        "native_compaction_expected": context_state == "native-compaction",
        "controller_thread_policy": "permanent",
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


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument(
        "--request",
        choices=("continue", "status"),
        default="continue",
        help="Select an acting continuation or a mutation-free status observation.",
    )
    return value


def main() -> None:
    args = parser().parse_args()
    usage = latest_usage()
    controller = controller_state()
    checkpoint = checkpoint_state(CHECKPOINT, controller)
    report = {
        "schema": 1,
        "checkpoint": checkpoint,
        "controller": controller,
        "continuation": continuation_policy(controller, checkpoint, request=args.request),
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
