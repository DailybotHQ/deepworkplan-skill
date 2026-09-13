#!/usr/bin/env bats

# Interruption-recovery and workspace-persistence regressions (plan Task 5).
# Behavioral oracles run the real context.sh, the real guarded writer and the
# real read-only checker against hostile-but-valid paths, fresh clones without
# ignored data, transferred artifacts and dangling evidence pointers. The
# final test is a labeled contract-presence check — it proves the flows teach
# the contract, not agent behavior.

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    WORK="$(mktemp -d)"
}

teardown() { rm -rf "$WORK"; }

@test "context.sh emits valid JSON for hostile-but-valid paths and DWP_DIR" {
  HOSTILE="$WORK"'/wei rd "q" (b)&$z\back'
  mkdir -p "$HOSTILE"
  git -C "$HOSTILE" init -q
  git -C "$HOSTILE" -c user.email=t@t -c user.name=t commit -q --allow-empty -m init
  DWP="$WORK"'/dwp dir "x"\y'
  run bash -c 'cd "$1" && DWP_DIR="$2" bash "$3/skills/deepworkplan/shared/context.sh"' \
      _ "$HOSTILE" "$DWP" "$REPO_ROOT"
  [ "$status" -eq 0 ]
  EXPECT_ROOT="$HOSTILE" EXPECT_DWP="$DWP" EXPECT_REPO='wei rd "q" (b)&$z\back' \
      python3 -c '
import json, os, sys
o = json.load(sys.stdin)
assert o["repo_root"] == os.environ["EXPECT_ROOT"], o
assert o["dwp_dir"] == os.environ["EXPECT_DWP"], o
assert o["repo"] == os.environ["EXPECT_REPO"], o
assert o["branch"] in ("master", "main"), o
print("hostile repo_root, dwp_dir and repo name round-trip through valid JSON")
' <<<"$output"
  # Outside a git work tree the same escaping holds and branch degrades.
  run bash -c 'cd "$1" && DWP_DIR="$2" bash "$3/skills/deepworkplan/shared/context.sh"' \
      _ "$WORK" "$DWP" "$REPO_ROOT"
  [ "$status" -eq 0 ]
  EXPECT_DWP="$DWP" python3 -c '
import json, os, sys
o = json.load(sys.stdin)
assert o["dwp_dir"] == os.environ["EXPECT_DWP"], o
assert o["branch"] == "unknown", o
print("outside git: branch unknown, escaped dwp_dir intact")
' <<<"$output"
}

@test "a fresh clone without .dwp reports missing data; a complete transfer verifies" {
  run python3 - "$REPO_ROOT" "$WORK" <<'PY'
import json, pathlib, shutil, subprocess, sys, tempfile
sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(sys.argv[1])/'tests'))
from completion_test import ready_plan
checker = str(pathlib.Path(sys.argv[1])/'skills/deepworkplan/verify/plan_contract.py')
work = pathlib.Path(sys.argv[2])
# A repository whose .dwp/ holds a complete, conformant plan...
src = work/'repo-src'
src.mkdir()
(src/'.gitignore').write_text('.dwp/\n')
subprocess.run(['git','init','-q','.'],cwd=src,check=True)
subprocess.run(['git','-C',str(src),'-c','user.email=t@t','-c','user.name=t',
                'add','.gitignore'],check=True)
subprocess.run(['git','-C',str(src),'-c','user.email=t@t','-c','user.name=t',
                'commit','-qm','init'],check=True)
plan, candidate = ready_plan(src/'.dwp/plans')
(plan/'state.json').write_text(json.dumps(candidate))
assert subprocess.run(['python3',checker,str(plan)],capture_output=True).returncode == 0
# ...clones without it: the clone has nothing to resume and must say so.
clone = work/'repo-clone'
subprocess.run(['git','clone','-q',str(src),str(clone)],check=True)
assert not (clone/'.dwp').exists()
x = subprocess.run(['python3',checker,str(clone/'.dwp/plans/PLAN_lite_fixture')],
                   capture_output=True,text=True)
assert x.returncode == 1, x.stdout
assert 'no README.md' in x.stdout, x.stdout
# The complete transferred workspace (whole plan folder, same relative path)
# verifies under the recorded contract.
dest = clone/'.dwp/plans/PLAN_lite_fixture'
dest.parent.mkdir(parents=True)
shutil.copytree(plan, dest)
x = subprocess.run(['python3',checker,str(dest)],capture_output=True,text=True)
assert x.returncode == 0, x.stdout
print('fresh clone reports missing recovery data; complete transfer verifies')
PY
  [ "$status" -eq 0 ]
}

@test "a dangling or escaping log= pointer is refused by writer and checker" {
  run python3 - "$REPO_ROOT" "$WORK" <<'PY'
import json, pathlib, subprocess, sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(sys.argv[1])/'tests'))
from completion_test import ready_plan
root = pathlib.Path(sys.argv[1])
writer = str(root/'skills/deepworkplan/shared/update-state.py')
checker = str(root/'skills/deepworkplan/verify/plan_contract.py')
# Writer: closing a task whose fresh gate cites a log that does not exist.
state = pathlib.Path(sys.argv[2])/'state.json'
state.write_bytes((root/'tests/fixtures/lite-plan/.dwp/plans/PLAN_lite_fixture/state.json').read_bytes())
before = state.read_bytes()
def run_writer(*args):
    return subprocess.run(['python3',writer,str(state),*args],capture_output=True,text=True)
x = run_writer('--task','1','--status','completed',
               '--gate','check-a|0|executed=1; log=analysis_results/gates/t1/gate.log')
assert x.returncode != 0 and 'must stay recoverable' in (x.stdout+x.stderr), x
assert state.read_bytes() == before  # the refused write changed nothing
# Checker: the same dangling pointer on a completed task is a finding...
plan, candidate = ready_plan(pathlib.Path(sys.argv[2]))
candidate['tasks'][0]['gates'][0]['evidence'] = 'executed=1/1; log=analysis_results/gates/missing.log'
(plan/'state.json').write_text(json.dumps(candidate))
x = subprocess.run(['python3',checker,str(plan)],capture_output=True,text=True)
assert x.returncode == 1 and 'must stay recoverable' in x.stdout, x.stdout
# ...a pointer escaping the plan folder is reported even when the target exists...
(plan/'../outside.log').write_text('x')
candidate['tasks'][0]['gates'][0]['evidence'] = 'executed=1/1; log=../outside.log'
(plan/'state.json').write_text(json.dumps(candidate))
x = subprocess.run(['python3',checker,str(plan)],capture_output=True,text=True)
assert x.returncode == 1 and 'outside the plan folder' in x.stdout, x.stdout
# ...and creating the cited artifact recovers the clean verdict.
candidate['tasks'][0]['gates'][0]['evidence'] = 'executed=1/1; log=analysis_results/gates/t1/gate.log'
(plan/'state.json').write_text(json.dumps(candidate))
(plan/'analysis_results/gates/t1').mkdir(parents=True, exist_ok=True)
(plan/'analysis_results/gates/t1/gate.log').write_text('recorded output')
x = subprocess.run(['python3',checker,str(plan)],capture_output=True,text=True)
assert x.returncode == 0, x.stdout
# Recovery for the writer too: with the log present the closure succeeds.
# The writer resolves log pointers against the state file's own folder.
p2 = pathlib.Path(sys.argv[2])/'p2'
(p2/'analysis_results/gates/t1').mkdir(parents=True)
(p2/'analysis_results/gates/t1/gate.log').write_text('recorded output')
state2 = p2/'state.json'
state2.write_bytes((root/'tests/fixtures/lite-plan/.dwp/plans/PLAN_lite_fixture/state.json').read_bytes())
x = subprocess.run(['python3',writer,str(state2),'--task','1','--status','completed',
                    '--gate','check-a|0|executed=1; log=analysis_results/gates/t1/gate.log'],
                   capture_output=True,text=True)
assert x.returncode == 0, x.stderr
print('dangling/escaping pointers refused by writer and checker; recovery by creating the artifact')
PY
  [ "$status" -eq 0 ]
}

@test "the state-replacement boundary is detected in both directions" {
  run python3 - "$REPO_ROOT" "$WORK" <<'PY'
import json, pathlib, subprocess, sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(sys.argv[1])/'tests'))
from completion_test import ready_plan
checker = str(pathlib.Path(sys.argv[1])/'skills/deepworkplan/verify/plan_contract.py')
plan, candidate = ready_plan(pathlib.Path(sys.argv[2]))
(plan/'state.json').write_text(json.dumps(candidate))
def check():
    return subprocess.run(['python3',checker,str(plan)],capture_output=True,text=True)
assert check().returncode == 0  # clean control
# Interrupted between Markdown and state.json: README says [x], state stale.
s = json.loads((plan/'state.json').read_text())
s['tasks'][0].update(status='pending')
s['tasks'][0].pop('completed_at', None)
s['status'], s['completed_count'] = 'in_progress', 1
(plan/'state.json').write_text(json.dumps(s))
x = check()
assert x.returncode == 1 and 'disagrees with README' in x.stdout, x.stdout
# Interrupted before the Markdown update: state completed, README still [ ].
plan, candidate = ready_plan(pathlib.Path(sys.argv[2])/'second')
(plan/'state.json').write_text(json.dumps(candidate))
(plan/'README.md').write_text((plan/'README.md').read_text().replace('[x] Task 1','[ ] Task 1',1))
x = check()
assert x.returncode == 1 and 'disagrees with README' in x.stdout, x.stdout
print('both markdown/state desync directions are reported')
PY
  [ "$status" -eq 0 ]
}

@test "contract presence (labeled): persistence, fingerprints, receipts, recovery" {
  pack="$REPO_ROOT/skills/deepworkplan"
  doc_has() { tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"; }
  # Resume: guarded lifecycle integration + persistence section, no doc link
  # after the never-by-default tier (the read contract forbids it).
  doc_has "$pack/resume/SKILL.md" "never lets a summary override"
  doc_has "$pack/resume/SKILL.md" "plan_contract.py"
  doc_has "$pack/resume/SKILL.md" "the recorded \`fp=\` still matches the world"
  doc_has "$pack/resume/SKILL.md" ".finalizing.json"
  doc_has "$pack/resume/SKILL.md" "--recover"
  doc_has "$pack/resume/SKILL.md" "No daemon, auto-upload, or automatic unignoring"
  doc_has "$pack/resume/SKILL.md" "The minimum handoff manifest: the complete plan folder"
  doc_has "$pack/resume/SKILL.md" "a missing receipt is investigated"
  if tail -n +$(( $(grep -n '^- \*\*Never by default' "$pack/resume/SKILL.md" | cut -d: -f1) )) \
      "$pack/resume/SKILL.md" | grep -q '](' ; then
    echo "a markdown link appears after the never-by-default tier:"
    tail -n +$(( $(grep -n '^- \*\*Never by default' "$pack/resume/SKILL.md" | cut -d: -f1) )) \
      "$pack/resume/SKILL.md" | grep -n ']('
    return 1
  fi
  # dwp-paths: the normative transfer procedure and missing-artifact behavior.
  doc_has "$pack/shared/dwp-paths.md" "Workspace persistence and transfer"
  doc_has "$pack/shared/dwp-paths.md" "carries no plan data"
  doc_has "$pack/shared/dwp-paths.md" "minimum handoff"
  doc_has "$pack/shared/dwp-paths.md" "no daemon, no auto-upload"
  # Specs and guide teach the same contract.
  doc_has "$pack/spec/PLAN_STATE.md" "Evidence reuse requires an unchanged world"
  doc_has "$pack/spec/PLAN_STATE.md" "External-action receipts"
  doc_has "$pack/spec/AGENT_PROTOCOL.md" "report missing recovery data and halt"
  doc_has "$pack/guide/prompts.md" "9.6. Resuming on a New Machine or After a Fresh Clone"
  doc_has "$pack/guide/prompts.md" "minimum handoff manifest"
}
