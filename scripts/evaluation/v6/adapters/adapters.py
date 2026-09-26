#!/usr/bin/env python3
"""Host adapters for the v6 evaluation lab (contributor-only).

An adapter wraps one host/model stratum: probe (availability + version, no
secrets), launch (a scrubbed subprocess, reusing the lab driver's
environment rules), and the documented usage-counter source that the canary
verifies at execution time. The fake adapter generates synthetic usage so
the whole metering path is validated without paying a provider.

Python 3.9+ stdlib only. Probes never read, print, or transmit credentials.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lab  # noqa: E402


def _probe_binary(argv, version_arg="--version"):
    try:
        proc = subprocess.run(argv + [version_arg], capture_output=True, text=True, timeout=30)
        if proc.returncode == 0:
            return {"available": True, "version": proc.stdout.strip().splitlines()[0][:80]}
        return {"available": False, "reason": f"exit {proc.returncode}"}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "reason": str(exc)[:120]}


ADAPTERS = {
    "fake": {
        "description": "deterministic synthetic actor; usage counters are generated, never real",
        "counter_source": "synthetic generator (validated against expected totals)",
        "probe": lambda: {"available": True, "version": "synthetic-1"},
    },
    "claude": {
        "description": "Claude Code CLI headless launch (claude -p ... --output-format json)",
        "counter_source": "to verify at canary: the JSON response usage block "
                          "(input_tokens / output_tokens / cache_* per the CLI's documented schema)",
        "probe": lambda: _probe_binary(["claude"]),
    },
    "codex": {
        "description": "Codex CLI headless launch (codex exec)",
        "counter_source": "to verify at canary: the session log's token_usage block "
                          "(discovered at execution; absent logs are recorded unknown)",
        "probe": lambda: _probe_binary(["codex"]),
    },
}


def probe(name):
    if name not in ADAPTERS:
        raise KeyError(f"unknown adapter: {name!r}")
    record = {"adapter": name, "description": ADAPTERS[name]["description"],
              "counter_source": ADAPTERS[name]["counter_source"]}
    record.update(ADAPTERS[name]["probe"]())
    return record


def launch(adapter_name, actor_command, workspace, timeout_s=900, extra_args=None):
    """Launch one actor process in a scrubbed environment (lab rules).

    Returns (exit_code, duration_s). The actor command is a shell command
    string executed with cwd=workspace; stdout/stderr are the caller's
    handles' problem (captured by the lab driver in real campaigns).
    """
    if adapter_name not in ADAPTERS:
        raise KeyError(f"unknown adapter: {adapter_name!r}")
    argv = actor_command if isinstance(actor_command, list) else [actor_command]
    if extra_args:
        argv = argv + list(extra_args)
    scratch_home = workspace / ".adapter-home"
    scratch_home.mkdir(exist_ok=True)
    env = lab.scrubbed_env(workspace, scratch_home)
    import time
    started = time.time()
    proc = subprocess.run(argv, cwd=str(workspace), env=env, capture_output=True,
                          text=True, timeout=timeout_s)
    return proc.returncode, round(time.time() - started, 3), proc.stdout[-2000:]


def synthetic_usage(seed_value=1):
    """Deterministic synthetic counters for metering validation (never real)."""
    return {
        "input_tokens": 1000 * seed_value,
        "output_tokens": 200 * seed_value,
        "cached_input_tokens": 50 * seed_value,
        "reasoning_tokens": 30 * seed_value,
    }


def canary(adapter_name, timeout_s=120):
    """One bounded real probe of counter availability.

    For `claude`: a single trivial headless prompt, JSON output, counters read
    from the documented usage block. For `codex`: a trivial exec run, counters
    from the session log if present. NEVER a paid campaign — one tiny call,
    bounded by the timeout, whose only purpose is discovering whether and
    where counters are exposed. Credentials stay in the environment; nothing
    secret is written to the report.
    """
    probe_result = probe(adapter_name)
    report = {"adapter": adapter_name, "probe": probe_result,
              "canary": "not attempted", "counters_available": False,
              "counter_fields_seen": [], "raw_usage_excerpt": None}
    if not probe_result.get("available"):
        report["canary"] = f"skipped: probe unavailable ({probe_result.get('reason')})"
        return report
    if adapter_name == "fake":
        report["canary"] = "synthetic: counters generated, totals reconcile by construction"
        report["counters_available"] = True
        report["counter_fields_seen"] = list(__import__("telemetry").COUNTER_FIELDS)
        return report
    if adapter_name == "claude":
        try:
            proc = subprocess.run(
                ["claude", "-p", "Reply with exactly: ok", "--output-format", "json"],
                capture_output=True, text=True, timeout=timeout_s)
            if proc.returncode == 0:
                try:
                    payload = json.loads(proc.stdout)
                    usage = payload.get("usage") or (payload.get("result") or {})
                    fields = {k: usage[k] for k in ("input_tokens", "output_tokens",
                                                    "cache_read_input_tokens",
                                                    "cache_creation_input_tokens") if k in usage}
                    report.update({"canary": "ok", "counters_available": bool(fields),
                                   "counter_fields_seen": sorted(fields),
                                   "raw_usage_excerpt": fields})
                except ValueError:
                    report["canary"] = "run ok but output was not JSON; counter source needs re-discovery"
            else:
                report["canary"] = f"exit {proc.returncode}: {(proc.stderr or proc.stdout)[-200:]}"
        except (OSError, subprocess.TimeoutExpired) as exc:
            report["canary"] = f"failed: {str(exc)[:160]}"
        return report
    if adapter_name == "codex":
        try:
            started = __import__("time").time()
            proc = subprocess.run(
                ["codex", "exec", "--skip-git-repo-check",
                 "--dangerously-bypass-approvals-and-sandbox", "Reply with exactly: ok"],
                capture_output=True, text=True, timeout=timeout_s,
                stdin=__import__("subprocess").DEVNULL)
            from codex_usage import default_sessions_dir, usage_since
            usage = usage_since(default_sessions_dir(), started)
            report["canary"] = f"exit {proc.returncode}; rollouts: {usage['rollout_count']}"
            report["counters_available"] = bool(usage["counters"]["output_tokens"])
            report["counter_fields_seen"] = sorted(usage["counters"])
            report["raw_usage_excerpt"] = usage["counters"]
        except (OSError, subprocess.TimeoutExpired) as exc:
            report["canary"] = f"failed: {str(exc)[:160]}"
        return report
    report["canary"] = "no canary defined"
    return report
