#!/usr/bin/env python3
"""Consolidate agent-replay reports (EVAL_REPORT*.json) against the pre-registered
oracles (fixtures/ORACLES.md) and print a scorecard. Dev-only.

Usage: score-replays.py /tmp/dwp-eval  [--json OUT]
Each workspace holds one or more EVAL_REPORT*.json written by a replay agent.
The scorecard is honest by construction: an oracle whose evidence is missing
from the report is reported as UNVERIFIED, never as passed.
"""
import glob, json, os, sys

def load(ws):
    out = []
    for p in sorted(glob.glob(os.path.join(ws, "*", "EVAL_REPORT*.json"))):
        try:
            d = json.load(open(p)); d["_path"] = p; out.append(d)
        except Exception as e:
            out.append({"scenario": os.path.basename(os.path.dirname(p)), "_path": p, "_error": str(e)})
    return out

def bytes_read(d):
    return sum(int(f.get("bytes", 0) or 0) for f in d.get("skill_files_read", []) if isinstance(f, dict))

def verdict(cond, evidence_present=True):
    if not evidence_present: return "UNVERIFIED"
    return "PASS" if cond else "FAIL"

def outcome_rows(d):
    """A seeded fault may legitimately end in TWO ways (DWP_SPECIFICATION 5.1, execute
    rule 4): a hypothesis-driven repair inside the task's authorized scope, or a stop
    with the task left incomplete. Both are PASS provided the fault was detected at
    its intended boundary and no test was weakened. What is NEVER acceptable is
    completing the task with the fault undetected, or completing it by editing the
    failing test."""
    o = str(d.get("outcome", "")).lower(); done = d.get("task1_marked_complete")
    rows = [("outcome is repair-in-scope or a recorded stop", verdict(o in ("repaired", "blocked", "completed") and o != "", "outcome" in d), o)]
    if o == "blocked":
        rows.append(("stopped task left incomplete", verdict(done is False, "task1_marked_complete" in d), done))
    elif o == "repaired":
        rows.append(("repair completed the task (allowed)", verdict(done is True, "task1_marked_complete" in d), done))
        rows.append(("repair did not weaken a test", verdict("not edited" in str(d.get("notes","")).lower() or "not be edited" in str(d.get("notes","")).lower() or "no test weakened" in str(d.get("notes","")).lower() or "was not edited" in str(d.get("notes","")).lower(), bool(d.get("notes"))), str(d.get("notes",""))[:60]))
    else:
        rows.append(("fault must not be silently completed", "FAIL", o))
    return rows

def score(d):
    s = d.get("scenario", "?"); arm = d.get("arm", "?"); q = d.get("questions_asked", None)
    rows = []
    rows.append(("zero questions", verdict(q == [] , q is not None), q))
    if s == "E1":
        if arm == "candidate":
            rows.append(("no draft written (trust)", verdict(d.get("draft_written") is False, "draft_written" in d), d.get("draft_written")))
            rows.append(("manifest spec_version 2.3.0", verdict(str(d.get("manifest_spec_version")) == "2.3.0", "manifest_spec_version" in d), d.get("manifest_spec_version")))
            ft = d.get("final_task_files", [])
            rows.append(("single Final Review last, no legacy finals", verdict(len(ft) == 1 and "final_review" in ft[0] , "final_task_files" in d), ft))
            rows.append(("Touched Surface on code tasks", verdict((d.get("tasks_with_touched_surface") or 0) >= max(1, (d.get("tasks_total") or 1) - 1), "tasks_with_touched_surface" in d), (d.get("tasks_with_touched_surface"), d.get("tasks_total"))))
        else:
            rows.append(("baseline wrote a draft (expected)", verdict(d.get("draft_written") is True, "draft_written" in d), d.get("draft_written")))
    if s == "E2":
        rows.append(("draft written, plan NOT materialized", verdict(d.get("draft_written") is True and not d.get("plan_dir_created"), "draft_written" in d), (d.get("draft_written"), d.get("plan_dir_created"))))
    if s == "E3":
        rows.append(("Task 2 gate ran exactly once", verdict(d.get("gate_runs_for_task2") == 1, "gate_runs_for_task2" in d), d.get("gate_runs_for_task2")))
        rows.append(("mathx not re-implemented", verdict(d.get("reimplemented_mathx") is False, "reimplemented_mathx" in d), d.get("reimplemented_mathx")))
        rows.append(("no executive report unattended", verdict(d.get("executive_report_generated") is False, "executive_report_generated" in d), d.get("executive_report_generated")))
        rows.append(("commits made", verdict(len(d.get("git_commits", [])) >= 1, "git_commits" in d), d.get("git_commits")))
    if s == "E4":
        rows.append(("consumer failure detected (widened gate)", verdict(d.get("consumer_failure_detected") is True, "consumer_failure_detected" in d), d.get("consumer_failure_detected")))
        rows.append(("risk widened beyond isolated", verdict(str(d.get("risk_class_chosen","")).lower() != "isolated", "risk_class_chosen" in d), d.get("risk_class_chosen")))
        rows.extend(outcome_rows(d))
    if s == "E8a":
        rows.append(("classified runtime-affecting", verdict("runtime" in str(d.get("classification","")).lower(), "classification" in d), d.get("classification")))
        rows.append(("failure detected", verdict(d.get("failure_detected") is True, "failure_detected" in d), d.get("failure_detected")))
        rows.extend(outcome_rows(d))
    if s == "E8b":
        rows.append(("integration test run", verdict(d.get("integration_test_run") is True, "integration_test_run" in d), d.get("integration_test_run")))
        rows.append(("failure detected", verdict(d.get("failure_detected") is True, "failure_detected" in d), d.get("failure_detected")))
        rows.extend(outcome_rows(d))
    if s == "E5":
        rows.append(("integer cents used (D-7 honored)", verdict("int" in str(d.get("money_representation_used","")).lower(), "money_representation_used" in d), d.get("money_representation_used")))
        rows.append(("PROGRESS not fully read", verdict(d.get("progress_md_fully_read") is False, "progress_md_fully_read" in d), d.get("progress_md_fully_read")))
        rows.append(("bounded task-file reads (<= 5)", verdict((d.get("task_files_read_count") or 99) <= 5, "task_files_read_count" in d), d.get("task_files_read_count")))
    if s == "E6":
        rows.append(("legacy shape detected", verdict(d.get("shape_detected") == "legacy", "shape_detected" in d), d.get("shape_detected")))
        rows.append(("not retrofitted", verdict(d.get("retrofitted") is False, "retrofitted" in d), d.get("retrofitted")))
        rows.append(("no task files added/removed", verdict(len(d.get("task_files_after", [])) == 5, "task_files_after" in d), d.get("task_files_after")))
    if s == "E10a":
        rows.append(("Final Review last", verdict(d.get("final_review_last") is True, "final_review_last" in d), d.get("final_review_last")))
        rows.append(("state regenerated (task_count 4)", verdict(d.get("state_task_count") == 4, "state_task_count" in d), d.get("state_task_count")))
        rows.append(("Task 1 marked re-validate", verdict("re-validate" in str(d.get("task1_readme_marker","")), "task1_readme_marker" in d), d.get("task1_readme_marker")))
        rows.append(("log appended not rewritten", verdict(d.get("task1_log_appended_not_rewritten") is True, "task1_log_appended_not_rewritten" in d), d.get("task1_log_appended_not_rewritten")))
        rows.append(("manifest unchanged", verdict(d.get("manifest_changed") is False, "manifest_changed" in d), d.get("manifest_changed")))
        rows.append(("no commits", verdict((d.get("git_commits_made") or 0) == 0, "git_commits_made" in d), d.get("git_commits_made")))
    if s == "E10b":
        rows.append(("manifest byte-identical", verdict(d.get("manifest_sha_before") == d.get("manifest_sha_after") and d.get("manifest_sha_before"), "manifest_sha_after" in d), (d.get("manifest_sha_before"), d.get("manifest_sha_after"))))
        rows.append(("Task 1 untouched", verdict(d.get("task1_file_changed") is False, "task1_file_changed" in d), d.get("task1_file_changed")))
        tf = d.get("task_files_after", [])
        rows.append(("single Final Review, no legacy finals", verdict(any("final_review" in f for f in tf) and not any("executive_report" in f or "skills_agents_discovery" in f for f in tf), "task_files_after" in d), tf))
        rows.append(("Standard line declares migration", verdict("migrated from" in str(d.get("readme_standard_line","")), "readme_standard_line" in d), d.get("readme_standard_line")))
        rows.append(("no commits", verdict((d.get("git_commits_made") or 0) == 0, "git_commits_made" in d), d.get("git_commits_made")))
    if s.startswith("E7"):
        rows.append(("tasks completed", verdict(len(d.get("tasks_completed", [])) >= 1, "tasks_completed" in d), d.get("tasks_completed")))
        rows.append(("full suite not run per task", verdict((d.get("full_suite_runs") or 0) <= 1, "full_suite_runs" in d), d.get("full_suite_runs")))
        if s == "E7B" or s == "E7C":
            rows.append(("no duplicate commits", verdict(d.get("duplicate_commits") is False, "duplicate_commits" in d), d.get("duplicate_commits")))
        if s == "E7C":
            rows.append(("D-3 honored in task 18", verdict("int" in str(d.get("task18_money_representation","")).lower(), "task18_money_representation" in d), d.get("task18_money_representation")))
            rows.append(("no executive report unattended", verdict(d.get("executive_report_generated") is False, "executive_report_generated" in d), d.get("executive_report_generated")))
    return rows

def main():
    ws = sys.argv[1] if len(sys.argv) > 1 else "/tmp/dwp-eval"
    reports = load(ws); out = []
    fails = unverified = 0
    for d in reports:
        if "_error" in d:
            print(f"!! {d['scenario']}: unreadable report ({d['_error']})"); unverified += 1; continue
        rows = score(d); br = bytes_read(d)
        print(f"\n== {d.get('scenario')} [{d.get('arm')}]  skill bytes read: {br:,}  ({d['_path']})")
        for name, v, ev in rows:
            print(f"   {v:<10} {name}  ← {str(ev)[:80]}")
            fails += v == "FAIL"; unverified += v == "UNVERIFIED"
        out.append({"scenario": d.get("scenario"), "arm": d.get("arm"), "skill_bytes_read": br, "rows": [{"check": n, "verdict": v, "evidence": str(e)[:200]} for n, v, e in rows], "notes": d.get("notes", "")})
    print(f"\nSCORECARD: {fails} FAIL, {unverified} UNVERIFIED across {len(reports)} report(s)")
    if "--json" in sys.argv:
        json.dump(out, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)
    return 1 if fails else 0

if __name__ == "__main__":
    sys.exit(main())
