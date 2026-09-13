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

**The resume bound, and what happened to it.** At the close of the instruction
accounting work the resume entry bundle sat at 29,688 B against the 30,000 B
bound in `tests/resume-read-contract.bats` — 312 B of headroom — and the record
said the next change must find room inside it or argue the bound up on its own
merits. The acceptance runs then required two operative additions to that flow.
So the argument was made, in the open: every byte of duplication the file still
carried was extracted first (a restated Important Notes bullet, trust-boundary
rules stated twice, a tier enumeration repeating the Workflow headings, and a
line of contributor test guidance that belonged in the testing guide),
recovering **1,275 B**. What remained was substance. The bound was then raised
once, to 31,000 B, with the reasoning written into the test itself. The
headroom stays deliberately small: the bound exists to trip when a whole
companion (~19–38 KB) is re-linked as compulsory, and it still does.

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

## Claims, mechanisms and evidence

Every active reliability claim this skill makes, the mechanism that implements
it, and the **kind** of evidence behind it. The kinds are not interchangeable:

- **Implemented behavior** — a runtime helper or flow rule that executes.
- **Automated evidence** — a test that runs in CI over real artifacts.
- **Contract presence** — a test that asserts the instruction text teaches a
  rule. It proves the contract is taught; it is *never* evidence that a model
  obeys it.
- **Observed agent behavior** — a recorded live run, per harness.
- **Limitation** — the boundary the claim does not cross.

"Unknown" is never listed as supported. Where a row's strongest evidence is
contract presence, the row says so.

| Claim | Mechanism | Evidence | Kind | Limitation |
|---|---|---|---|---|
| A plan's state cannot silently contradict its Markdown | `shared/state_contract.py` guards the writer; the checker refuses contradictory transitions | `bats tests/state-transitions.bats tests/state-evidence.bats tests/state-updater.bats` | Implemented + automated | Guards the writer and the checker. An agent that hand-edits `state.json` with an editor bypasses both; the README remains the authority that exposes it |
| A task cannot be marked complete on evidence that admits non-execution | Five evidence states; `NON_EXECUTION` / `invalidated` rules in `state_contract.py` | `bats tests/scope-evidence.bats` (sanitized from the historical false-completion case) | Implemented + automated | Detects contradictions it can read — a gate record that lies about a command it never ran is caught, a command that ran and reported a false result is not |
| Plan completion is a recoverable transaction, not a status flip | `shared/finalize_plan.py` publish/recover with a `FINALIZATION.json` receipt and a `.finalizing.json` failure marker | `bats tests/completion-transaction.bats`, incl. before/after-publication fault injection | Implemented + automated | Covers interruption between publication steps. A filesystem that reorders or loses a completed `rename` is out of scope |
| Evidence pointers stay resolvable after a handoff | `log=` pointers are validated at the guarded writer **and** the read-only checker; dangling or escaping paths are refused | `bats tests/resume-integrity.bats` (hostile paths, fresh clone without the gitignored `.dwp/`) | Implemented + automated | Validates the pointer, not the content it points at |
| An interrupted plan resumes at its exact interruption boundary | The resume protocol's boundary table, checker-driven reconciliation, the smoke test | `bats tests/resume-integrity.bats` + `bats tests/resume-read-contract.bats`; the boundary table itself is contract presence | Implemented + **contract presence** for the classification step | The table tells the agent which single step is missing; whether a given model classifies correctly is observed behavior, not proven here |
| Any agent can activate the flows from a repository's own kit | `onboard` Phase 3 installs the intent-to-flow routing block and the `dwp-*` delegators; Phase 8 verifies them | `bats tests/activation-contract.bats` — oracles over the real generated kit; the intent-mapping cases are labeled contract presence | Implemented + automated (artifacts) + **contract presence** (routing) | Not evidence that a model routes a fresh request reliably. Live routing evidence is recorded per harness in [`../COMPATIBILITY.md`](../COMPATIBILITY.md) |
| A plan written by one agent resumes correctly in another | The plan folder is the whole handoff artifact — nothing required lives only in a conversation | [`cross-agent-handoff.md`](cross-agent-handoff.md) — bidirectional Claude Code ↔ Codex CLI | **Observed agent behavior** | Two harnesses. The other supported agents have installation coverage only |
| The instruction surface is measured honestly | Entry bundle and end-to-end paths measured separately, with repeats, triggers and exclusions published | `bash tests/efficiency/measure-instruction-load.sh` + `bats tests/context-accounting.bats` | Implemented + automated | Filesystem bytes of pack files. **Not a cap on a run**, not tokens, not a live-session saving |
| The documented claims match the shipped pack | Version stamps, helper inventory, sub-skill count and absolute-claim wording are pinned to the filesystem | `bats tests/claims-consistency.bats` (counts derived from the tree, never hardcoded prose) | Automated | Catches drift in the specific statements it pins. It cannot judge whether a new claim is true |
| The core methodology makes no network calls | No runtime helper opens a socket; onboarding Phase 7a's pinned install is the single consent-gated exception | The runnable self-audit in [`../../skills/deepworkplan/TRUST.md`](../../skills/deepworkplan/TRUST.md) | Implemented + automated (self-audit) | Covers the shipped pack. What *your* agent harness does over the network is outside this skill's control |

### Claims deliberately not made

- No comparison against v2, another methodology, or a no-DWP baseline.
- No "quality percentage", completion rate, or "works with any model".
- No token, billing or latency saving — the one attempt at a paired live
  comparison is recorded as **incomplete** in
  [`token-efficiency.md`](token-efficiency.md) rather than as a result.
- No claim that a plan cannot fail. The guarantees are about what the
  repository records and recovers, not about model infallibility.

## Behavioral acceptance — the v5 lifecycle driven by fresh agents

**Protocol:** [`../../tests/reliability/PROTOCOL.md`](../../tests/reliability/PROTOCOL.md),
written and committed **before** the first run. **Oracles:** A1–A8, scored from
the run's artifacts by
[`../../tests/reliability/oracles/score-acceptance.py`](../../tests/reliability/oracles/score-acceptance.py),
never from the agent's narration. **Evidence:**
[`../../tests/reliability/evidence/`](../../tests/reliability/evidence/), one
sanitized file per run.

### What ran

Five live runs across three rounds, each a fresh agent context with no
conversation carryover, each in a disposable workspace, each entering the flows
by name (reading `SKILL.md` and routing from it — the documented fallback for
hosts without slash commands).

| Run | Round | Flow | Verdict |
|---|---|---|---|
| L1 | 1 | clean Lite lifecycle | **PASS** (8/8) |
| L2 | 1 | Full lifecycle, interrupted, resumed by a second agent | **PASS** (8/8) |
| R2-L1 | 2 | clean Lite lifecycle | **PASS** (8/8) |
| R2-L2 | 2 | Full lifecycle, interrupted, resumed | **FAIL** — A6, no publication receipt |
| R3-L2 | 3 | Full lifecycle, interrupted, resumed | **PASS** (8/8) |

Two oracles carry most of the weight. **A3** calls the fixed code and requires
an overdrawing transfer to raise *and record nothing*. **A4** reverts the run's
own fix and requires its own suite to fail, then restores it and requires a
pass — a test that passes either way is not coverage. Neither can be satisfied
by text.

### The R2-L2 failure, and why it is recorded rather than amended

R2-L2 produced a coherent, conformant terminal plan with **no**
`FINALIZATION.json`: it was closed by hand because the guarded publication
crashed. The cause was a function-local `import re` in
`finalize_plan.validate()` shadowing the module-level one for the whole
function. Lite plans took the branch that bound it; a **Full** plan — every
locator `kind: "file"` — never did, so guarded publication was unreachable for
Full plans entirely. It had a perverse signature: *correct* artifacts caused the
crash, because a task whose log was unreadable took an earlier branch and never
reached the `re` call.

That defect was introduced **by this plan's own work**, in the fix for a
separate false-refusal defect. Every deterministic lifecycle scenario passed
throughout, because they all used Lite plans — representation was a dimension
the suite did not cover. Scenario **F12** now covers it: a Full plan published
end to end, plus a static AST guard over every shipped helper that fails on any
function-local import shadowing a module-level one.

The resuming agent's conduct is the reason this was recoverable: it refused to
hand-write a receipt, on the stated grounds that `"result": "verified"` would
assert a verification that never happened. It recorded the absence instead.

The run is published as **FAIL**. The fix came afterwards; amending the record
would erase the only evidence that the failure mode is real.

### What the runs found

Thirteen product defects, none of which the static suites could see. A
representative sample:

| Defect | Found by | Why static tests missed it |
|---|---|---|
| A Full plan authored exactly as the canonical template documents could not pass the pack's own guarded finalization — and the error blamed the task's log, which was complete | L2 | The template and the parser were each internally consistent; only using both together exposed it |
| Guarded publication unreachable for every Full plan (the shadowed import above) | R2-L2 | Every scenario used Lite plans |
| A completed plan refused publication because its log contained the word "appending" — a substring test for "pending" — with a message that was false about the file | R2-L1 | Needs a real log written in the workload's own domain vocabulary |
| The router told an unattended run to *offer* a harness upgrade — the confirmation `trust` exists to remove | L2 | A branch no test exercised with an unattended request |
| A repository with `AGENTS.md` but no `.agents/` matched neither router branch | L1 | Both documented branches are internally consistent; the gap is between them |
| `create` declared the target's `docs/TESTING_GUIDE.md` compulsory with no rule for its absence | L1 | Introduced by this plan's own instruction-accounting work, one task earlier |
| "read §6.1" addressed a `##` heading; extracting `### 6.1` reads **empty** and exits **zero** | R3-L2a | A silent no-read produces no error to assert on |
| The `--checkpoint-step done` literal the terminal transition requires appeared in no flow — only in the spec the execute tier does not load for a close | R3-L2 | The refusal names the requirement; nothing named the accepted form |

Each is fixed with a regression that derives its expectation from the shipped
artifacts rather than from a copy of the same sentence. Two findings were
**not** accepted: three separate runs attributed a `__pycache__` inside the pack
to the shipped flows, and reproduction showed the flows write nothing (their own
diagnostic imports did) — the guarantee is now pinned by **F11** instead of a
phantom being "fixed"; and one report proposed widening an `except` clause,
which would have *hidden* the shadowed-import crash rather than surfacing it.

### Limitations — read these before citing anything above

- **No round ran against a frozen candidate.** Fixes from each round's own
  findings landed while later sessions were running. Every run's `META.json`
  records its real tree state, and two claims of "frozen" were corrected after
  a run reported pack files changing mid-session. This is a limitation of the
  protocol as executed, not a detail.
- **One host, one model family.** Fresh contexts on the available host are
  genuinely fresh, but two processes of the same host are **not** cross-vendor
  evidence and are never labelled as such. Cross-vendor evidence remains the
  separate record in [`cross-agent-handoff.md`](cross-agent-handoff.md).
- **One small workload.** Nothing here generalizes to a large repository, a
  costly suite, or a long-history plan.
- **A pass is an existence proof, not a rate.** These runs show the lifecycle
  can be driven correctly from the repository alone. They do not establish how
  often an arbitrary model does so, and no percentage may be derived from them.
- **No timing claims.** The runs shared a host with other work.
- **The defect rate did not reach zero.** Round 1 found five defects, round 2
  found seven, round 3 found three. The honest conclusion is not that the
  lifecycle is now proven correct — it is that **fresh-context runs are a
  productive detection channel that static suites do not replace**. Not one of
  these thirteen defects was visible to a suite that was passing 380 cases.

## Reproducing all of this

Everything in this record reproduces from a clean checkout with no secret, no
credential and no network access. Contributor tools only: Bats, ShellCheck, and
two test-only Python packages.

```bash
pip install jsonschema pyyaml          # test-only; the shipped helpers use the stdlib
bats tests/                            # the whole suite, including every contract below
```

Per guarantee, if you want to check one at a time:

| Guarantee | Command |
|---|---|
| State transitions, evidence truth, scope amendments | `bats tests/state-transitions.bats tests/state-evidence.bats tests/scope-evidence.bats` |
| Completion is a recoverable transaction | `bats tests/completion-transaction.bats` |
| Interruption recovery and workspace transfer | `bats tests/resume-integrity.bats` |
| Flow activation and portability | `bats tests/activation-contract.bats` |
| Instruction accounting (entry bundle vs end-to-end paths) | `bash tests/efficiency/measure-instruction-load.sh` + `bats tests/context-accounting.bats` |
| Claims match the shipped tree | `bats tests/claims-consistency.bats` |
| The lifecycle end to end, with injected faults | `bats tests/reliability-acceptance.bats` |
| CI runs what it claims to run | `bats tests/ci-guarantees.bats` |
| The pack works installed alone | `bats tests/packaging-reliability.bats` |

The **live** acceptance runs are the one part that does not reproduce from a
command: they need fresh agent contexts and an isolated workspace, per
[`../../tests/reliability/PROTOCOL.md`](../../tests/reliability/PROTOCOL.md).
Their scored results ship in
[`../../tests/reliability/evidence/`](../../tests/reliability/evidence/) — five
files, four PASS and one FAIL, each recording the round it belongs to and the
real state of the tree it ran against. Re-score any of them with:

```bash
python3 tests/reliability/oracles/score-acceptance.py <run-dir>
```

### Distribution

Only `skills/deepworkplan/` reaches a user's disk. `bats
tests/packaging-reliability.bats` proves that is enough: it exports the pack to
a scratch directory with no `tests/`, `scripts/`, contributor docs or repository
checkout in sight, and runs the read-only checker, the guarded writer and the
completion transaction from there. It also asserts the pack carries no
contributor file, that no runtime helper references one, that nothing in the
runtime opens a network connection, that a missing Python interpreter produces
**UNVERIFIED** rather than a pass, that the published schema snapshots are
byte-unchanged, and that the contributor dogfood mirror is byte-identical to the
shipped pack.
