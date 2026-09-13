# v5 reliability closure — evidence record

Public, sanitized evidence for the v5 reliability closure work: what was
measured, against which revisions, and what each number may and may not be
used to claim. It **adds to** the evaluation history in
[`../EVALUATION.md`](../EVALUATION.md); it rewrites none of the earlier
records, which keep their own scope and limits.

Sections are appended by the task that produced them. Every number below is
reproducible from the commands it names.

## Standing limits, stated plainly

- **No live-agent superiority claim.** Nothing here compares DWP against
  another methodology, another version's live behavior, or a no-DWP baseline.
  No paired live-token, latency, cost or quality experiment backs this record.
- **Bytes are filesystem bytes.** The `/4` column in the measurement script is
  a labeled estimate of tokens, never a measurement. No monetary figure
  follows.
- **Static contracts are not model behavior.** A test over instruction text
  proves the contract is taught. Whether a model obeys it is live evidence,
  recorded per harness in [`../COMPATIBILITY.md`](../COMPATIBILITY.md).

## Instruction accounting

**Baseline:** `6bf7830` (the v5.2.0 release, the revision this closure branched
from). **Candidate:** the closure branch head. **Command:**

```bash
bash tests/efficiency/measure-instruction-load.sh
```

### What is measured, and what changed

Two distinct numbers are now published, because one was being read as the
other:

- the **entry bundle** — what a flow loads at t0 (the router plus the flow's
  own contract plus anything its essential tier links); and
- the **end-to-end path** — the entry bundle plus every companion the named
  triggers of a realistic path actually load, counted once per unique file,
  with files read at two moments disclosed separately.

The named paths, their phases and their triggers are declared in
[`../../tests/efficiency/paths.tsv`](../../tests/efficiency/paths.tsv) and
checked by `bats tests/context-accounting.bats`, which fails if the manifest
names a file the pack does not have, or one the flow's own read contract does
not declare.

### Entry bundle per flow (filesystem bytes)

| Flow | `6bf7830` | closure branch | change |
|---|---:|---:|---:|
| create | 98,609 | 68,021 | **−31.0 %** |
| execute | 46,137 | 49,161 | +6.6 % |
| resume | 25,841 | 29,688 | +14.9 % |
| refine | 61,002 | 67,622 | +10.9 % |
| onboard | 68,480 | 74,655 | +9.0 % |
| status | 18,597 | 21,861 | +17.6 % |
| verify | 26,720 | 30,280 | +13.3 % |

**The create reduction is a real path change, not a relabel.** Three files
left the compulsory set because the path that needed them changed, not because
the label did:

| File | Bytes | Why it is no longer compulsory |
|---|---:|---|
| `guide/authoring.md` | 26,521 | §4–§5 are the Full task-file anatomy, reached only at Step 4.4; the Lite-first path writes its shape inline and Step 3.6 states the test/security/documentation discipline inline. A Lite creation never reaches a trigger for this file. |
| `examples/CREATE_PLAN.md` | 6,998 | A copy-paste catalogue of prompt phrasings for the **developer**. Composing a plan takes its input from Steps 1–3; no workflow step reads it. |
| `shared/dwp-paths.md` | 4,377 | Step 4.0 already inlines `.dwp/plans/PLAN_{name}/`; the file is needed only for a `DWP_DIR` override or an unlocatable folder — the same trigger `execute` and `resume` already use. |

Two companions that *do* fire on every create — `create/addon-augmentations.md`
and `guide/execution.md` §6.1, both reached while composing the Final Review —
were **not** moved out of sight. They sit in the conditional tier with their
trigger marked as always-firing, and both measured create paths count them, so
the published end-to-end number includes what the entry number does not.

**Guard cost — what the reliability work added.** Every other flow's entry
bundle grew, and the growth is the price of the guarantees Tasks 2–6 added, in
already-read files:

| File | Bytes added | What it buys |
|---|---:|---|
| `create/SKILL.md` | +2,973 | the tiered read contract itself (it replaced a flat list) |
| `onboard/SKILL.md` | +2,911 | the intent-to-flow routing block and its Phase 8 verification |
| `resume/SKILL.md` | +2,624 | checker-driven reconciliation, the transfer/persistence contract |
| `refine/SKILL.md` | +2,285 | amendment records and evidence invalidation (3.7) |
| `execute/SKILL.md` | +1,801 | guarded closure order, the completion transaction, evidence rules |
| `SKILL.md` (router) | +1,223 | activation rules; paid by all seven flows |
| `verify/SKILL.md` | +296 | log-pointer and non-execution checks |

New runtime helpers (`shared/state_contract.py` 9,947 B,
`shared/finalize_plan.py` 5,748 B, `shared/update-state.py` +4,290 B) are
executed, not read as instructions, so they add nothing to any bundle.

**Disclosed risk:** the resume entry bundle is 29,688 B against the 30,000 B
bound pinned by `tests/resume-read-contract.bats` — 312 B of headroom. The
bound was **not** raised to accommodate the guard cost; the next change to the
resume flow must find room inside it or argue the bound up on its own merits.

### End-to-end paths (unique pack files, closure branch)

| Path | entry B | path B | vs entry | files | phases |
|---|---:|---:|---:|---:|---:|
| create-lite | 68,021 | 92,207 | 1.36× | 6 | 2 |
| create-full | 68,021 | 124,801 | 1.83× | 8 | 4 |
| execute-final-review | 49,161 | 148,678 | 3.02× | 7 | 4 |
| resume-assessment | 29,688 | 29,688 | 1.00× | 2 | 1 |
| resume-execution | 29,688 | 141,195 | 4.76× | 7 | 4 |
| conditional-escalation | 49,161 | 217,442 | 4.42× | 13 | 9 |

This table is the point of the change. A resume that goes on to execute loads
about **4.8×** its entry bundle, and an orchestrator plan with team agents that
hits an inconsistent state loads about **4.4×**. Publishing only the entry
column invited the reading that a flow's instruction cost was its t0 read; it
never was.

`guide/authoring.md` is read at two distinct moments on `create-full`
(discipline judgment, then Full expansion) and on `conditional-escalation`
(discipline, then gate widening). It is counted once in each path total and
listed under the script's "Repeated reads" section.

### What these numbers do not establish

- **Not a cap on a run.** Neither column bounds the context a real session
  consumes. Both exclude the repository's own files (`AGENTS.md`,
  `docs/TESTING_GUIDE.md`, the source under review, the plan folder), tool
  output, the plan files a flow writes and re-reads, re-reads after a
  compaction or handoff, the agent's own output, and anything the host injects.
  In a real run those dominate.
- **Not a live-session saving.** A smaller entry bundle is a smaller starting
  read. Converting that into tokens, money or wall-clock requires provider
  counters this repository does not have; see
  [`token-efficiency.md`](token-efficiency.md) for why the earlier attempt at
  that comparison is recorded as incomplete rather than as a result.
- **Not a competition.** No v2, no other methodology and no "quality
  percentage" appears here, by design.

### Reproduce

```bash
bash tests/efficiency/measure-instruction-load.sh      # both measurements
bats tests/context-accounting.bats                     # the accounting contract
bats tests/execute-read-contract.bats tests/resume-read-contract.bats
```

For the baseline column, export the tagged tree and run that revision's own
script against it — an export's provenance is the revision it came from, not
the checkout that produced it:

```bash
EXP=$(mktemp -d)
git archive 6bf7830 skills/deepworkplan tests/efficiency | tar -x -C "$EXP"
bash "$EXP/tests/efficiency/measure-instruction-load.sh" "$EXP"
```
