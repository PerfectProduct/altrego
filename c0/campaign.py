"""Small C0 journal and bounded CLI stage runner. No automatic owner approvals."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import time


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_events(path: Path) -> list[dict]:
    rows = []
    previous = None
    for line in path.read_text().splitlines() if path.exists() else []:
        row = json.loads(line)
        digest = row.pop("event_sha256")
        if row["sequence"] != len(rows) or row["previous_sha256"] != previous:
            raise ValueError("Journal sequence or chain mismatch")
        if hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest() != digest:
            raise ValueError("Journal event hash mismatch")
        row["event_sha256"] = digest
        rows.append(row)
        previous = digest
    return rows


def append_event(path: Path, event: dict) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        rows = read_events(path)
        previous = rows[-1]["event_sha256"] if rows else None
        record = {"sequence": len(rows), "at": datetime.now(timezone.utc).isoformat(),
                  "previous_sha256": previous, **event}
        record["event_sha256"] = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return record


def verify_manifest(path: Path) -> dict:
    seal = path.with_suffix(path.suffix + ".sha256")
    if not seal.is_file() or seal.read_text().strip() != sha(path):
        raise ValueError("Manifest seal missing or mismatched")
    manifest = json.loads(path.read_text())
    for item in manifest["frozen_files"]:
        candidate = Path(item["path"])
        if sha(candidate) != item["sha256"]:
            raise ValueError(f"Frozen file changed: {candidate}")
    return manifest


def stage(args: argparse.Namespace) -> int:
    manifest = verify_manifest(args.manifest)
    root = Path(manifest["evidence_root"])
    journal = root / "attempts.jsonl"
    attempt = next(x for x in manifest["attempts"] if x["id"] == args.attempt)
    workspace = Path(attempt["workspace"])
    client = Path(attempt["client"])
    events = read_events(journal)
    completed_stages = {(e.get("attempt"), e.get("stage")) for e in events if e.get("event") == "stage_finished"}
    if any((e.get("attempt"), e.get("stage")) not in completed_stages
           for e in events if e.get("event") == "stage_started"):
        raise ValueError("Unfinished stage exists; recover its actual process/evidence before continuing")
    prior = manifest["attempts"][:manifest["attempts"].index(attempt)]
    finished = {e.get("attempt") for e in events if e.get("event") == "attempt_finished"}
    if any(item["id"] not in finished for item in prior):
        raise ValueError("Earlier attempt in frozen order is unfinished")
    if args.attempt in finished:
        raise ValueError("Attempt already finished; measured retries are forbidden")
    stages = [e for e in events if e.get("event") == "stage_started" and e.get("attempt") == args.attempt]
    if len(stages) >= manifest["max_stages_per_attempt"]:
        raise ValueError("Stage limit reached")
    if stages and not args.resume:
        raise ValueError("Continuing an attempt requires its existing builder context")
    if not stages and attempt.get("initial_prompt") and sha(args.prompt) != sha(Path(attempt["initial_prompt"])):
        raise ValueError("Initial prompt differs from frozen handoff")
    if args.resume and not any(e.get("attempt") == args.attempt and e.get("thread_id") == args.resume for e in events):
        raise ValueError("Resume thread does not belong to this attempt")
    spent = sum(e.get("elapsed_seconds", 0) for e in events
                if e.get("attempt") == args.attempt and e.get("event") == "stage_finished")
    remaining = manifest["builder_active_seconds"] - spent
    if remaining <= 0:
        raise ValueError("Attempt active-runtime budget exhausted")
    if args.phase == "execution" and attempt["arm"] == "altrego":
        required = {"brief_signed", "documentation_signed", "plan_approved", "execution_authorized"}
        observed = {e.get("event") for e in events if e.get("attempt") == args.attempt}
        if not required <= observed:
            raise ValueError(f"Missing actual Altrego gates: {sorted(required - observed)}")
    if args.phase == "planning" and attempt["arm"] == "altrego":
        if not any(e.get("attempt") == args.attempt and e.get("event") == "brief_signed" for e in events):
            raise ValueError("Missing actual owner brief signature")
    output = root / args.attempt / args.stage
    output.mkdir(parents=True, exist_ok=False)
    prompt = args.prompt.read_bytes()
    (output / "prompt.txt").write_bytes(prompt)
    # CLI 0.160.0 hides explicit read mounts beneath denied /tmp. Its write
    # entries materialize the mounts; an outer Linux read-only mount enforces
    # planning and runtime immutability independently of that CLI behavior.
    read_or_write = "write"
    config = Path(attempt["base_config"]).read_text()
    config = config.replace('[permissions.c0.filesystem]\n',
                            f'[permissions.c0.filesystem]\n{json.dumps(str(workspace))} = "{read_or_write}"\n')
    (client / "config.toml").write_text(config)
    (output / "effective-config.toml").write_text(config)
    command = ["/usr/local/bin/codex", "exec", "--strict-config", "--json", "--color", "never",
               "--skip-git-repo-check", "-o", str(output / "final.txt")]
    if args.resume:
        command += ["resume", args.resume]
    command += ["-"]
    command = ["bwrap", "--die-with-parent", "--new-session", "--unshare-pid",
               "--unshare-ipc", "--unshare-uts", "--cap-drop", "ALL", "--ro-bind", "/", "/",
               "--dev-bind", "/dev", "/dev", "--proc", "/proc",
               "--tmpfs", "/tmp", "--ro-bind", "/tmp/c0-runtime", "/tmp/c0-runtime",
               "--bind", str(client), str(client),
               "--bind", str(output), str(output),
               "--ro-bind" if args.phase == "planning" else "--bind",
               str(workspace), str(workspace), "--chdir", str(workspace), "--"] + command
    boundary = command.index("--")
    for name in ("README.md", "runtime-lock.txt"):
        immutable_input = workspace / name
        if immutable_input.is_file():
            command[boundary:boundary] = ["--ro-bind", str(immutable_input), str(immutable_input)]
            boundary += 3
    env = {"PATH": "/tmp/c0-runtime/bin:/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8",
           "CODEX_HOME": str(client), "XDG_RUNTIME_DIR": str(client / "runtime")}
    (client / "runtime").mkdir(mode=0o700, exist_ok=True)
    append_event(journal, {"event": "stage_started", "attempt": args.attempt, "stage": args.stage,
                          "phase": args.phase, "manifest_sha256": sha(args.manifest),
                          "prompt_sha256": sha(output / "prompt.txt"),
                          "config_sha256": sha(output / "effective-config.toml"),
                          "remaining_seconds": remaining, "evidence": str(output)})
    start = time.monotonic()
    def child_limits():
        os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    with (output / "events.jsonl").open("wb") as stdout, (output / "stderr.txt").open("wb") as stderr:
        proc = subprocess.Popen(command, cwd=workspace, env=env, stdin=subprocess.PIPE,
                                stdout=stdout, stderr=stderr, start_new_session=True,
                                preexec_fn=child_limits)
        timed_out = False
        try:
            proc.communicate(prompt, timeout=remaining)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
    usage = []
    thread = None
    for line in (output / "events.jsonl").read_text().splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("type") == "thread.started":
            thread = record["thread_id"]
        if record.get("type") == "turn.completed":
            usage.append(record.get("usage"))
    # CLI 0.160.0 reports cumulative context totals even after exec resume.
    # Preserve those values; never sum them across stages as if they were deltas.
    previous_usage = next((e["usage"][-1] for e in reversed(events)
                           if e.get("attempt") == args.attempt and e.get("usage")), {})
    stage_usage = ({k: value - previous_usage.get(k, 0) for k, value in usage[-1].items()}
                   if usage and usage[-1] else None)
    if (client / "sessions").exists():
        shutil.copytree(client / "sessions", output / "sessions")
    result = append_event(journal, {"event": "stage_finished", "attempt": args.attempt,
                                   "stage": args.stage, "phase": args.phase,
                                   "elapsed_seconds": round(time.monotonic() - start, 3),
                                   "exit_code": proc.returncode, "timed_out": timed_out,
                                   "thread_id": thread, "usage": usage,
                                   "usage_semantics": "cumulative_thread_totals",
                                   "stage_usage": stage_usage,
                                   "usage_delta_span": "since_last_reported_total",
                                   "events_sha256": sha(output / "events.jsonl")})
    print(json.dumps(result, ensure_ascii=False))
    return proc.returncode or int(timed_out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--phase", choices=("planning", "execution"), required=True)
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--resume")
    raise SystemExit(stage(parser.parse_args()))
