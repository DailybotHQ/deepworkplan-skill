# v6 guarantees — what is proven, taught, enforced or observed

Written by `PLAN_v6_verified_autonomy` Task 20. This document is the
published answer to "what does DWP v6 actually guarantee?". Its rule is
separation: every guarantee is labeled with **how it is backed**, and only
one of the four kinds below is called a guarantee in the strong sense.
It exists so that a reader never has to infer the backing of a claim from
its tone. The working evidence behind this matrix (gate logs, readiness
assessment) is recorded under the authoring plan's `analysis_results/` in
the repository's gitignored `.dwp/` working state; the suites named
throughout are the durable, reviewable half.

## The four kinds

| Kind | Backing | Arbiter | Holds where |
| --- | --- | --- | --- |
| **Deterministic invariant** | Fault injection and clean controls run against the shipped code (`tests/v6-*.bats`, `tests/packaging-reliability.bats`) | The journal, the refusal exit codes, and the reproduced artifact — never a model's narration | Anywhere Python 3.9+ (stdlib only) and bash run; proven from an exported pack with no contributor tree and no network |
| **Host-enforced control** | `shared/resources.py` negotiates a closed set of host abilities; the enforcement is the host's | The negotiated capability record and the journal's settlement events | Only on a host that declares the ability; an unstated ability is `false`, and a meterless limit is advisory with the missing ability named |
| **Taught instruction** | Prose contracts in the flow files (`execute/SKILL.md`, `create/SKILL.md`, `onboard/v6.md`, …), statically pinned by contract tests for presence, triggers and vocabulary | The contract test pins the text exists at its trigger; it does not pin that any model obeyed it | Wherever the skill is installed; compliance by a specific model in a specific run is **not** guaranteed — behavioral evidence lives in the recorded campaigns |
| **Empirical observation** | Preregistered campaigns under [`PROTOCOL.md`](PROTOCOL.md) (Q1–Q4), scored by calibrated oracles outside the actor | The preregistered estimand and its denominator | Nowhere as a guarantee: these are measured results with confidence bounds, and a target is never a result |

## The guarantee matrix

Eleven boundaries from
the local `.dwp/plans/PLAN_v6_verified_autonomy/analysis_results/ARCHITECTURE.md`,
each with its clean control and its injected counterexample, mapped to the
suite that pins it. Every row labeled *invariant* below is machine-checked;
a regression in the named behavior fails CI.

| Boundary | Clean control | Injected counterexample | Suite and case |
| --- | --- | --- | --- |
| Authorization | Approval-gated `task_start` dispatches under the cited contract | Start before approval; replayed start under an unapproved revision; an observation *claiming* approval | `v6-ledger` ("task_start before approval is refused…", "a replayed task_start under an unapproved revision is refused"); `v6-scheduler` ("no dispatch before the approval cites the live contract"); `v6-faults` ("a retrieved assertion cannot authorize: the approval canary") |
| Dependency scheduling | Ready task selected; satisfied prerequisite unlocks the next | Cycle refused before any policy; unmet prerequisite refuses `select`; overlapping in-progress work refused; starvation aging recorded | `v6-scheduler` ("a prerequisite cycle is refused…", "prerequisites: an unmet prerequisite refuses select", "surface serialization…", "starvation aging…") |
| Evidence validity | Equivalent input reuses cached evidence | Changed input re-runs; pre-restart evidence is stale after the window reopens; stale invariant evaluation stops dispatch | `v6-ledger` ("equivalent input reuses evidence…", "a restart reopens the evidence window…"); `v6-scheduler` ("a stale invariant evaluation…", "deferral disguised as completion…") |
| Test reality | A gate that runs records observed exit codes | Zero-test completion refused; a missing gate binary is a recorded failure, never a pass; a command that never runs records no event | `v6-ledger` ("completion with zero evidence is refused (zero-test control)", "a command that never runs records no event…"); `v6-lifecycle` ("a missing gate binary is a recorded failure…") |
| Completion | Completion earned from gate evidence under the started task | Narrative-only QA claim still refused; exhaustion observation never satisfies a criterion | `v6-ledger` ("observed evidence after task_start satisfies completion"); `v6-faults` ("a retrieved assertion cannot satisfy: the QA canary"); `v6-budget` ("an exhaustion observation never satisfies a criterion") |
| Recovery | Interrupted materialization resumes; a roll archives and continues; a cold second workspace rebuilds from the journal alone | Crash at each persisted transition; torn final line; post-roll continuation with evidence intact | `v6-lifecycle` ("an interrupted materialization resumes…"); `v6-ledger` ("a complete final event that lost only its newline is restored", "after a roll the plan continues…", "a torn tail is repaired…"); `v6-migration` ("a re-run of migrate mints no duplicate events; a resumed run finishes from any phase", "a cold second workspace recovers the plan from the journal alone") |
| Persistence | Idempotent replay; deterministic projection; state.json rebuilt byte-identically from the journal | Duplicate submission; a second writer refused by the cooperative lock; corrupt journal/state/contract/chain each refused by name, nothing minted | `v6-ledger` ("approval then task_start works; duplicate submission is idempotent", "the cooperative lock refuses a second writer"); `v6-faults` ("a corrupt journal middle line is labeled torn and costs its evidence", "a corrupt state.json is rebuilt byte-identically…", "a corrupt contract.json refuses by name and writes nothing", "a corrupt contracts/ chain member refuses by name") |
| Resource limits | Dispatch within a declared supported limit; journal-computed counters enforce with no host at all | Exhaustion holds dispatch and persists incomplete state; reserve the spend cannot fit flips the refusal; settlement exactly-once | `v6-budget` ("journal-computed counters enforce with no host at all", "exhaustion holds dispatch and an explicit recovery clears it", "a reserve the spent cannot fit flips the refusal", "settlement is exactly-once…") |
| Context | Per-task manifest with mandatory sections pruning cannot drop; deterministic, record-anchored derivation | An unattributable summary is stale by construction; changed inputs invalidate freshness; a missing touched file surfaces the miss; four quantities never collapse into one | `v6-context` ("pruning cannot drop the acceptance or authorization boundary", "an unattributable summary (no fingerprint) is stale by construction", "freshness: unchanged inputs are fresh, changed inputs invalidate", "a missing touched file widens discovery and surfaces the miss", "accounting keeps four quantities apart and missing means missing") |
| Compatibility | Historical v5 plans keep their recorded lifecycle; migration is explicit with preview, verified rollback | Silent conversion refused; cross-generation writes refused; rollback restores the v5 pair byte-identically | `v6-migration` (preview/migrate/rollback cases); `v6-lifecycle` ("a v5-generation manifest is refused and left untouched", "a v6 plan folder next to a v5 plan folder: no cross-generation writes") |
| Packaging | The exported pack alone runs the full lifecycle and self-tests | Missing interpreter degrades honestly (unverified, never pass); no network call from the runtime; hostile-but-valid paths run the lifecycle | `v6-faults` ("the exported pack alone runs the v6 lifecycle", "a hostile-but-valid repository root runs the full lifecycle", "the plan identifier grammar rejects hostile names…"); `packaging-reliability` ("a missing interpreter degrades honestly instead of passing", "the exported runtime makes no network call") |

### The injection boundary (instructions are data)

Beyond the eleven rows, `tests/v6-faults.bats` pins the boundary the matrix
exists to defend: **a retrieved assertion cannot authorize a state
transition.** Benign instruction-injection canaries planted in untrusted
repo content (a touched file, the plan README, an observation, a draft
contract field) stay data: the approval canary's claim lands as a recorded
observation while `task_start` still refuses; the QA canary's claim does not
satisfy the zero-test control; the poisoned file's imperative text gates
nothing and mints nothing — the journal holds exactly the authored events;
the injected `override_authority` field is refused at materialization as a
closed-schema violation. These are properties of the shipped writer, not
claims about any model's resistance to the same text.

### What CI does with this

`bats tests/` runs every suite named above on every push; the workflow
installs the suites' prerequisites, rejects an empty TAP plan and fails on
any undeclared skip (`tests/ci-guarantees.bats` pins this against the
workflow itself). Two further jobs carry the platform claims: the
`setup.sh` smoke runs on Linux **and** macOS — the bash 3.2 compatibility
of the shipped shell surface — and a dedicated floor job runs the shipped
helpers stdlib-only on the documented Python 3.9 minimum, so "runs on the
floor" is executed there, not asserted here.

## What is deliberately not guaranteed

- **No universal agent-behavior guarantee is claimed, and none is
  testable here.** The deterministic rows prove what the shipped code does
  when a model (or a human, or a script) attempts the fault; they prove
  nothing about which attempts occur. That a malicious or confused actor
  cannot mint evidence through the ledger is an invariant; that an actor
  will follow the taught flow is an instruction contract whose behavioral
  evidence is — and can only be — the recorded campaigns under
  [`PROTOCOL.md`](PROTOCOL.md).
- **Host-enforced controls are only as strong as the host.** A host that
  declares no metering gets advisory limits, honestly labeled; DWP never
  publishes enforcement parity across untested hosts.
- **The instruction byte measurements are not caps on a run**, and the
  efficiency numbers are published under the accounting rules of
  [`token-efficiency.md`](../token-efficiency.md), not as guarantees.
- **Empirical rows can change with the next campaign.** A target is never
  a result; the frozen operative bar lives in the preregistration, and any
  post-freeze change requires a new identity there.

## Reproducing

```bash
bats tests/v6-faults.bats          # the fault-injection suite alone
bats tests/                        # everything, as CI runs it
```

Every case is self-contained: it creates a throwaway repository in a temp
directory, injects exactly one fault at a persisted boundary, and asserts
both the refusal and the surviving artifact. No network, no third-party
Python packages, no contributor fixtures beyond `tests/fixtures/v6/`.
