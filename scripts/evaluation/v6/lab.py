#!/usr/bin/env python3
"""DWP v6 evaluation lab driver (contributor-only; never shipped in the pack).

Implements the interface proposed in the lab blueprint and owned by
PLAN_v6_verified_autonomy Task 4:

    lab.py self-test
    lab.py validate  --config <campaign.json>
    lab.py prepare   --family <name> [--dry-run] [--config <campaign.json>]
    lab.py run       --config <campaign.json> --output <dir> [--resume <attempt-id>]
    lab.py score     --config <campaign.json> --output <dir>
    lab.py analyze   --config <campaign.json> --output <dir>

Isolation posture, stated where it can be seen: the driver provides
WORKSPACE-level isolation (fresh disposable workspaces, a scrubbed minimal
environment with a scratch HOME, pinned TZ/locale, unique attempt IDs) and
proves it with contamination canaries. It cannot provide host-enforced
isolation (containers, separate OS users, an enforced custodian boundary) on
a host that lacks those primitives; the posture is written into every
attempt's ISOLATION.json and campaigns that require enforced separation are
refused rather than run at a weaker level. Fake actors (mode "fake") exercise
the full orchestration path without any provider call.

The driver itself never opens a network connection and never calls a paid
API: actors are external processes launched from the campaign config, and a
campaign marked "paid" is refused unless the preregistered resource envelope
is set.

Python 3.9+ stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

SCHEMA = "deepworkplan-skill/evaluation/v6/campaign/1"
KNOWN_ARMS = ("A", "B", "C")
DESIGN_PATH = Path("tests/evaluation/v6/protocol/design.json")
DEFAULT_PACK_PATTERN_MSG = (
    "pack references must point at an immutable snapshot directory named "
    "<tag>-<digest> under tmp/repositories/dwp-v6-lab/packs/ — never at a live checkout, a mutable ref, or a symlink"
)


def die(message: str) -> "None":
    print(f"REFUSED: {message}", file=sys.stderr)
    raise SystemExit(1)


def repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "skills" / "deepworkplan" / "SKILL.md").is_file() and (candidate / "tests").is_dir():
            return candidate
    raise SystemExit("cannot locate the repository root")


def default_lab_root() -> Path:
    return repo_root() / "tmp" / "repositories" / "dwp-v6-lab"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_hashes(root: Path) -> dict:
    """Sorted file->sha256 map of a tree, excluding nothing (workspaces are small)."""
    out = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            out[path.relative_to(root).as_posix()] = "symlink:" + os.readlink(path)
        elif path.is_file():
            out[path.relative_to(root).as_posix()] = sha256_path(path)
    return out


def is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def has_escape(path: Path) -> bool:
    return ".." in path.parts or path.is_absolute()


def safe_copytree(src: Path, dst: Path) -> None:
    """Copy a tree, refusing symlinks anywhere in it (no traversal out of the seed)."""
    for path in src.rglob("*"):
        if path.is_symlink():
            die(f"seed contains a symlink ({path}) — symlink traversal is refused")
    shutil.copytree(src, dst, symlinks=False)


def design_envelope(design_path: Path) -> dict:
    if not design_path.is_file():
        die(f"preregistered design not found at {design_path}")
    design = load_json(design_path)
    return design.get("resource_envelope", {})


# ---------------------------------------------------------------- validation

def validate_campaign(cfg: dict, lab_root: Path, design_path: Path) -> list:
    errors = []

    def err(message):
        errors.append(message)

    for key in ("schema", "name", "paid", "arms", "seed", "tasks", "strata", "repeats", "oracles"):
        if key not in cfg:
            err(f"campaign config missing required key: {key}")
    if errors:
        return errors
    if cfg["schema"] != SCHEMA:
        err(f"unexpected schema id: {cfg['schema']!r} (expected {SCHEMA!r})")
    if not cfg["name"] or not cfg["name"].replace("-", "").replace("_", "").isalnum():
        err(f"campaign name must be a simple slug: {cfg['name']!r}")

    arms = cfg["arms"]
    if not arms or any(a not in KNOWN_ARMS for a in arms):
        err(f"arms must be a non-empty subset of {KNOWN_ARMS}")

    for arm, spec in arms.items():
        pack = (spec or {}).get("pack")
        if pack is None:
            if arm == "B":
                err("arm B (latest-v5) must reference a frozen pack snapshot")
            continue
        path = (lab_root / pack) if not Path(pack).is_absolute() else Path(pack)
        if has_escape(Path(pack)):
            err(f"arm {arm} pack path escapes the lab root: {pack}")
            continue
        if not path.exists():
            err(f"arm {arm} pack snapshot does not exist: {pack} — export it first (see tests/evaluation/v6/baselines/)")
            continue
        if path.is_symlink() or not path.is_dir():
            err(f"arm {arm} pack reference must be a real directory, not a symlink: {pack} ({DEFAULT_PACK_PATTERN_MSG})")
            continue
        name = path.name
        if "-" not in name or not name.rsplit("-", 1)[1].isalnum() or len(name.rsplit("-", 1)[1]) < 12:
            err(f"arm {arm} pack directory name must be <tag>-<digest>: {name} ({DEFAULT_PACK_PATTERN_MSG})")

    seed = cfg["seed"]
    seed_path = repo_root() / seed.get("path", "")
    if has_escape(Path(seed.get("path", ""))):
        err("seed path escapes the repository")
    elif not seed_path.is_dir():
        err(f"seed fixture directory not found: {seed.get('path')}")
    if not cfg["tasks"]:
        err("campaign has no tasks")
    for i, task in enumerate(cfg["tasks"]):
        for field in ("id", "prompt"):
            if not task.get(field):
                err(f"tasks[{i}] missing {field}")
    if not cfg["strata"]:
        err("campaign has no strata")
    for i, stratum in enumerate(cfg["strata"]):
        launch = stratum.get("launch", {})
        if launch.get("mode") not in ("fake", "exec"):
            err(f"strata[{i}] launch.mode must be 'fake' or 'exec'")
        if launch.get("mode") == "fake" and not launch.get("command"):
            err(f"strata[{i}] fake launch requires command (a fixture actor script)")
        if launch.get("mode") == "exec" and not launch.get("argv"):
            err(f"strata[{i}] exec launch requires argv")
        if not stratum.get("name"):
            err(f"strata[{i}] missing name")
    if not isinstance(cfg["repeats"], int) or cfg["repeats"] < 1:
        err("repeats must be a positive integer")
    for i, oracle in enumerate(cfg["oracles"]):
        if oracle.get("kind") not in ("file_contains", "file_exists", "exit_zero_file"):
            err(f"oracles[{i}].kind must be one of file_contains | file_exists | exit_zero_file")
        if not oracle.get("id"):
            err(f"oracles[{i}] missing id")

    if cfg.get("paid"):
        envelope = design_envelope(design_path)
        if envelope.get("status") != "SET" or envelope.get("per_run_cap") is None or envelope.get("total_cap") is None:
            err(
                "campaign is marked paid but the preregistered resource envelope is UNSET "
                "(design.json resource_envelope) — launch refused; approve RESOURCE_PROPOSAL.md caps first"
            )
    if cfg.get("requires_enforced_isolation"):
        posture = isolation_posture(lab_root)
        if not posture["host_enforced_isolation"]:
            err(
                "campaign requires enforced host isolation (custodian sealing) but this host cannot "
                "provide it — confirmation stays blocked; run it as exploratory without the flag"
            )
    return errors


def cmd_validate_family(lab_root: Path, family: str, execute_checks: bool) -> int:
    """Validate a prepared fixture family: static pinned-hash drift check plus,
    with --execute-checks, a disposable clean install/build/check run.

    Zero-check defense: a check command that reports zero checks, produces no
    output, or exits nonzero is a failure, never a pass."""
    staging = lab_root / "seeds" / family
    manifest_path = staging / "manifest.json"
    seed = staging / "seed"
    if not manifest_path.is_file() or not seed.is_dir():
        die(f"family {family!r} is not prepared: run prepare --family {family} first "
            f"(expected {manifest_path})")
    manifest = load_json(manifest_path)
    pinned = manifest.get("files") or tree_hashes(seed)
    current = tree_hashes(seed)
    if pinned != current:
        die("staged seed drifted from its pinned hashes — re-prepare the family; "
            "a mutable fixture is refused")
    commands = manifest.get("commands")
    if not commands:
        seed_manifest = seed / "manifest.json"
        if seed_manifest.is_file():
            # The fixture's own manifest travels with the seed; the pinned
            # manifest carries hashes, the fixture manifest carries commands.
            commands = load_json(seed_manifest).get("commands")
    commands = commands or {}
    for key in ("install", "build", "check"):
        if not commands.get(key):
            die(f"family manifest is missing commands.{key}")
    result = {"family": family, "static": "ok", "pinned_files": len(pinned),
              "executed_checks": False}
    if not execute_checks:
        (staging / "validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"OK family {family!r}: staged seed matches {len(pinned)} pinned files; "
              f"install/build/check declared. Pass --execute-checks to run them.")
        return 0

    with tempfile.TemporaryDirectory(prefix=f"dwp-v6-family-{family}-") as td:
        work = Path(td) / "seed"
        safe_copytree(seed, work)
        outputs = {}
        for key in ("install", "build", "check"):
            try:
                proc = subprocess.run(commands[key], shell=True, cwd=str(work),
                                      capture_output=True, text=True, timeout=1800)
            except subprocess.TimeoutExpired:
                result.update({"executed_checks": True, "failed_at": key,
                               "outputs": outputs, "timeout": True})
                (staging / "validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
                print(f"FAIL family {family!r}: {key} timed out", file=sys.stderr)
                return 1
            outputs[key] = {"exit_code": proc.returncode,
                            "output": (proc.stdout + proc.stderr)[-4000:]}
            if proc.returncode != 0:
                result.update({"executed_checks": True, "failed_at": key, "outputs": outputs})
                (staging / "validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
                print(f"FAIL family {family!r}: {key} exited {proc.returncode}", file=sys.stderr)
                print(outputs[key]["output"][-2000:], file=sys.stderr)
                return 1
        check_out = outputs["check"]["output"]
        counts = [int(n) for n in re.findall(r"(\d+) checks", check_out)]
        if (counts and max(counts) == 0) or not check_out.strip():
            result.update({"executed_checks": True, "failed_at": "check", "outputs": outputs})
            (staging / "validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            print(f"FAIL family {family!r}: the check produced no verifiable output "
                  f"(zero checks is not a pass)", file=sys.stderr)
            return 1
        result.update({"executed_checks": True,
                       "outputs": {k: v["exit_code"] for k, v in outputs.items()}})
        (staging / "validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        last = check_out.strip().splitlines()[-1][:160]
        print(f"OK family {family!r}: install/build/check all exit 0; check: {last}")
        return 0


def isolation_posture(lab_root: Path) -> dict:
    """Honest capability report: what this host can and cannot enforce."""
    return {
        "workspace_isolation": True,
        "memory_isolation": "scratch HOME + scrubbed environment (process-level)",
        "host_enforced_isolation": bool((lab_root / "custodian" / "ENFORCED").is_file()),
        "note": "host_enforced_isolation requires containers, a separate enforced OS user, or an equivalent access-controlled custodian store; the ENFORCED marker must only be written by such a mechanism, never by hand",
    }


# ------------------------------------------------------------------- prepare

def cmd_prepare(lab_root: Path, family: str, dry_run: bool, seed_rel: str) -> int:
    seed_path = repo_root() / seed_rel
    staging = lab_root / "seeds" / family
    print(f"family: {family}")
    print(f"seed source: {seed_path}")
    print(f"staging: {staging}")
    if staging.exists():
        die(f"staging collision: {staging} already exists — a rerun gets a new identity, it never overwrites")
    existing = [p.name for p in (lab_root / "seeds").glob(f"{family}*")] if (lab_root / "seeds").is_dir() else []
    if existing:
        print(f"note: related seed identities exist ({', '.join(existing)}); the new identity is separate")
    manifest = {
        "family": family,
        "seed_source": str(seed_path.relative_to(repo_root())) if is_within(seed_path, repo_root()) else str(seed_path),
        "files": tree_hashes(seed_path) if seed_path.is_dir() else {},
        "pinned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    print(f"would pin {len(manifest['files'])} files with hashes above (dry-run: nothing written)" if dry_run
          else f"pinning {len(manifest['files'])} files")
    if dry_run:
        for name, digest in sorted(manifest["files"].items()):
            print(f"  {digest[:12]}  {name}")
        return 0
    staging.mkdir(parents=True, exist_ok=True)
    safe_copytree(seed_path, staging / "seed")
    (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"prepared {staging} (manifest.json with pinned hashes)")
    return 0


# ----------------------------------------------------------------------- run

def scrubbed_env(workspace: Path, scratch_home: Path) -> dict:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(scratch_home),
        "TMPDIR": str(workspace / ".scratch"),
        "TZ": "UTC",
        "LC_ALL": "C",
        "LANG": "C",
    }
    return env


def run_cell(cell: dict, cfg: dict, attempt_dir: Path, lab_root: Path, timeout_s: int) -> dict:
    """Set up one workspace, dispatch one actor, verify canaries; record everything."""
    workspace = attempt_dir / "workspaces" / cell["cell_id"]
    workspace.parent.mkdir(parents=True, exist_ok=True)
    seed_staging = lab_root / "seeds" / cfg["seed"]["family"] / "seed"
    seed_src = seed_staging if seed_staging.is_dir() else repo_root() / cfg["seed"]["path"]
    safe_copytree(seed_src, workspace)
    (workspace / ".scratch").mkdir(exist_ok=True)
    # Materialize the task prompt: the actor's contract is the workspace
    # itself plus this file — nothing else (no plan, no oracles, no labels).
    (workspace / "TASK.md").write_text(cell["task"]["prompt"] + "\n", encoding="utf-8")
    initial = tree_hashes(workspace)
    # Host hazard: a package manifest anywhere above the workspace can make
    # package managers resolve an unrelated workspace root (observed with pnpm
    # under /app). Recorded per cell; the real mitigation is host-level.
    ancestor_workspace_risk = any(
        (ancestor / marker).is_file()
        for ancestor in list(workspace.parents)[:12]
        for marker in ("package.json", "pnpm-workspace.yaml")
    )

    # Actor-invisible items live OUTSIDE the workspace, inside the attempt.
    hidden = attempt_dir / "actor_invisible"
    hidden.mkdir(exist_ok=True)
    canary = hidden / "CUSTODIAN_CANARY.secret"
    canary_token = uuid.uuid4().hex
    canary.write_text(canary_token + "\n", encoding="utf-8")

    scratch_home = attempt_dir / "homes" / cell["cell_id"]
    scratch_home.mkdir(parents=True, exist_ok=True)
    env = scrubbed_env(workspace, scratch_home)

    launch = cell["stratum"]["launch"]
    if launch["mode"] == "fake":
        argv = [sys.executable, str((repo_root() / launch["command"]).resolve()),
                "--workspace", str(workspace), "--task", cell["task"]["id"]]
        if launch.get("actor_arg"):
            argv.append(launch["actor_arg"])
    else:
        argv = [str(a) for a in launch["argv"]] + ["--workspace", str(workspace), "--task", cell["task"]["id"]]

    pack = (cell["arm_spec"] or {}).get("pack")
    if pack:
        env["DWP_EVAL_PACK"] = str((lab_root / pack).resolve())

    log_path = attempt_dir / "logs" / f"{cell['cell_id']}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    status, exit_code, note = "error", None, ""
    started = time.time()
    with log_path.open("w", encoding="utf-8") as log:
        log.write("# argv: " + json.dumps(argv) + "\n")
        log.write("# env keys: " + ", ".join(sorted(env)) + "\n")
        log.write("# cwd: " + str(workspace) + "\n")
        log.flush()
        try:
            proc = subprocess.Popen(
                argv, cwd=str(workspace), env=env, stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            exit_code = proc.wait(timeout=timeout_s)
            status = "completed"
        except subprocess.TimeoutExpired:
            status = "timeout"
            note = f"killed after {timeout_s}s"
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
            exit_code = proc.returncode
        except OSError as exc:
            status = "error"
            note = str(exc)
            exit_code = None
    duration = round(time.time() - started, 3)

    content_intact = canary.read_text(encoding="utf-8") == canary_token + "\n"
    leaked = False
    for produced in workspace.rglob("*"):
        if produced.is_file() and canary_token in produced.read_text(encoding="utf-8", errors="replace"):
            leaked = True
            break
    canary_intact = content_intact and not leaked
    final = tree_hashes(workspace)
    record = {
        "cell_id": cell["cell_id"],
        "attempt": attempt_dir.name,
        "campaign": cfg["name"],
        "arm": cell["arm"],
        "task": cell["task"]["id"],
        "stratum": cell["stratum"]["name"],
        "repeat": cell["repeat"],
        "status": status,
        "exit_code": exit_code,
        "note": note,
        "duration_s": duration,
        "timeout_s": timeout_s,
        "initial_hashes": initial,
        "final_hashes": final,
        "produced_change": initial != final,
        "ancestor_workspace_risk": ancestor_workspace_risk,
        "canary_intact": canary_intact,
        "canary": "actor_invisible/CUSTODIAN_CANARY.secret",
        "env_keys": sorted(env),
        "log": str(log_path.relative_to(attempt_dir)),
        "workspace": str(workspace.relative_to(attempt_dir)),
    }
    if not canary_intact:
        record["status"] = "ineligible"
        record["note"] = (record["note"] + "; " if note else "") + "contamination canary violated — actor read or modified actor-invisible storage"
    return record


def campaign_cells(cfg: dict, arms: dict) -> list:
    cells = []
    for task in cfg["tasks"]:
        for stratum in cfg["strata"]:
            for repeat in range(cfg["repeats"]):
                for arm in sorted(arms):
                    cells.append({
                        "cell_id": f"{task['id']}-{stratum['name']}-r{repeat + 1}-{arm}",
                        "task": task, "stratum": stratum, "repeat": repeat + 1,
                        "arm": arm, "arm_spec": arms[arm],
                    })
    return cells


def cmd_run(cfg: dict, lab_root: Path, output_dir: Path, resume: str, timeout_s: int) -> int:
    inventory = output_dir / "attempts.jsonl"
    if resume:
        attempt_dir = output_dir / resume
        if not attempt_dir.is_dir():
            die(f"cannot resume: attempt {resume} not found under {output_dir}")
        attempt_id = resume
    else:
        if output_dir.exists() and any(output_dir.iterdir()):
            die(f"output collision: {output_dir} exists and is non-empty — a rerun gets a new attempt ID and never overwrites")
        attempt_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid.uuid4().hex[:8]
        attempt_dir = output_dir / attempt_id
        attempt_dir.mkdir(parents=True, exist_ok=True)
        posture = isolation_posture(lab_root)
        posture["attempt"] = attempt_id
        (attempt_dir / "ISOLATION.json").write_text(json.dumps(posture, indent=2) + "\n", encoding="utf-8")
        if cfg.get("requires_enforced_isolation") and not posture["host_enforced_isolation"]:
            die("campaign requires enforced host isolation; this host cannot provide it (see ISOLATION.json)")

    done_cells = set()
    if inventory.exists():
        for line in inventory.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                if record.get("status") in ("completed", "ineligible", "timeout"):
                    done_cells.add(record["cell_id"])

    cells = campaign_cells(cfg, cfg["arms"])
    inventory.parent.mkdir(parents=True, exist_ok=True)
    with inventory.open("a", encoding="utf-8") as inv:
        for cell in cells:
            if cell["cell_id"] in done_cells:
                print(f"skip (already recorded): {cell['cell_id']}")
                continue
            print(f"run: {cell['cell_id']}")
            record = run_cell(cell, cfg, attempt_dir, lab_root, timeout_s)
            inv.write(json.dumps(record) + "\n")
            inv.flush()
            print(f"  -> {record['status']} (exit={record['exit_code']}, canary_intact={record['canary_intact']})")
    print(f"attempt {attempt_id}: {len(cells)} cells; inventory {inventory}")
    return 0


# ---------------------------------------------------------------- score/analyze

def apply_oracles(cfg: dict, record: dict, attempt_dir: Path) -> dict:
    """Artifact-derived scoring: PASS needs evidence in the files, never narration.
    A missing artifact scores UNVERIFIED, which is a failure, never a pass."""
    results = {}
    workspace = attempt_dir / record["workspace"]
    for oracle in cfg["oracles"]:
        oid = oracle["id"]
        if record["status"] != "completed":
            results[oid] = ["FAIL", f"cell status is {record['status']}"]
            continue
        rel = oracle.get("path", "")
        target = workspace / rel
        if oracle["kind"] == "file_contains":
            if not target.is_file():
                results[oid] = ["UNVERIFIED", f"artifact missing: {rel}"]
            elif oracle["expect"] in target.read_text(encoding="utf-8", errors="replace"):
                results[oid] = ["PASS", f"{rel} contains expected marker"]
            else:
                results[oid] = ["FAIL", f"{rel} lacks expected marker"]
        elif oracle["kind"] == "file_exists":
            results[oid] = (["PASS", f"{rel} exists"] if target.is_file()
                            else ["FAIL", f"{rel} absent"])
        elif oracle["kind"] == "exit_zero_file":
            marker = workspace / rel
            if record["exit_code"] != 0:
                results[oid] = ["FAIL", f"actor exited {record['exit_code']}"]
            elif marker.is_file():
                results[oid] = ["PASS", "actor exit 0 and produced its artifact"]
            else:
                results[oid] = ["UNVERIFIED", f"artifact missing: {rel} — an absent artifact is never a pass"]
    return results


def cmd_score(cfg: dict, output_dir: Path) -> int:
    inventory = output_dir / "attempts.jsonl"
    if not inventory.is_file():
        die(f"no inventory to score: {inventory}")
    scores = {}
    for line in inventory.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        attempt_dir = inventory.parent / record["attempt"]
        scores[record["cell_id"]] = {
            "arm": record["arm"], "task": record["task"], "status": record["status"],
            "canary_intact": record["canary_intact"],
            "oracles": apply_oracles(cfg, record, attempt_dir),
        }
    out = output_dir / "SCORES.json"
    out.write_text(json.dumps(scores, indent=2) + "\n", encoding="utf-8")
    eligible = sum(1 for s in scores.values() if s["status"] == "completed" and s["canary_intact"])
    print(f"scored {len(scores)} cells -> {out} (eligible: {eligible})")
    return 0


def cmd_analyze(cfg: dict, output_dir: Path) -> int:
    scores_path = output_dir / "SCORES.json"
    if not scores_path.is_file():
        die("no SCORES.json — run score first; analyzing absent data cannot pass")
    scores = load_json(scores_path)
    by_arm = {}
    for cell in scores.values():
        bucket = by_arm.setdefault(cell["arm"], {"cells": 0, "eligible": 0, "passed": 0})
        bucket["cells"] += 1
        if cell["status"] == "completed" and cell["canary_intact"]:
            bucket["eligible"] += 1
            if all(v[0] == "PASS" for v in cell["oracles"].values()) and cell["oracles"]:
                bucket["passed"] += 1
    lines = ["# Campaign analysis — " + cfg["name"], "",
             "Counts are of this attempt only; an existence proof is not a rate.", "",
             "| Arm | Cells | Eligible | All-oracles-pass |", "| --- | ---: | ---: | ---: |"]
    for arm in sorted(by_arm):
        b = by_arm[arm]
        lines.append(f"| {arm} | {b['cells']} | {b['eligible']} | {b['passed']} |")
    ineligible = [cid for cid, s in scores.items() if not (s["status"] == "completed" and s["canary_intact"])]
    if ineligible:
        lines += ["", "Ineligible / failed cells (retained, never deleted): " + ", ".join(sorted(ineligible))]
    (output_dir / "ANALYSIS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


# ------------------------------------------------------------------ self-test

def cmd_self_test(tmp: Path) -> int:
    """End-to-end orchestration proof with fake actors. No network, no provider."""
    lab_root = tmp / "lab"
    packs = lab_root / "packs" / "vtest"
    for name in ("vT1-aaaaaaaaaaaaaaaa", "vT2-bbbbbbbbbbbbbbbb"):
        (packs / name).mkdir(parents=True, exist_ok=True)
        (packs / name / "PACK_MARKER").write_text(name + "\n", encoding="utf-8")
    seed = tmp / "seed"
    (seed / "src").mkdir(parents=True)
    (seed / "README.md").write_text("smoke seed\n", encoding="utf-8")
    (seed / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")
    actor = tmp / "fake_actor.py"
    actor.write_text(
        "import pathlib, sys\n"
        "ws = pathlib.Path(sys.argv[sys.argv.index('--workspace') + 1])\n"
        "(ws / 'solution.txt').write_text('done\\n')\n",
        encoding="utf-8",
    )
    reader = tmp / "snooping_actor.py"
    reader.write_text(
        "import pathlib, sys\n"
        "ws = pathlib.Path(sys.argv[sys.argv.index('--workspace') + 1])\n"
        "hidden = ws.parent.parent / 'actor_invisible' / 'CUSTODIAN_CANARY.secret'\n"
        "if hidden.exists():\n"
        "    (ws / 'stolen.txt').write_text(hidden.read_text())\n"
        "(ws / 'solution.txt').write_text('done\\n')\n",
        encoding="utf-8",
    )
    cfg = {
        "schema": SCHEMA, "name": "selftest", "paid": False,
        "arms": {"A": None, "B": {"pack": "packs/vtest/vT1-aaaaaaaaaaaaaaaa"},
                 "C": {"pack": "packs/vtest/vT2-bbbbbbbbbbbbbbbb"}},
        "seed": {"path": str(seed), "family": "selftest"},
        "tasks": [{"id": "S-1", "prompt": "produce solution.txt"}],
        "strata": [{"name": "fake", "launch": {"mode": "fake", "command": str(actor)}}],
        "repeats": 1,
        "oracles": [{"id": "O1", "kind": "exit_zero_file", "path": "solution.txt"}],
    }
    out = tmp / "out"

    # 1. identical initial sources across arms, distinct workspaces
    run_full(cfg, lab_root, out)
    inv = [json.loads(l) for l in (out / "attempts.jsonl").read_text().splitlines() if l.strip()]
    assert len(inv) == 3, f"expected 3 cells, got {len(inv)}"
    by_arm = {r["arm"]: r for r in inv}
    hashes = {r["arm"]: json.dumps(r["initial_hashes"], sort_keys=True) for r in inv}
    assert len(set(hashes.values())) == 1, "initial source hashes differ across arms"
    assert len({by_arm[a]["workspace"] for a in by_arm}) == 3, "workspaces are not distinct"
    assert all(r["canary_intact"] for r in inv), "canary violated in the clean run"
    cmd_score(cfg, out)
    cmd_analyze(cfg, out)
    scores = load_json(out / "SCORES.json")
    assert all(v["oracles"]["O1"][0] == "PASS" for v in scores.values()), "clean run did not pass oracle"

    # 2. a snooping actor violates the canary and becomes ineligible
    cfg2 = json.loads(json.dumps(cfg))
    cfg2["strata"] = [{"name": "fake", "launch": {"mode": "fake", "command": str(reader)}}]
    out2 = tmp / "out2"
    run_full(cfg2, lab_root, out2)
    inv2 = [json.loads(l) for l in (out2 / "attempts.jsonl").read_text().splitlines() if l.strip()]
    assert all(not r["canary_intact"] and r["status"] == "ineligible" for r in inv2), "snoop was not caught"

    # 3. collision refusal + paid-without-envelope refusal + timeout recording
    (out / "notempty").write_text("x", encoding="utf-8")
    try:
        run_full(cfg, lab_root, out)
        raise AssertionError("collision was not refused")
    except SystemExit as exc:
        assert exc.code == 1, "collision refusal exited nonzero-incorrectly"
    envelope = {"status": "UNSET", "per_run_cap": None, "total_cap": None,
                "retry_reserve_fraction": 0.25, "launch_rule": "REFUSED while unset"}
    tmpdesign = tmp / "design.json"
    tmpdesign.write_text(json.dumps({"resource_envelope": envelope}), encoding="utf-8")
    paid = json.loads(json.dumps(cfg))
    paid["paid"] = True
    errors = validate_campaign(paid, lab_root, tmpdesign)
    assert any("envelope" in e for e in errors), "paid-without-envelope was not refused"
    cfg4 = json.loads(json.dumps(cfg))
    cfg4["strata"] = [{"name": "fake", "launch": {"mode": "fake", "command": str(actor), "actor_arg": "--sleep-29"}}]
    actor_sleep = tmp / "sleeper.py"
    actor_sleep.write_text(
        "import pathlib, sys, time\n"
        "ws = pathlib.Path(sys.argv[sys.argv.index('--workspace') + 1])\n"
        "if '--sleep-29' in sys.argv: time.sleep(29)\n"
        "(ws / 'solution.txt').write_text('done\\n')\n",
        encoding="utf-8",
    )
    cfg4["strata"][0]["launch"]["command"] = str(actor_sleep)
    out4 = tmp / "out4"
    run_full(cfg4, lab_root, out4, timeout_s=1)
    inv4 = [json.loads(l) for l in (out4 / "attempts.jsonl").read_text().splitlines() if l.strip()]
    assert all(r["status"] == "timeout" for r in inv4), "timeout was not recorded"

    # 4. resume skips completed cells: a second pass appends nothing
    out5 = tmp / "out5"
    run_full(cfg, lab_root, out5)
    attempt_id = json.loads((out5 / "attempts.jsonl").read_text().splitlines()[0])["attempt"]
    before = len((out5 / "attempts.jsonl").read_text().splitlines())
    run_full(cfg, lab_root, out5, resume=attempt_id)
    after = len((out5 / "attempts.jsonl").read_text().splitlines())
    assert before == after, f"resume re-ran completed cells ({before} -> {after})"
    print("self-test OK")
    return 0


def run_full(cfg: dict, lab_root: Path, out: Path, timeout_s: int = 20, resume: str = None) -> None:
    """Internal helper mirroring cmd_run for the self-test."""
    attempt_dir = None
    if resume is None:
        if out.exists() and any(out.iterdir()):
            die(f"output collision: {out} exists and is non-empty")
        attempt_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid.uuid4().hex[:8]
        attempt_dir = out / attempt_id
        attempt_dir.mkdir(parents=True, exist_ok=True)
        (attempt_dir / "ISOLATION.json").write_text(json.dumps(isolation_posture(lab_root), indent=2) + "\n", encoding="utf-8")
    else:
        attempt_dir = out / str(resume)
        if not attempt_dir.is_dir():
            die(f"cannot resume: attempt {resume} not found under {out}")
    inventory = out / "attempts.jsonl"
    done = set()
    if inventory.exists():
        for line in inventory.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("status") in ("completed", "ineligible", "timeout"):
                    done.add(r["cell_id"])
    with inventory.open("a", encoding="utf-8") as inv:
        for cell in campaign_cells(cfg, cfg["arms"]):
            if cell["cell_id"] in done:
                continue
            record = run_cell(cell, cfg, attempt_dir, lab_root, timeout_s)
            inv.write(json.dumps(record) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["self-test", "validate", "prepare", "run", "score", "analyze"])
    parser.add_argument("--config")
    parser.add_argument("--family", default="family")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output")
    parser.add_argument("--resume")
    parser.add_argument("--lab-root")
    parser.add_argument("--timeout-s", type=int, default=900)
    parser.add_argument("--execute-checks", action="store_true",
                        help="family validate: run the manifest's install/build/check in a disposable copy")
    parser.add_argument("--seed-path", help="prepare: fixture seed directory relative to the repository root")
    args = parser.parse_args()

    if args.mode == "self-test":
        with tempfile.TemporaryDirectory(prefix="dwp-v6-lab-selftest-") as td:
            return cmd_self_test(Path(td))

    lab_root = Path(args.lab_root).resolve() if args.lab_root else default_lab_root()
    design_path = repo_root() / DESIGN_PATH

    if args.mode in ("validate", "prepare") and not args.config:
        if args.mode == "validate":
            if args.family == "family":
                die("validate needs --config <campaign.json> or --family <name>")
            return cmd_validate_family(lab_root, args.family, args.execute_checks)
        if not args.seed_path:
            die("prepare needs --seed-path <path> or --config <campaign.json>")
        return cmd_prepare(lab_root, args.family, args.dry_run, args.seed_path)

    if not args.config:
        die(f"--config is required for {args.mode}")
    cfg = load_json(Path(args.config))

    if args.mode == "validate":
        errors = validate_campaign(cfg, lab_root, design_path)
        if errors:
            print("INVALID campaign config:")
            for e in errors:
                print(f"  - {e}")
            return 1
        print(f"OK campaign {cfg['name']!r}: config valid"
              f" (paid={cfg.get('paid', False)}, arms={sorted(cfg['arms'])})")
        return 0

    if args.mode == "prepare":
        return cmd_prepare(lab_root, args.family, args.dry_run,
                           args.seed_path or load_json(Path(args.config))["seed"]["path"])

    if args.mode == "run":
        if not args.output:
            die("--output is required for run (use a path under the owning plan's analysis_results/lab/)")
        raw = Path(args.output)
        if has_escape(raw):
            die("output path escapes")
        output_dir = raw if raw.is_absolute() else repo_root() / raw
        if not is_within(output_dir, repo_root()):
            die("run output must live inside the repository checkout: the lab root or the owning plan's analysis_results/lab/")
        return cmd_run(cfg, lab_root, output_dir, args.resume, args.timeout_s)

    if args.mode == "score":
        return cmd_score(cfg, Path(args.output))
    if args.mode == "analyze":
        return cmd_analyze(cfg, Path(args.output))
    die("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
