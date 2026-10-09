#!/usr/bin/env python3
"""Dev-only schema/contract regression check for the DeepWorkPlan state layer.

Validates every plan fixture's manifest.json / state.json against the shipped
JSON Schemas (skills/deepworkplan/spec/schema/) with a real JSON Schema
validator, then runs contract checks the schemas cannot express:

  * closed-schema direction: an extra top-level field is INVALID (both schema
    families are closed);
  * learnings record: the committed fixtures validate under both halves and
    the closed-vocabulary / anchor-grammar / finding+proposal mutants are
    rejected (spec/BENCHMARK.md section 10);
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
        "https://deepworkplan.com/schema/plan-manifest/v6.json": json.load(open(os.path.join(d, "plan-manifest-v6.schema.json"))),
        "https://deepworkplan.com/schema/benchmark-record/v1.json": json.load(open(os.path.join(d, "benchmark-record.schema.json"))),
        "https://deepworkplan.com/schema/learnings-record/v1.json": json.load(open(os.path.join(d, "learnings-record.schema.json"))),
        "https://deepworkplan.com/schema/dwp-config/v1.json": json.load(open(os.path.join(d, "dwp-config-v1.schema.json"))),
        "https://deepworkplan.com/schema/plan-contract/v7.json": json.load(open(os.path.join(d, "plan-contract-v7.schema.json"))),
        "https://deepworkplan.com/schema/journal-event/v7.json": json.load(open(os.path.join(d, "journal-event-v7.schema.json"))),
        "https://deepworkplan.com/schema/plan-manifest/v7.json": json.load(open(os.path.join(d, "plan-manifest-v7.schema.json"))),
        "https://deepworkplan.com/schema/addon-descriptor/v1.json": json.load(open(os.path.join(d, "addon-descriptor-v1.schema.json"))),
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
    # section 8 reserves: optional additive field. A VALID reserve passes
    # both halves (optionality proof); a non-numeric reserve fails both;
    # the reserve<=limit ceiling is runtime-only (it depends on the
    # sibling field's value, which draft 2020-12 cannot express).
    reserved = copy.deepcopy(contract)
    reserved["resource_envelope"]["limits"][0]["reserve"] = 500
    # the fixture is identity-stamped: adding a field changes the canonical
    # bytes, so the probe re-stamps exactly as a new revision would
    reserved["contract_id"] = c6.compute_contract_id(reserved)
    both_ok(reserved, cs, c6.contract_errors(reserved), "valid reserve accepted", True)
    contract_mutant("reserve as a string", lambda d: d["resource_envelope"]["limits"][0].update(reserve="5"))
    contract_mutant("reserve above the limit", lambda d: d["resource_envelope"]["limits"][0].update(reserve=5000), runtime_only=True)
    contract_mutant("negative reserve", lambda d: d["resource_envelope"]["limits"][0].update(reserve=-1))
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
    notes.append("v6: contract mutants rejected (schema: era / closed object / capability / resource / scheduling / reserve; runtime-only: graph integrity, reserve ceiling)")
    if "model_routing" not in cs["$defs"]["capability"]["enum"]:
        problems.append("v6: model_routing missing from the schema capability enum (section 8 routing authority)")

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

    # Manifest (A12): the REAL materialize writes the manifest; its output
    # validates under the published generation, and the runtime refuses
    # every rewrite path the schema closes (era const, closed object,
    # pointer shape). Two-half drift is caught by construction.
    ms = schemas["https://deepworkplan.com/schema/plan-manifest/v6.json"]
    mtmp = tempfile.mkdtemp(prefix="dwp-manifest-check-")
    mplan = os.path.join(mtmp, "PLAN_manifest_check")
    try:
        os.makedirs(mplan)
        open(os.path.join(mplan, "README.md"), "w").write("# manifest check\n")
        mdraft = os.path.join(mtmp, "draft.json")
        mcontract = copy.deepcopy(contract)
        mcontract["plan"] = "PLAN_manifest_check"
        json.dump(mcontract, open(mdraft, "w"))
        result = ledger.materialize_plan(mplan, mdraft, authority="checker")
        manifest = json.load(open(os.path.join(mplan, "manifest.json")))
        merrs = errors(ms, manifest)
        if merrs or result["contract_id"] != manifest["contract"]["id"]:
            problems.append(f"v6 manifest probe: jsonschema rejects the real materialize manifest ({merrs[:1]})")
        else:
            notes.append("v6: manifest written by the shipped materialize validates under plan-manifest-v6.schema.json")
        for label, mutate in (
            ("mixed-era schema url", lambda d: d.update(schema="https://deepworkplan.com/schema/plan-manifest/v5.json")),
            ("extra top-level field", lambda d: d.update(spec_version="6.0.0")),
            ("non-hex contract id", lambda d: d["contract"].update(id="not-hex")),
            ("wrong pointer path", lambda d: d["contract"].update(path="contracts/1.json")),
        ):
            doc = copy.deepcopy(manifest)
            mutate(doc)
            if not errors(ms, doc):
                problems.append(f"v6 manifest mutant {label}: accepted by the schema")
        # runtime: a v5-generation manifest is refused untouched, and a
        # differing contract never rewrites what already landed
        v5plan = os.path.join(mtmp, "PLAN_v5_manifest")
        os.makedirs(v5plan)
        open(os.path.join(v5plan, "README.md"), "w").write("# v5\n")
        json.dump({"schema": "https://deepworkplan.com/schema/plan-manifest/v5.json",
                   "spec_version": "5.0.0"}, open(os.path.join(v5plan, "manifest.json"), "w"))
        try:
            ledger.materialize_plan(v5plan, mdraft, authority="checker")
            problems.append("v6 manifest probe: a v5-generation manifest was rewritten instead of refused")
        except ledger.LedgerError:
            pass
        if json.load(open(os.path.join(v5plan, "manifest.json"))).get("spec_version") != "5.0.0":
            problems.append("v6 manifest probe: the refused v5 manifest was modified anyway")
        notes.append("v6: manifest mutants rejected (era const / closed object / pointer shape) and rewrite refusals hold")
    finally:
        shutil.rmtree(mtmp, ignore_errors=True)


def benchmark_cases(schemas, problems, notes, pack):
    """Benchmark record (spec/BENCHMARK.md): the committed fixtures validate
    under BOTH halves - jsonschema over the published schema, and the shipped
    benchmark.validate_record - and the halves agree on the mutants. The
    cross-field no-imputation rules (an unmetered record carries no values;
    an unavailable diff window carries no counts; a task span is null
    exactly when its end is; an unavailable context-accounting block carries
    no values) are runtime-expressive only, so those mutants are
    runtime-only probes, mirroring the contract-mutant convention above."""
    bs = schemas["https://deepworkplan.com/schema/benchmark-record/v1.json"]
    bdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "tests", "fixtures", "v6", "benchmark-records")
    names = ("benchmark-record-metered.json", "benchmark-record-unmetered.json",
             "benchmark-record-minimal.json", "benchmark-record-spans.json",
             "benchmark-record-accounting.json")
    docs = []
    for name in names:
        path = os.path.join(bdir, name)
        if not os.path.isfile(path):
            problems.append(f"benchmark: fixture {name} missing")
            continue
        docs.append((name, json.load(open(path))))
    if docs:
        benchmark = load_pack_module(pack, "benchmark")
        for name, doc in docs:
            jerrs = errors(bs, doc)
            rerrs = benchmark.validate_record(doc)
            if jerrs:
                problems.append(f"benchmark fixture {name}: jsonschema rejects it ({jerrs[:1]})")
            if rerrs:
                problems.append(f"benchmark fixture {name}: shipped validator rejects it ({rerrs[:1]})")
        if not problems:
            notes.append("benchmark: all five record fixtures valid under both halves "
                         "(jsonschema + shipped validator; spans present / absent-evidence "
                         "/ accounting available + unavailable)")

        def both_reject(label, mutate):
            doc = copy.deepcopy(docs[0][1])
            mutate(doc)
            jerrs, rerrs = errors(bs, doc), benchmark.validate_record(doc)
            if not jerrs or not rerrs:
                problems.append(f"benchmark mutant {label}: a half accepted it (jsonschema={bool(jerrs)} runtime={bool(rerrs)})")

        def runtime_rejects(label, mutate, base=None):
            doc = copy.deepcopy(docs[0][1] if base is None else base)
            mutate(doc)
            if not benchmark.validate_record(doc):
                problems.append(f"benchmark mutant {label}: runtime validator accepted it")

        both_reject("extra top-level field", lambda d: d.update(mystery=1))
        both_reject("wrong schema const", lambda d: d.update(schema="https://deepworkplan.com/schema/benchmark-record/v2.json"))
        both_reject("short contract id", lambda d: d.update(contract_id="zz"))
        both_reject("plan name grammar", lambda d: d.update(plan="not a plan name"))
        both_reject("v5 generation", lambda d: d.update(generation="v5"))
        both_reject("unknown status", lambda d: d.update(status="finished"))
        runtime_rejects("unmetered record carrying values (imputation)",
                        lambda d: d["metered"].update(flag=False))
        runtime_rejects("metered flag without any value",
                        lambda d: d["metered"].update(tokens=None, spend_usd=None))
        runtime_rejects("unavailable diff carrying counts",
                        lambda d: d["diff_stats"].update(available=False))
        runtime_rejects("available diff lacking counts",
                        lambda d: d["diff_stats"].update(files=None))
        by_name = dict(docs)
        spans_doc = by_name.get("benchmark-record-spans.json")
        if spans_doc is not None:
            runtime_rejects("span with zeroed missing evidence (imputation)",
                            lambda d: d["timing"]["task_spans"][1].update(span_seconds=0),
                            base=spans_doc)
        acct_doc = by_name.get("benchmark-record-accounting.json")
        if acct_doc is not None:
            runtime_rejects("imputed-looking context accounting",
                            lambda d: d["context_accounting"].update(instruction_bytes=12),
                            base=acct_doc)
        if not problems:
            notes.append("benchmark: mutants rejected (schema const / closed object / grammar / no-imputation cross-rules incl. spans + accounting)")


def learnings_cases(schemas, problems, notes, pack):
    """Learnings record (spec/BENCHMARK.md section 10): the committed
    fixtures validate under BOTH halves - jsonschema over the published
    schema, and the shipped benchmark.validate_learnings - and the halves
    agree on the mutants. The closed category vocabulary, the closed
    top-level object, the anchor grammar (integer seq >= 1; section
    <= 64 chars, no paths) and the required finding+proposal pair are all
    schema-expressive, so every learnings mutant is a both-halves probe."""
    ls = schemas["https://deepworkplan.com/schema/learnings-record/v1.json"]
    ldir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "tests", "fixtures", "v6", "benchmark-records")
    names = ("learnings-record-populated.json", "learnings-record-template.json")
    docs = []
    for name in names:
        path = os.path.join(ldir, name)
        if not os.path.isfile(path):
            problems.append(f"learnings: fixture {name} missing")
            continue
        docs.append((name, json.load(open(path))))
    if docs:
        benchmark = load_pack_module(pack, "benchmark")
        for name, doc in docs:
            jerrs = errors(ls, doc)
            rerrs = benchmark.validate_learnings(doc)
            if jerrs:
                problems.append(f"learnings fixture {name}: jsonschema rejects it ({jerrs[:1]})")
            if rerrs:
                problems.append(f"learnings fixture {name}: shipped validator rejects it ({rerrs[:1]})")
        if not problems:
            notes.append("learnings: populated + template fixtures valid under both halves "
                         "(jsonschema + shipped validator; unanchored entry carried)")

        def both_reject(label, mutate):
            doc = copy.deepcopy(docs[0][1])
            mutate(doc)
            jerrs, rerrs = errors(ls, doc), benchmark.validate_learnings(doc)
            if not jerrs or not rerrs:
                problems.append(f"learnings mutant {label}: a half accepted it (jsonschema={bool(jerrs)} runtime={bool(rerrs)})")

        both_reject("unknown category (closed vocabulary)",
                    lambda d: d["curated"][0].update(category="performance-gap"))
        both_reject("extra top-level field", lambda d: d.update(mystery=1))
        both_reject("anchor section with a path",
                    lambda d: d["curated"][0].update(anchor={"section": "spec/BENCHMARK.md"}))
        both_reject("curated entry missing finding", lambda d: d["curated"][0].pop("finding"))
        both_reject("curated entry missing proposal", lambda d: d["curated"][1].pop("proposal"))
        both_reject("anchor seq as a string", lambda d: d["curated"][0].update(anchor={"seq": "3"}))
        if not problems:
            notes.append("learnings: mutants rejected by both halves (closed vocabulary / "
                         "closed object / anchor grammar / required finding+proposal)")


def v7_cases(schemas, problems, notes, pack):
    """v7 generation (spec/V7_CONTRACT.md): the ledger-generated fixtures
    under tests/fixtures/v7/ are valid under BOTH halves - jsonschema over
    plan-contract/v7, journal-event/v7 and plan-manifest/v7, and the shipped
    contract_v6 validator - and the halves agree on every mutant: the v7
    additions (parallel_safe, delegation) are refused under the v6 URLs, and
    a delegation that claims evidence or skips its digest is refused."""
    cs = schemas["https://deepworkplan.com/schema/plan-contract/v7.json"]
    js = schemas["https://deepworkplan.com/schema/journal-event/v7.json"]
    ms = schemas["https://deepworkplan.com/schema/plan-manifest/v7.json"]
    cs6 = schemas["https://deepworkplan.com/schema/plan-contract/v6.json"]
    js6 = schemas["https://deepworkplan.com/schema/journal-event/v6.json"]
    fdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "tests", "fixtures", "v7")
    cv6 = load_pack_module(pack, "contract_v6")
    before = len(problems)
    try:
        contract = json.load(open(os.path.join(fdir, "contract-minimal-v7.json")))
        manifest = json.load(open(os.path.join(fdir, "manifest-v7.json")))
        events = [json.loads(l) for l in open(os.path.join(fdir, "journal-delegation-v7.ndjson")) if l.strip()]
    except (OSError, ValueError) as exc:
        problems.append(f"v7: fixtures unreadable ({exc})")
        return
    if errors(cs, contract) or cv6.contract_errors(contract):
        problems.append(f"v7 contract fixture rejected (jsonschema={errors(cs, contract)[:1]} runtime={cv6.contract_errors(contract)[:1]})")
    if errors(ms, manifest):
        problems.append(f"v7 manifest fixture rejected ({errors(ms, manifest)[:1]})")
    for ev in events:
        if errors(js, ev) or cv6.journal_event_errors(ev, contract):
            problems.append(f"v7 journal fixture seq {ev.get('seq')} rejected")
    if cv6.journal_errors(events, contract):
        problems.append("v7 journal fixture fails the sequence rules")
    if not any(e.get("type") == "delegation" for e in events):
        problems.append("v7 journal fixture carries no delegation event")

    def contract_both_reject(label, mutate, schema=cs):
        doc = copy.deepcopy(contract)
        doc.pop("contract_id", None)
        mutate(doc)
        if not errors(schema, doc) or not cv6.contract_errors(doc):
            problems.append(f"v7 contract mutant {label}: a half accepted it")

    contract_both_reject("parallel_safe not boolean",
                         lambda d: d["tasks"][0].update(parallel_safe="yes"))
    contract_both_reject("parallel_safe under the v6 URL",
                         lambda d: d.update(schema="https://deepworkplan.com/schema/plan-contract/v6.json"),
                         schema=cs6)

    launch = next(e for e in events if e.get("type") == "delegation" and e.get("state") == "launched")
    done = next(e for e in events if e.get("type") == "delegation" and e.get("state") == "completed")

    def event_both_reject(label, base, mutate, schema=js, runtime_contract=contract):
        ev = copy.deepcopy(base)
        mutate(ev)
        if not errors(schema, ev) or not cv6.journal_event_errors(ev, runtime_contract):
            problems.append(f"v7 event mutant {label}: a half accepted it "
                            f"(jsonschema={bool(errors(schema, ev))} runtime={bool(cv6.journal_event_errors(ev, runtime_contract))})")

    v6_contract = dict(contract, schema="https://deepworkplan.com/schema/plan-contract/v6.json")
    event_both_reject("delegation under the v6 journal URL", launch,
                      lambda e: e.update(schema="https://deepworkplan.com/schema/journal-event/v6.json"),
                      schema=js6, runtime_contract=None)
    event_both_reject("launch without prompt_digest", launch, lambda e: e.pop("prompt_digest"))
    event_both_reject("delegation claims trust", launch, lambda e: e.update(trust="observed"))
    event_both_reject("unknown transport", launch, lambda e: e.update(transport="email"))
    event_both_reject("unknown state", launch, lambda e: e.update(state="paused"))
    event_both_reject("result on a launch", launch, lambda e: e.update(result_path="a.txt"))
    event_both_reject("absolute result path", done, lambda e: e.update(result_path="/etc/passwd"))
    event_both_reject("traversing result path", done, lambda e: e.update(result_path="../../x"))
    event_both_reject("bad prompt digest", launch, lambda e: e.update(prompt_digest="md5:abc"))
    event_both_reject("unknown field", launch, lambda e: e.update(secret="x"))
    # runtime-only: the generation binding is a cross-record rule
    if not cv6.journal_event_errors(launch, v6_contract):
        problems.append("v7 event under a v6 contract: runtime accepted a mixed generation")
    if len(problems) == before:
        notes.append("v7: contract/manifest/journal fixtures (ledger-generated) valid under both "
                     "halves; 2 contract + 10 delegation mutants rejected by both; mixed "
                     "generation refused at runtime")


def config_cases(schemas, problems, notes, pack):
    """Configuration file (spec/CONFIG.md): the committed fixtures validate
    under BOTH halves - jsonschema over the published dwp-config v1 schema,
    and the shipped shared/config.py (no warning for a known key) - and the
    halves agree entry by entry on the mutants: a registry entry is
    schema-valid exactly when the runtime reader accepts it."""
    cs = schemas["https://deepworkplan.com/schema/dwp-config/v1.json"]
    cdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "tests", "fixtures", "v7", "config")
    names = ("config-full.json", "config-benchmark-only.json",
             "config-prerelease-version.json")
    config = load_pack_module(pack, "config")
    keys = config.addon_keys(os.path.join(pack, "addons"))
    before = len(problems)
    for name in names:
        path = os.path.join(cdir, name)
        if not os.path.isfile(path):
            problems.append(f"config: fixture {name} missing")
            continue
        doc = json.load(open(path))
        jerrs = errors(cs, doc)
        if jerrs:
            problems.append(f"config fixture {name}: jsonschema rejects it ({jerrs[:1]})")
        files = [(".dwp/config.json", path, doc, None)]
        _view, warns = config.resolve_addons(files, keys)
        _b = config.resolve_benchmark(files)
        if warns or _b[2]:
            problems.append(f"config fixture {name}: runtime warned ({(warns + _b[2])[:1]})")
    entries = [
        ("enabled only", {"enabled": True}, True),
        ("enabled + version", {"enabled": False, "version": "v1.2.3"}, True),
        ("prerelease version", {"enabled": True, "version": "v7.0.0-beta.1"}, True),
        ("missing enabled", {"version": "v1.2.3"}, False),
        ("string enabled", {"enabled": "yes"}, False),
        ("floating version", {"enabled": True, "version": "latest"}, False),
        ("unprefixed version", {"enabled": True, "version": "1.2.3"}, False),
        ("extra field", {"enabled": True, "pin": "main"}, False),
        ("not an object", True, False),
    ]
    for label, entry, expect in entries:
        doc = {"addons": {"vim": entry}}
        j_ok = not errors(cs, doc)
        r_ok = config._entry_error(entry) is None
        if j_ok != expect or r_ok != expect:
            problems.append(f"config entry {label}: expected valid={expect}, "
                            f"jsonschema={j_ok} runtime={r_ok}")
    for label, doc in (("addons not an object", {"addons": ["vim"]}),
                       ("benchmark not an object", {"benchmark": "on"}),
                       ("wrong-typed learnings", {"benchmark": {"enabled": True, "learnings": "y"}})):
        if not errors(cs, doc):
            problems.append(f"config mutant {label}: jsonschema accepted it")
    if len(problems) == before:
        notes.append("config: three fixtures valid under both halves; nine registry "
                     "entries agree (jsonschema == shipped reader); three top-level "
                     "mutants rejected")


def descriptor_cases(schemas, problems, notes, pack):
    """Addon descriptors (spec/ADDONS.md section 7): every shipped addon.json
    is valid under BOTH halves - jsonschema over the published descriptor
    schema and the shipped config.descriptor_errors - its key equals its
    directory, and the halves agree on the mutants."""
    ds = schemas["https://deepworkplan.com/schema/addon-descriptor/v1.json"]
    config = load_pack_module(pack, "config")
    addons = os.path.join(pack, "addons")
    keys = config.addon_keys(addons)
    before = len(problems)
    shipped = []
    for key in keys:
        path = os.path.join(addons, key, "addon.json")
        if not os.path.isfile(path):
            problems.append(f"descriptor: addons/{key}/addon.json missing")
            continue
        doc = json.load(open(path))
        shipped.append(doc)
        jerrs, rerrs = errors(ds, doc), config.descriptor_errors(doc, key)
        if jerrs:
            problems.append(f"descriptor {key}: jsonschema rejects it ({jerrs[:1]})")
        if rerrs:
            problems.append(f"descriptor {key}: shipped validator rejects it ({rerrs[:1]})")
    base = next((d for d in shipped if d.get("transport")), None)
    if base is None:
        problems.append("descriptor: no transport descriptor to mutate")
        return
    mutants = (
        ("unknown field", lambda d: d.update(extra=1)),
        ("missing detect", lambda d: d.pop("detect")),
        ("shell metacharacter", lambda d: d["detect"].update(command="x; rm -rf /")),
        ("command and paths", lambda d: d["detect"].update(paths=["a"])),
        ("unknown ability", lambda d: d.update(provides_abilities=["root_shell"])),
        ("repeated grant", lambda d: d.update(requires_grants=["agent_delegation", "agent_delegation"])),
        ("unknown transport", lambda d: d.update(transport="carrier-pigeon")),
        ("transport without subagents", lambda d: d.update(provides_abilities=["cancel_children"])),
        ("floating product tag", lambda d: d["product"].update(tag="main")),
        ("interface zero", lambda d: d["product"].update(interface=0)),
        ("bad interface_from", lambda d: d["detect"].update(interface_from="eval:x")),
        ("wrong schema const", lambda d: d.update(schema="https://deepworkplan.com/schema/addon-descriptor/v2.json")),
    )
    for label, mutate in mutants:
        doc = copy.deepcopy(base)
        mutate(doc)
        jerrs, rerrs = errors(ds, doc), config.descriptor_errors(doc)
        if not jerrs or not rerrs:
            problems.append(f"descriptor mutant {label}: a half accepted it "
                            f"(jsonschema={bool(jerrs)} runtime={bool(rerrs)})")
    if len(problems) == before:
        notes.append(f"descriptor: {len(shipped)} shipped addon.json valid under both "
                     f"halves with key == directory; {len(mutants)} mutants rejected by both")


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
    benchmark_cases(schemas, problems, notes, a.pack)
    learnings_cases(schemas, problems, notes, a.pack)
    v7_cases(schemas, problems, notes, a.pack)
    config_cases(schemas, problems, notes, a.pack)
    descriptor_cases(schemas, problems, notes, a.pack)
    for n in notes:
        print("ok  ", n)
    for p in problems:
        print("FAIL", p)
    print(f"{'OK' if not problems else 'FAILED'}: schema/contract check ({len(problems)} problem(s), {len(notes)} checks)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
