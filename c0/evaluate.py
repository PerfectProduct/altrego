"""C0-only Linux evaluator: separate service/test filesystems, shared private loopback.

Run with the reviewed Python runtime and oracle paths explicitly supplied.
This adapts execution, not the upstream test assertions. No upstream module is
imported here. The synthetic smoke must pass before use on campaign artifacts.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import resource
import signal
import socket
import subprocess
import sys
import time
import xml.etree.ElementTree as ET


def mounts(hosts: str = "/etc/hosts") -> list[str]:
    return [
        "bwrap", "--die-with-parent", "--new-session", "--unshare-pid",
        "--unshare-ipc", "--unshare-uts", "--cap-drop", "ALL",
        "--ro-bind", "/usr", "/usr", "--ro-bind", "/lib", "/lib",
        "--ro-bind", "/lib64", "/lib64", "--symlink", "usr/bin", "/bin",
        "--ro-bind", hosts, "/etc/hosts",
        "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
        "--symlink", "/runtime", "/tmp/c0-runtime",
        "--clearenv", "--setenv", "LANG", "C.UTF-8",
        "--setenv", "PATH", "/runtime/bin:/usr/bin:/bin",
    ]


def stop(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)


def limits() -> None:
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])


def inside(args: argparse.Namespace) -> int:
    """Trusted supervisor in a private network namespace; children share only network."""
    service_cmd = mounts() + [
        "--ro-bind", "/runtime", "/runtime", "--bind", "/submission", "/app",
        "--chdir", "/app", "--", "/bin/bash", "./start.sh",
    ]
    # venv launchers reference their original prefix; use interpreter + PYTHONPATH.
    site = next(Path("/runtime/lib").glob("python*/site-packages"))
    env_args = ["--setenv", "PYTHONPATH", str(site)]
    service_cmd[service_cmd.index("--"):service_cmd.index("--")] = env_args
    started = time.monotonic()
    with open("/results/service.log", "wb") as log:
        service = subprocess.Popen(service_cmd, stdout=log, stderr=subprocess.STDOUT, preexec_fn=limits)
        ready = False
        try:
            while time.monotonic() - started < args.startup_timeout:
                if service.poll() is not None:
                    break
                try:
                    with socket.create_connection(("127.0.0.1", args.port), timeout=.2):
                        ready = True
                        break
                except OSError:
                    time.sleep(.1)
            result = {"port_open": ready, "service_exit_before_tests": service.poll()}
            test_cmd = mounts() + [
                "--ro-bind", "/runtime", "/runtime",
                "--ro-bind", "/oracle", "/oracle",
                "--bind", "/results", "/results", "--chdir", "/oracle",
                "--setenv", "PYTHONPATH", str(site),
                "--setenv", "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1",
                "--", "/runtime/bin/python", "-m", "pytest", "/oracle",
                "--confcutdir=/oracle", "--import-mode=importlib", "-p", "no:cacheprovider",
                "--junitxml=/results/tests.xml", "-q", "--tb=short",
            ]
            if args.oracle_kind == "rbac":
                boundary = test_cmd.index("--")
                test_cmd = test_cmd[:boundary] + [
                    "--ro-bind", "/rbac_adapter.py", "/rbac_adapter.py",
                    "--", "/runtime/bin/python", "/rbac_adapter.py",
                ]
            with open("/results/tests.log", "wb") as output:
                test = subprocess.Popen(test_cmd, stdout=output, stderr=subprocess.STDOUT, preexec_fn=limits)
                try:
                    result["test_exit"] = test.wait(timeout=args.test_timeout)
                    result["test_timeout"] = False
                except subprocess.TimeoutExpired:
                    stop(test)
                    result.update(test_exit=test.returncode, test_timeout=True)
            result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        finally:
            stop(service)
    Path("/results/supervisor.json").write_text(json.dumps(result, indent=2) + "\n")
    return 0


def copy_submission(source: Path, dest: Path) -> None:
    for path in source.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"Submission symlink requires review: {path.relative_to(source)}")
        if not (path.is_file() or path.is_dir()):
            raise ValueError(f"Submission special file requires review: {path.relative_to(source)}")
    shutil.copytree(source, dest, ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inside", action="store_true")
    parser.add_argument("--submission", type=Path)
    parser.add_argument("--oracle", type=Path)
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--startup-timeout", type=int, default=15)
    parser.add_argument("--test-timeout", type=int, default=300)
    parser.add_argument("--oracle-kind", choices=("pytest", "rbac"), default="pytest")
    parser.add_argument("--expected-tests", type=int, required=True)
    args = parser.parse_args()
    if args.inside:
        return inside(args)
    for key in ("submission", "oracle", "runtime", "output"):
        if getattr(args, key) is None:
            parser.error(f"--{key} is required")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)  # never overwrite an evaluation
    copy_submission(args.submission.resolve(), output / "submission")
    (output / "results").mkdir()
    if not (output / "submission/start.sh").is_file():
        (output / "results/result.json").write_text(json.dumps({
            "status": "submission_missing_start_script", "all_tests_passed": False,
            "tests": None, "port_open": False,
            "expected_tests": args.expected_tests,
        }, indent=2) + "\n")
        return 0
    command = mounts(str(Path(__file__).with_name("localhosts").resolve())) + [
        "--unshare-net", "--unshare-user",
        "--ro-bind", str(args.runtime.resolve()), "/runtime",
        "--ro-bind", str(args.oracle.resolve()), "/oracle",
        "--bind", str(output / "submission"), "/submission",
        "--bind", str(output / "results"), "/results",
        "--ro-bind", str(Path(__file__).resolve()), "/evaluate.py",
        "--ro-bind", str(Path(__file__).with_name("rbac_adapter.py").resolve()), "/rbac_adapter.py",
        "--", "/usr/bin/python3", "/evaluate.py", "--inside", "--port", str(args.port),
        "--startup-timeout", str(args.startup_timeout), "--test-timeout", str(args.test_timeout),
        "--oracle-kind", args.oracle_kind,
        "--expected-tests", str(args.expected_tests),
    ]
    with (output / "supervisor.log").open("wb") as log:
        proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = proc.wait(timeout=args.startup_timeout + args.test_timeout + 30)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            code = proc.wait()
    result = {"supervisor_exit": code, "status": "infrastructure_failure", "tests": None,
              "all_tests_passed": False, "expected_tests": args.expected_tests}
    state = output / "results/supervisor.json"
    if code == 0 and state.is_file():
        result.update(json.loads(state.read_text()))
        result["status"] = "evaluated"
        report = output / "results/tests.xml"
        if report.is_file():
            cases = ET.parse(report).getroot().findall(".//testcase")
            counts = {"collected_in_report": len(cases), "passed": 0, "failed": 0,
                      "errors": 0, "skipped": 0}
            for case in cases:
                outcome = ("errors" if case.find("error") is not None else
                           "failed" if case.find("failure") is not None else
                           "skipped" if case.find("skipped") is not None else "passed")
                counts[outcome] += 1
            result["tests"] = counts
            result["all_tests_passed"] = len(cases) == args.expected_tests > 0 and counts["passed"] == len(cases) and result["test_exit"] == 0 and not result["test_timeout"]
        elif args.oracle_kind == "rbac" and (output / "results/rbac.json").is_file():
            result["tests"] = json.loads((output / "results/rbac.json").read_text())["tests"]
            result["all_tests_passed"] = result["tests"]["passed"] == args.expected_tests == 9 and result["test_exit"] == 0 and not result["test_timeout"]
    (output / "results/result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    return 0 if result["status"] == "evaluated" else 2


if __name__ == "__main__":
    sys.exit(main())
