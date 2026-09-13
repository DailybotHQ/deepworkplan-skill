#!/usr/bin/env python3
"""Export one acceptance run as sanitized, committable evidence.

Raw prompts, absolute paths and full logs stay in the plan folder, outside this
repository. What ships is the run's identity, its scored oracles, and the
checkable facts a reader needs to reproduce or challenge the result.

Usage:
    python3 tests/reliability/oracles/export-evidence.py <run-dir> <out-dir>
"""
import argparse
import json
import pathlib
import re
import subprocess

# Absolute paths that would leak this machine's layout. The run root and the
# pack root are replaced by stable labels; anything else absolute is rejected
# rather than silently shipped.
def sanitize(value, replacements):
    if isinstance(value, str):
        for needle, label in replacements:
            value = value.replace(needle, label)
        return value
    if isinstance(value, list):
        return [sanitize(v, replacements) for v in value]
    if isinstance(value, dict):
        return {k: sanitize(v, replacements) for k, v in value.items()}
    return value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("out_dir")
    a = ap.parse_args()
    run = pathlib.Path(a.run_dir).resolve()
    out = pathlib.Path(a.out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    meta = json.loads((run / "META.json").read_text())
    score = json.loads((run / "SCORE.json").read_text())
    report = json.loads((run / "ACCEPTANCE_REPORT.json").read_text())

    # Longest first: the pack path sits under the repo root, so replacing the
    # root first would leave a half-substituted pack path behind.
    pack_path = meta.get("pack_path") or "\0"
    repo_root = str(pathlib.Path(pack_path).parents[1]) if pack_path != "\0" else "\0"
    replacements = sorted(
        [(str(run), "<run>"), (pack_path, "<pack>"),
         (str(run.parents[2]), "<plan>"), (repo_root, "<repo>")],
        key=lambda pair: len(pair[0]), reverse=True)
    repo = run / "repo"
    log = subprocess.run(["git", "log", "--format=%h %s"], cwd=repo,
                         capture_output=True, text=True)
    plans = sorted((repo / ".dwp/plans").glob("PLAN_*"))
    plan = plans[0] if plans else None

    payload = {
        "run_id": meta.get("run_id"),
        "flow": meta.get("flow"),
        "pack_revision": meta.get("pack_revision"),
        "host": meta.get("host"),
        "entry_path": meta.get("entry_path"),
        "cross_vendor": meta.get("cross_vendor", False),
        "interrupted": meta.get("interrupted", False),
        "round": meta.get("round"),
        "tree_state": meta.get("tree_state", "clean"),
        "pack_sha256": meta.get("pack_sha256"),
        "round_note": meta.get("round_note"),
        "plan_name": plan.name if plan else None,
        "verdict": score.get("verdict"),
        "oracles": score.get("results"),
        "commits": log.stdout.strip().split("\n") if log.returncode == 0 else [],
        "pack_files_read": sanitize(report.get("pack_files_read", []), replacements),
        "pack_bytes_read": sum(f.get("bytes", 0) for f in report.get("pack_files_read", [])),
        "commands_run": len(report.get("commands", [])),
        "questions_asked": sanitize(report.get("questions_asked", []), replacements),
        "stopped_early": report.get("stopped_early"),
        "notes": sanitize(report.get("notes", ""), replacements),
    }
    for extra in ("interruption_boundary", "work_not_repeated"):
        if extra in report:
            payload[extra] = sanitize(report[extra], replacements)

    blob = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    leaked = re.findall(r"(?<![\w<])/(?:app|home|Users|root|tmp)/[\w./-]+", blob)
    if leaked:
        raise SystemExit("refusing to export: absolute paths survive sanitization: "
                         + ", ".join(sorted(set(leaked))[:5]))
    target = out / f"{meta['run_id']}.json"
    target.write_text(blob)
    print(f"exported {target} ({payload['verdict']})")


if __name__ == "__main__":
    main()
