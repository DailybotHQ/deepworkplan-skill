#!/usr/bin/env python3
"""Dev-only schema/contract regression check for the DeepWorkPlan state layer.

Validates every plan fixture's manifest.json / state.json against the shipped
JSON Schemas (skills/deepworkplan/spec/schema/) with a real JSON Schema
validator, then runs contract checks the schemas cannot express:

  * closed-schema direction: an extra top-level field is INVALID (v1 schemas are
    closed; 2.3.0 adds no field — PLAN_STATE.md §6);
  * both supported directions: a 2.2.0 legacy fixture and a 2.3.0 fixture are
    both VALID against the unchanged v1 schemas;
  * unknown future spec_version: schema-valid, but flagged by the contract
    (an executor must not treat it as legacy — DWP_SPECIFICATION.md §6.5);
  * zero-test evidence: a passing gate record whose evidence says it ran or
    selected zero tests is INVALID evidence (DWP_SPECIFICATION.md §5.1.c);
  * stale projection: state.completed_count must not exceed the README's [x]
    count (markdown wins — PLAN_STATE.md §5);
  * partial materialization: a plan directory without README.md is reported.

Runtime files never depend on this script; it needs `jsonschema` (pip).
Exit 1 on any failure. Usage: check-schema-contract.py [--pack DIR] [--fixtures DIR] [PLAN_DIR ...]
"""
import argparse, copy, json, os, re, sys

try:
    import jsonschema
except ImportError:  # pragma: no cover
    print("FAIL jsonschema is not installed (pip install jsonschema) — cannot run the contract check")
    sys.exit(1)

SUPPORTED_SPEC = (2, 3, 0)
ZERO_EVIDENCE = re.compile(r"(ran|selected|executed)\s*=\s*0(\s*/|\b)|no tests? (ran|found|collected)|NO TESTS RAN", re.I)


def vtuple(v):
    try:
        return tuple(int(x) for x in v.split("."))
    except Exception:
        return None


def load_schemas(pack):
    d = os.path.join(pack, "spec", "schema")
    return (json.load(open(os.path.join(d, "plan-manifest.schema.json"))),
            json.load(open(os.path.join(d, "plan-state.schema.json"))))


def errors(schema, doc):
    v = jsonschema.Draft202012Validator(schema)
    return [f"{list(e.path)}: {e.message[:90]}" for e in sorted(v.iter_errors(doc), key=lambda e: list(e.path))]


def check_plan(plan_dir, ms, ss, problems, notes):
    name = os.path.basename(plan_dir.rstrip("/"))
    readme = os.path.join(plan_dir, "README.md")
    materializing = os.path.isfile(readme) and re.search(r"Plan Status: *materializing", open(readme, encoding="utf-8").read()) is not None
    if not os.path.isfile(readme) or materializing:
        why = "README says 'Plan Status: materializing'" if materializing else "no README.md"
        shape = ""
        mpath0 = os.path.join(plan_dir, "manifest.json")
        if os.path.isfile(mpath0):
            try:
                m0 = json.load(open(mpath0))
                bad = errors(ms, m0)
                present = len([f for f in os.listdir(plan_dir) if re.match(r"^\d+\.task_.*\.md$", f)])
                shape = f"; manifest declares {m0.get('task_count')} tasks, {present} task files present" + (f"; manifest invalid: {bad[0]}" if bad else "")
            except Exception as exc:  # noqa: BLE001
                shape = f"; manifest unreadable ({exc})"
        if os.path.isfile(os.path.join(plan_dir, ".contract-expect-partial")):
            notes.append(f"{name}: partial materialization detected as expected ({why}{shape})")
            return
        problems.append(f"{name}: partial materialization — {why}{shape} (complete or discard it with create/refine, never execute)")
        return
    mpath, spath = os.path.join(plan_dir, "manifest.json"), os.path.join(plan_dir, "state.json")
    if not (os.path.isfile(mpath) or os.path.isfile(spath)):
        notes.append(f"{name}: no state layer (optional in a git repo)")
        return
    for label, path, schema in (("manifest", mpath, ms), ("state", spath, ss)):
        if not os.path.isfile(path):
            problems.append(f"{name}: {label}.json missing while the other state file exists")
            continue
        try:
            doc = json.load(open(path))
        except Exception as e:
            problems.append(f"{name}: {label}.json does not parse ({e})")
            continue
        errs = errors(schema, doc)
        if errs:
            problems.append(f"{name}: {label}.json INVALID against the v1 schema: " + "; ".join(errs[:3]))
        else:
            notes.append(f"{name}: {label}.json valid")
        if label == "manifest":
            sv = vtuple(str(doc.get("spec_version", "")))
            if sv is None:
                problems.append(f"{name}: manifest spec_version is not dotted-numeric")
            elif sv > SUPPORTED_SPEC:
                problems.append(f"{name}: manifest declares spec {doc['spec_version']} newer than supported {'.'.join(map(str, SUPPORTED_SPEC))} — must be reported, never treated as legacy")
        if label == "state":
            for t in doc.get("tasks", []):
                for g in t.get("gates", []) or []:
                    ev = str(g.get("evidence", ""))
                    if g.get("passes") is True and ZERO_EVIDENCE.search(ev):
                        problems.append(f"{name}: task {t.get('id')} gate '{g.get('command','')[:40]}' passes=true with zero-selection evidence '{ev[:60]}' — an empty run is not evidence")
                    if g.get("passes") is None:
                        problems.append(f"{name}: task {t.get('id')} gate has passes=null — record unavailable checks as passes=false with a reason")
            readme = os.path.join(plan_dir, "README.md")
            if os.path.isfile(readme):
                md_done = len(re.findall(r"^\s*- \[x\]", open(readme).read(), re.M))
                if doc.get("completed_count", 0) > md_done:
                    problems.append(f"{name}: state.completed_count={doc.get('completed_count')} exceeds README [x]={md_done} — stale/ahead projection (markdown wins)")


def negative_cases(ms, ss, problems, notes):
    base_m = {"schema": "https://deepworkplan.com/schema/plan-manifest/v1.json", "spec_version": "2.3.0", "name": "PLAN_contract_probe",
              "archetype": "individual", "rigor": "standard", "created_at": "2026-09-01T00:00:00Z", "task_count": 2}
    base_s = {"schema": "https://deepworkplan.com/schema/plan-state/v1.json", "plan": "PLAN_contract_probe", "updated_at": "2026-09-01T00:00:00Z",
              "status": "in_progress", "completed_count": 0, "task_count": 2,
              "tasks": [{"id": 1, "file": "1.task_a.md", "title": "a", "status": "pending", "gates": []},
                        {"id": 2, "file": "2.task_final_review.md", "title": "final", "status": "pending", "gates": []}]}
    if errors(ms, base_m) or errors(ss, base_s):
        problems.append("probe: baseline probe documents should be valid"); return
    notes.append("probe: 2.3.0-shaped state/manifest valid against v1 (forward direction)")
    legacy_m = dict(base_m, spec_version="2.2.0")
    if errors(ms, legacy_m):
        problems.append("probe: a 2.2.0 manifest must remain valid (backward direction)")
    else:
        notes.append("probe: 2.2.0 manifest valid (backward direction)")
    extra_m = dict(base_m, efficiency={"tokens": 1})
    if not errors(ms, extra_m):
        problems.append("probe: an extra top-level manifest field must be INVALID (closed v1 schema)")
    else:
        notes.append("probe: extra top-level manifest field rejected (closed schema)")
    extra_s = copy.deepcopy(base_s); extra_s["cost"] = {}
    if not errors(ss, extra_s):
        problems.append("probe: an extra top-level state field must be INVALID (closed v1 schema)")
    else:
        notes.append("probe: extra top-level state field rejected (closed schema)")
    extra_gate = copy.deepcopy(base_s); extra_gate["tasks"][0]["gates"] = [{"command": "x", "passes": True, "last_run": "2026-09-01T00:00:00Z", "cwd": "."}]
    if not errors(ss, extra_gate):
        problems.append("probe: an extra gate-record field must be INVALID (closed gate object) — 2.3.0 evidence goes inside the evidence string")
    else:
        notes.append("probe: extra gate field rejected — evidence string is the carrier")
    wrong_const = dict(base_m, schema="https://deepworkplan.com/schema/plan-manifest/v2.json")
    if not errors(ms, wrong_const):
        problems.append("probe: a v2 schema URL must not validate against the v1 schema")
    else:
        notes.append("probe: v2 schema URL rejected by the v1 schema")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", default="skills/deepworkplan")
    ap.add_argument("--fixtures", default="tests/efficiency/fixtures")
    ap.add_argument("plans", nargs="*")
    a = ap.parse_args()
    ms, ss = load_schemas(a.pack)
    problems, notes = [], []
    plans = list(a.plans)
    if os.path.isdir(a.fixtures):
        for root, dirs, files in os.walk(a.fixtures):
            if os.path.basename(os.path.dirname(root)) == "plans" and os.path.basename(root).startswith("PLAN_"):
                plans.append(root)
    for p in sorted(set(plans)):
        check_plan(p, ms, ss, problems, notes)
    negative_cases(ms, ss, problems, notes)
    for n in notes:
        print("ok  ", n)
    for p in problems:
        print("FAIL", p)
    print(f"{'OK' if not problems else 'FAILED'}: schema/contract check ({len(problems)} problem(s), {len(notes)} checks)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
