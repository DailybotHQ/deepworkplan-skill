#!/usr/bin/env python3
"""Dev-only schema/contract regression check for the DeepWorkPlan state layer.

Validates every plan fixture's manifest.json / state.json against the shipped
JSON Schemas (skills/deepworkplan/spec/schema/) with a real JSON Schema
validator, then runs contract checks the schemas cannot express:

  * closed-schema direction: an extra top-level field is INVALID (both schema
    families are closed);
  * both supported directions: legacy v1 plans and Lite/Full v2 plans select
    their declared schema family rather than being silently coerced;
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

SUPPORTED_SPEC = (2, 4, 0)
ZERO_EVIDENCE = re.compile(r"(ran|selected|executed)\s*=\s*0(\s*/|\b)|no tests? (ran|found|collected)|NO TESTS RAN", re.I)


def vtuple(v):
    try:
        return tuple(int(x) for x in v.split("."))
    except Exception:
        return None


def load_schemas(pack):
    d = os.path.join(pack, "spec", "schema")
    return {
        "https://deepworkplan.com/schema/plan-manifest/v1.json": json.load(open(os.path.join(d, "plan-manifest.schema.json"))),
        "https://deepworkplan.com/schema/plan-state/v1.json": json.load(open(os.path.join(d, "plan-state.schema.json"))),
        "https://deepworkplan.com/schema/plan-manifest/v2.json": json.load(open(os.path.join(d, "plan-manifest-v2.schema.json"))),
        "https://deepworkplan.com/schema/plan-state/v2.json": json.load(open(os.path.join(d, "plan-state-v2.schema.json"))),
        "https://deepworkplan.com/schema/plan-contract/v6.json": json.load(open(os.path.join(d, "plan-contract-v6.schema.json"))),
        "https://deepworkplan.com/schema/journal-event/v6.json": json.load(open(os.path.join(d, "journal-event-v6.schema.json"))),
        "https://deepworkplan.com/schema/plan-snapshot/v6.json": json.load(open(os.path.join(d, "plan-snapshot-v6.schema.json"))),
    }


def load_pack_module(pack, name):
    """Import a shipped runtime module for the two-half drift check.

    Importing from the pack MUST NOT leave bytecode inside it - a
    __pycache__ under skills/deepworkplan/ fails the pack-purity tests -
    so bytecode writing is disabled for the duration of the import no
    matter how this script was invoked. The shared directory goes on
    sys.path first so plain sibling imports (ledger imports contract_v6)
    resolve to the shipped files too.
    """
    import importlib.util
    shared = os.path.join(pack, "shared")
    prior_dw = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        if shared not in sys.path:
            sys.path.insert(0, shared)
        spec = importlib.util.spec_from_file_location(
            name, os.path.join(shared, name + ".py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = prior_dw
    return module


def v6_canonical_id(doc):
    """Independent re-implementation of the section-3.1 identity function."""
    import hashlib
    body = {k: v for k, v in doc.items() if k != "contract_id"}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def v6_cases(schemas, problems, notes, pack, fixtures):
    """v6 contract + journal-event surfaces: jsonschema (independent half)
    must agree with the shipped runtime validator on every probe. Drift
    between the two implementations is itself a failure."""
    cs = schemas["https://deepworkplan.com/schema/plan-contract/v6.json"]
    js = schemas["https://deepworkplan.com/schema/journal-event/v6.json"]
    ss = schemas["https://deepworkplan.com/schema/plan-snapshot/v6.json"]
    v6dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "tests", "fixtures", "v6")
    cpath = os.path.join(v6dir, "contract-minimal.json")
    jpath = os.path.join(v6dir, "journal-events.ndjson")
    if not (os.path.isfile(cpath) and os.path.isfile(jpath)):
        problems.append("v6: fixtures tests/fixtures/v6/ missing - cannot check the v6 surfaces")
        return
    contract = json.load(open(cpath))
    events = [json.loads(l) for l in open(jpath) if l.strip()]
    c6 = load_pack_module(pack, "contract_v6")

    def both_ok(doc, schema, runtime_errors, label, expect_valid,
                runtime_only=False):
        schema_errs = errors(schema, doc)
        if expect_valid and schema_errs:
            problems.append(f"v6 probe {label}: jsonschema rejects a document the runtime accepts ({schema_errs[0]})")
        if not expect_valid and not runtime_only and not schema_errs:
            problems.append(f"v6 probe {label}: jsonschema accepts a document the runtime rejects (drift)")
        if bool(runtime_errors) != (not expect_valid):
            problems.append(f"v6 probe {label}: runtime validator disagrees (drift)")
        # runtime_only marks semantics a schema cannot express (graph
        # integrity: dangling references, duplicate ids, cycles) - the same
        # category as the v1/v2 contract checks this script already performs
        # outside the schemas. The runtime must still reject them.

    # Positive: fixtures validate under BOTH halves.
    both_ok(contract, cs, c6.contract_errors(contract), "contract fixture", True)
    if len(events) != 14:
        problems.append(f"v6 journal fixture carries {len(events)} events; the closed catalog has 14 types and the fixture covers each once")
    for i, event in enumerate(events):
        both_ok(event, js, c6.journal_event_errors(event), f"journal event {event.get('type')} (line {i+1})", True)
    if not c6.journal_errors(events, contract=contract):
        notes.append("v6: contract + journal fixtures valid under both halves (jsonschema + shipped validator)")
    else:
        problems.append("v6: journal sequence invalid under the shipped validator")

    # Identity: the checker's own canonicalization must reproduce the stamp.
    if v6_canonical_id(contract) != contract.get("contract_id"):
        problems.append("v6: independent canonical sha256 does not reproduce the fixture's contract_id (identity drift)")
    else:
        notes.append("v6: contract_id reproduced by an independent canonicalization")
    if c6.compute_contract_id(contract) != contract.get("contract_id"):
        problems.append("v6: shipped compute_contract_id disagrees with the stamped fixture id")

    # Snapshot: the REAL projector runs over the same fixtures and its output
    # must validate under the published schema - drift between writer and
    # schema is caught by construction, not by a hand-maintained fixture.
    ledger = load_pack_module(pack, "ledger")
    if "/plan-state/" in ledger.STATE_SCHEMA_URL:
        problems.append("v6: the snapshot must publish under its own new-generation URL "
                        "(RFC 9.1), never inside the frozen plan-state v1/v2/v5 shape series")
    else:
        notes.append("v6: snapshot URL is a new schema-URL generation, outside the frozen plan-state series")
    if ledger.STATE_SCHEMA_URL != "https://deepworkplan.com/schema/plan-snapshot/v6.json":
        problems.append("v6: snapshot URL label does not map to the shipped schema file name")
    import shutil, tempfile
    tmp = tempfile.mkdtemp(prefix="dwp-snapshot-check-")
    plandir = os.path.join(tmp, "PLAN_snapshot_check")
    try:
        os.makedirs(plandir)
        shutil.copyfile(cpath, os.path.join(plandir, "contract.json"))
        shutil.copyfile(jpath, os.path.join(plandir, "journal.ndjson"))
        rec = ledger.PlanRecords(plandir)
        lock = ledger.CooperativeLock(plandir).acquire()
        try:
            snapshot = ledger.Writer(rec, lock).project()
        finally:
            lock.release()
        errs = errors(ss, snapshot)
        if errs:
            problems.append(f"v6: jsonschema rejects the real projector's snapshot ({errs[0]})")
        else:
            notes.append("v6: snapshot produced by the shipped ledger validates under plan-snapshot-v6.schema.json")
        for label, mutate in (
            ("mixed-era schema url", lambda d: d.update(schema="https://deepworkplan.com/schema/plan-state/v5.json")),
            ("extra top-level field", lambda d: d.update(efficiency={"tokens": 1})),
            ("non-enum trust on satisfied criterion",
             lambda d: d["tasks"][0]["criteria"][0].update(trust="vibes") if d["tasks"][0]["criteria"] and d["tasks"][0]["criteria"][0].get("satisfied") else d["tasks"][0]["criteria"].insert(0, {"criterion": "AC-valid-contract-shape", "satisfied": True, "via_seq": 3, "trust": "vibes"})),
            ("fabricated position seq", lambda d: d["positions"].update(gate_run={"seq": 0})),
        ):
            doc = copy.deepcopy(snapshot)
            mutate(doc)
            if not errors(ss, doc):
                problems.append(f"v6 snapshot mutant {label}: accepted by the schema")
        notes.append("v6: snapshot mutants rejected (era const / closed object / trust enum / seq floor)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # Negative probes: every mutant must fail BOTH halves identically.
    def contract_mutant(label, mutate, runtime_only=False):
        doc = copy.deepcopy(contract)
        mutate(doc)
        both_ok(doc, cs, c6.contract_errors(doc), label, False,
                runtime_only=runtime_only)

    contract_mutant("mixed-era schema url", lambda d: d.update(schema="https://deepworkplan.com/schema/plan-state/v5.json"))
    contract_mutant("extra top-level field", lambda d: d.update(efficiency={"tokens": 1}))
    contract_mutant("unsupported capability", lambda d: d["permissions"]["granted"].append("time_travel"))
    contract_mutant("negative resource limit", lambda d: d["resource_envelope"]["limits"][0].update(limit=-1))
    contract_mutant("enforced limit without metering source", lambda d: d["resource_envelope"]["limits"][0].pop("metering_source"))
    contract_mutant("dangling prerequisite", lambda d: d["tasks"][1]["prerequisites"].append("T-missing"), runtime_only=True)
    contract_mutant("duplicate criterion id", lambda d: d["acceptance"]["criteria"].append(copy.deepcopy(d["acceptance"]["criteria"][0])), runtime_only=True)
    contract_mutant("prerequisite cycle", lambda d: d["tasks"][0]["prerequisites"].append("T-ship-validator"), runtime_only=True)
    # Scheduling policy (RFC section 5): every bound is optional but never
    # unbounded when present — both halves reject the same out-of-policy
    # declarations (starvation floor, negative caps, open objects, empty
    # handoff conditions).
    contract_mutant("zero starvation threshold", lambda d: d["scheduling"].update(starvation_threshold_events=0))
    contract_mutant("negative adaptation cap", lambda d: d["scheduling"].update(max_adaptations_per_task=-1))
    contract_mutant("negative retry cap", lambda d: d["scheduling"].update(max_retries_per_gate=-1))
    contract_mutant("scheduling with an unknown field", lambda d: d["scheduling"].update(mode="auto"))
    contract_mutant("empty handoff condition", lambda d: d["scheduling"].update(handoff={"fresh_context": ""}))
    notes.append("v6: contract mutants rejected (schema: era / closed object / capability / resource / scheduling; runtime-only: graph integrity)")

    def event_mutant(label, mutate):
        doc = copy.deepcopy(events[0])
        mutate(doc)
        both_ok(doc, js, c6.journal_event_errors(doc), label, False)

    event_mutant("unknown event type", lambda e: e.update(type="time_travel"))
    event_mutant("unknown payload key", lambda e: e.update(mystery=1))
    pair = copy.deepcopy(events[9])
    assert pair["type"] == "control_pair"
    pair["old_leg"] = {"available": False, "outcome": "FAIL", "log": "x"}
    both_ok(pair, js, c6.journal_event_errors(pair), "unavailable old leg carrying an outcome", False)
    appr = copy.deepcopy(events[1])
    appr["mechanism"] = "migration"
    both_ok(appr, js, c6.journal_event_errors(appr), "third approval mechanism", False)
    startfp = copy.deepcopy(events[0])
    assert startfp["type"] == "task_start"
    startfp["fingerprint"] = {"revision": "r0", "dirty": 3}
    both_ok(startfp, js, c6.journal_event_errors(startfp), "task_start fingerprint with a non-string dirty", False)
    startfp2 = copy.deepcopy(events[0])
    startfp2["fingerprint"] = {"revision": "r0", "dirty": "", "staged": "yes"}
    both_ok(startfp2, js, c6.journal_event_errors(startfp2), "task_start fingerprint with an extra key", False)
    notes.append("v6: journal mutants rejected by both halves (catalog / closed object / D3-3 / D3-2 / fingerprint shape)")


def errors(schema, doc):
    v = jsonschema.Draft202012Validator(schema)
    return [f"{list(e.path)}: {e.message[:90]}" for e in sorted(v.iter_errors(doc), key=lambda e: list(e.path))]


def schema_for(doc, schemas, label):
    declared = doc.get("schema")
    schema = schemas.get(declared)
    if schema is None:
        return None, f"unknown {label} schema URL {declared!r}"
    return schema, None


def check_plan(plan_dir, schemas, problems, notes):
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
                schema, why = schema_for(m0, schemas, "manifest")
                bad = [why] if why else errors(schema, m0)
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
    for label, path in (("manifest", mpath), ("state", spath)):
        if not os.path.isfile(path):
            problems.append(f"{name}: {label}.json missing while the other state file exists")
            continue
        try:
            doc = json.load(open(path))
        except Exception as e:
            problems.append(f"{name}: {label}.json does not parse ({e})")
            continue
        schema, why = schema_for(doc, schemas, label)
        errs = [why] if why else errors(schema, doc)
        if errs:
            problems.append(f"{name}: {label}.json INVALID against its declared schema: " + "; ".join(errs[:3]))
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


def negative_cases(schemas, problems, notes):
    ms = schemas["https://deepworkplan.com/schema/plan-manifest/v1.json"]
    ss = schemas["https://deepworkplan.com/schema/plan-state/v1.json"]
    ms2 = schemas["https://deepworkplan.com/schema/plan-manifest/v2.json"]
    ss2 = schemas["https://deepworkplan.com/schema/plan-state/v2.json"]
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
    lite_m = dict(base_m, schema="https://deepworkplan.com/schema/plan-manifest/v2.json", spec_version="2.4.0", plan_format="lite")
    lite_s = {"schema": "https://deepworkplan.com/schema/plan-state/v2.json", "plan": "PLAN_contract_probe", "updated_at": "2026-09-01T00:00:00Z", "status": "pending", "completed_count": 0, "task_count": 1, "format": "lite", "materialization": "ready", "promotion": None, "checkpoint": None, "blocked": None, "tasks": [{"id": 1, "locator": {"kind": "inline", "value": "#task-1"}, "title": "a", "status": "pending", "gates": []}]}
    if errors(ms2, lite_m) or errors(ss2, lite_s):
        problems.append("probe: a 2.4.0 Lite state/manifest must validate against v2")
    else:
        notes.append("probe: 2.4.0 Lite state/manifest valid against v2")
    bad_locator = copy.deepcopy(lite_s); bad_locator["tasks"][0]["locator"]["value"] = "../escape.md"
    if not errors(ss2, bad_locator):
        problems.append("probe: a Lite task locator must reject paths outside the plan")
    else:
        notes.append("probe: invalid Lite task locator rejected")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", default="skills/deepworkplan")
    ap.add_argument("--fixtures", default="tests/efficiency/fixtures")
    ap.add_argument("plans", nargs="*")
    a = ap.parse_args()
    schemas = load_schemas(a.pack)
    problems, notes = [], []
    plans = list(a.plans)
    if os.path.isdir(a.fixtures):
        for root, dirs, files in os.walk(a.fixtures):
            if os.path.basename(os.path.dirname(root)) == "plans" and os.path.basename(root).startswith("PLAN_"):
                plans.append(root)
    for p in sorted(set(plans)):
        check_plan(p, schemas, problems, notes)
    negative_cases(schemas, problems, notes)
    v6_cases(schemas, problems, notes, a.pack, a.fixtures)
    for n in notes:
        print("ok  ", n)
    for p in problems:
        print("FAIL", p)
    print(f"{'OK' if not problems else 'FAILED'}: schema/contract check ({len(problems)} problem(s), {len(notes)} checks)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
