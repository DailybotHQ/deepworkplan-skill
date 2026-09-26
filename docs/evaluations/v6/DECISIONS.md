# DWP v6 decision log

Decisions underpinning [`ARCHITECTURE_RFC.md`](ARCHITECTURE_RFC.md). The table
row is the durable entry; the sections below elaborate selected decisions.
Entries are appended, never rewritten; a reversed decision gains a new entry
citing its predecessor.

| ID | Decision | Status |
| --- | --- | --- |
| D1 | Record architecture: guarded snapshot (`state.json`, v6 generation) + append-only `journal.ndjson`; snapshot is the recovery root, journal is the memory | Accepted (RFC draft-1) |
| D2 | Stable task IDs (`T-<slug>`) distinct from presentation order; events cite IDs, never positions | Accepted (RFC draft-1) |
| D3 | Scheduler proposes, deterministic core authorizes: `authorize(contract, record, proposal)` is a pure function; refusals are recorded events | Accepted (RFC draft-1) |
| D4 | Trust labels on all evidence: `observed` / `imported` / `asserted`; acceptance criteria declare which classes they accept; checksums prove bytes, not semantics | Accepted (RFC draft-1) |
| D5 | SQLite rejected for the v6 record (not diffable/grep-auditable, unneeded concurrency); revisit only on multi-writer evidence | Accepted (RFC draft-1) |
| D6 | Contract is content-addressed and immutable during execution; changes create revisions with `parent_contract_id`; amendments reuse the v5 refine-3.7 record shape | Accepted (RFC draft-1) |
| D7 | Closed enumeration of allowed adaptations (split, reorder, insert in-scope experiment, strategy change, capped retry); everything else refuses by construction | Accepted (RFC draft-1) |
| D8 | Migration is explicit, one-directional, with preview/backup/integrity/ID-mapping/interrupt recovery; a failed or interrupted migration leaves the v5 plan recoverable (resume from its phase marker or restore the backup) and resumable under v5 | Accepted (RFC draft-1) |
| D9 | Preserved public surface: skill names, slash commands, `.dwp/` layout, `DWP_DIR`/`DWP_AGENT_TOOL`, `setup.sh` flags; major rationale is the changed new-plan execution/state contract | Accepted (RFC draft-1) |
| D10 | Resource limits declared `enforced` or `advisory` per host capability; enforcement parity is never claimed; exhaustion persists incomplete state | Accepted (RFC draft-1) |
| D11 | Negative-control verification required for important changed behavior; fresh-context/second-model verification earns inclusion per criterion, never unconditional | Accepted (RFC draft-1) |
| D12 | Generated views carry `contract_id` + source digest; a human edit to a generated view blocks silent overwrite and offers amendment-import | Accepted (RFC draft-1) |

## D1 — Record architecture

- **Context.** v5's single `state.json` keeps only latest values; bounded
  adaptive execution needs an audit trail of observations, adaptations,
  amendments and interventions that survives task splits, reorders and
  strategy changes. A crash-safe, human-inspectable, gitignored-but-diffable
  record is a product property ("readable plans"), not a nicety.
- **Decision.** Keep the guarded snapshot exactly where v5 tooling expects it
  and add `journal.ndjson` as the append-only event memory. Torn final lines
  quarantine; the snapshot is never derived from a partial journal at
  recovery time.
- **Consequences.** Two files to keep consistent; consistency is one-directional
  (journal → snapshot at protocol points), preserving the v5 "stale, never
  ahead" property scoped to that direction. Checkers gain a small job:
  verifying journal items cited by the snapshot exist — the snapshot carries
  per-event-type journal sequence positions to make the check well-defined.
  Markdown-wins reconciliation appends a `reconciliation` event rather than
  discarding history.
- **Alternatives.** Single JSON only (loses history); SQLite (D5);
  event-sourcing every tool call (heavyweight — events live at named protocol
  points and meaningful observations).

## D3 — Proposals vs authorization

- **Context.** The v5 failure mode this plan targets is bookkeeping by
  narration: an agent writes what it believes. Adaptation multiplies that
  risk.
- **Decision.** The scheduler's output is a proposal object; a deterministic
  pure function accepts or refuses it against the contract and the record.
  Refusals are first-class recorded events with reasons.
- **Consequences.** Adaptation behavior is testable without a model (fault
  injection on the authorization core); the model's freedom is bounded by a
  closed enumeration rather than by exhortation.
- **Alternatives.** Prompt-only guardrails (contract presence, never
  obedience); a second model as gatekeeper (cost without determinism).

## D8 — Explicit one-way migration

- **Context.** v5 already fixes the migration contract for plans (declared
  migration, manifest immutability, preserve completed evidence). Repos
  adopting v6 deserve the same discipline.
- **Decision.** Migration is an explicit user-requested flow with preview,
  backup, integrity checks, ID/evidence mapping and interruption recovery;
  the v6 reader accepts v5 plans read-only forever.
- **Consequences.** No silent behavior change for existing plans; the major
  version is carried by the new-plan contract instead.
- **Alternatives.** Auto-migration on first open (rejected: silent mutation
  of recorded evidence); dual-write both formats (rejected: two sources of
  truth).

## D10 — Honest capability posture

- **Context.** A prompt-only skill cannot enforce a hard spend cap or tool
  policy; claiming enforcement would be the exact misrepresentation v6
  exists to prevent.
- **Decision.** Every resource limit declares `enforced` or `advisory` per
  host adapter; enforced limits gate dispatch; advisory limits are surfaced
  at every checkpoint and completion; exhaustion persists incomplete state.
- **Consequences.** Campaign metrics can distinguish enforced from advisory
  boundaries; host comparison claims stay within what each host actually
  enforces.
- **Alternatives.** Uniform advisory reporting (hides real enforcement);
  requiring a specific host to ship (violates portability).

## D13 — Red-team dispositions (draft-2)

- **Context.** The adversarial red-team
  (`analysis_results/ARCHITECTURE_REDTEAM.md`) found 13 vague or
  unimplementable points (A1–A13), 5 undersold capabilities (B1–B5) and
  ranked 5 upgrades (U1–U5). The strongest claims were verified against the
  draft-1 text before acceptance: no section designates the gate executor
  (A1), the contract is RECOMMENDED exactly where the authorization row
  presupposes it (A2), and the single-writer selection silently collides
  with shipped v5 team agents (A8). A6 is grounded in this plan's own lab:
  cosmetic-stub and green-build-sabotage cells pass every shape check and
  fail only hardened behavioral checks.
- **Decision.** All 13 findings and all 5 upgrades are accepted and
  incorporated in RFC draft-2. The two structural changes beyond editing:
  (1) the contract becomes REQUIRED for every v6 new plan, with the approval
  record — not the contract's existence — scaling by plan mode (U1, closing
  A2/A3); (2) the core becomes the gate executor, making `observed` mean
  helper-executed rather than helper-mediated (A1), and negative controls
  gain mechanical residency as helper-executed counterfactual pairs that
  pass only on (old FAIL, new PASS) (U2, closing A6).
- **Consequences.** v6's headline claims ("verified outcomes") become
  testable per plan rather than per campaign; migration is honest that
  agent-invoked history is `asserted`; parallelism is a designed boundary
  (per-worker child plans) instead of a silent regression. Costs: one extra
  scoped run per controlled criterion (U2), one approval step at
  materialization (U1).
- **Alternatives.** Keep the contract RECOMMENDED with a no-contract
  authorize() fallback (rejected: the §11 Authorization row then has no
  subject for the majority case); treat migrated gate records as `imported`
  (rejected: self-authored history is a claim, not a matched external
  source); defer U3/U4 to post-release (rejected: they are pure projections
  of already-recorded events and carry the launch bar's guardrail
  endpoints).

## D14 — D2 delta-review dispositions (draft-3)

- **Context.** The red-team peer's delta review of draft-2
  (`analysis_results/ARCHITECTURE_REDTEAM_D2.md`) checked disposition
  fidelity and hunted defects introduced by the draft-2 edits: 1 BLOCKER
  (D2-1), 5 MAJOR (D2-2–D2-6), 4 NOTE (D2-7–D2-10). All quotes were
  verified against the RFC text before acceptance (every cited sentence
  found verbatim, wrap-normalized).
- **Decision.** All 10 findings accepted, none rejected. The root cause the
  review names is real and worth recording: draft-2 was applied
  additively — new normative sentences were inserted without excising the
  draft-1 sentences they invalidated. Draft-3 is therefore an
  *excision-and-binding* pass: (D2-1) §5's stamp-at-write bullet now defers
  to the executor rule and §4.3 names mediated writes `asserted`;
  (D2-2) the §11 matrix rows carry their modes; (D2-3) both modes write
  the same materialization-time approval record
  `{authority, mechanism, contract_id, plan digest}` making the
  first-task-start refusal mode-uniform, with the drift comparison at
  task-start authorization; (D2-4) `reconciliation` events carry §3.2
  authority (trigger, editor, timestamp, contract_id) and criteria
  declaring evidence classes close on `reconciled` only under amendment
  authority — otherwise `blocked`, never silently closed; (D2-5) migration
  synthesizes the contract and writes its approval record, with
  re-evidence criteria listed in the preview with their re-verification
  tasks and envelope; (D2-6) the control-pair old leg is a worktree at the
  recorded starting fingerprint carrying only the gate's declared check
  artifacts (user dirty state never reverted; non-git hosts record
  `control=unavailable`); NOTEs pinned (§15 pointer, regenerated-position
  roll bound, stale/pending/lock-detection terms, receipt-contract wording
  and the v5-runner-meets-v6-plan refusal).
- **Consequences.** Draft-3 is the implementable text for Tasks 11–22; the
  implementation map (`analysis_results/V6_IMPLEMENTATION_MAP.md`) folds
  these bindings into the owning tasks. The mode-uniform approval record
  simplifies the guarded writer (one refusal rule); reconciliation
  authority closes the markdown-wins completion loophole for
  evidence-class criteria.
- **Alternatives.** Fix only D2-1 (rejected: D2-2–D2-6 each leave an
  implementer two ways to build their owning task's acceptance); treat
  `reconciled` as an evidence class (rejected: reconciliation restores
  consistency, it does not manufacture evidence — the A4 disposition's
  whole point); let migration skip the contract when no criteria need
  re-evidence (rejected: §14.5's refusal is unconditional and the
  scheduler's authorization core is undefined without a contract).

## D15 — Evaluation-protocol preregistration red-team (F1–F11)

- **Context.** Before the Task 25 freeze, an independent read-only red-team
  reviewed the operative preregistration — `docs/evaluations/v6/PROTOCOL.md`,
  `tests/evaluation/v6/protocol/design.json` and companions — against the
  execution reality of `scripts/evaluation/v6/lab.py` and
  `tests/evaluation/v6/oracles/score_pilot.py`
  (`analysis_results/EVALUATION_PROTOCOL_REDTEAM.md`). The review also
  corrected a scoping assumption: `analysis_results/EVALUATION_PROTOCOL.md`
  is the planning predecessor; the version-controlled operative protocol is
  PROTOCOL.md + design.json. Counts: 1 BLOCKER (F1), 7 MAJOR (F2–F8),
  3 NOTE (F9–F11). Every quoted claim was verified against the code before
  acceptance (oracle vocabulary at lab.py validate, the single stub oracle
  in the pilot campaigns, the scorer's resolution ladder, sealed.json's null
  commitments, zero quota mentions, control pairs absent from every
  evaluation doc, the Task 24/25 drift, stale readiness prose, unnamed
  interval method) — all confirmed verbatim.
- **Decision.** All 11 findings accepted, none rejected. F1 (oracle link of
  the hash chain did not exist in the execution path) is the blocker the
  pilot's own legitimate mid-pilot oracle edits prove is real: landed now in
  the scorer — every oracle's defining sources are SHA-256-stamped into
  every score record, freezable with `--dump-oracle-commitments`, and
  `--oracle-commitments` refuses to score on any digest or set mismatch;
  the campaign-schema side (per-case oracle bindings) lands in lab.py
  after the in-flight r3 resume completes, together with F3 (inventory
  chain hash, analyzer refusal) and F4 (pack content re-hash at validate
  and run — the name pattern alone never vouched for content). The
  protocol-side fixes landed as data: F2 exclusion rules as six frozen
  rule objects in design.json `statistics.exclusions`; F6 quota
  pacing/budget-stop/split-windows in `partitions.confirmation.
  quota_protections` with required campaign-schema fields for
  confirmation configs; F7 accepted_outcome now carries the RFC §6
  control-pair discipline — (PASS, PASS) never counts toward acceptance,
  discriminance rates reported per arm, rounded-up controls are L6
  false-completion events; F8 TELEMETRY meter record extended with
  journal-derived mechanism events (pointed lists, never aggregates); F5
  mechanism-distinctness attestation added to sealed.json
  opaque_commitments plus the mechanism-generic review clause in the
  sealing rule; F9 freeze numbering aligned to Task 25 in both docs; F10
  stale BLOCKED readiness prose replaced in the three pilot configs and
  confirmation configs restricted to machine-checked fields; F11 the
  zero-event interval method named (exact Clopper-Pearson upper bound;
  rule-of-three as approximation only) and a 60-usable-pilot-cell floor
  added to the power rule.
- **Consequences.** The r3 full scoring (post-resume runbook step 2) runs
  under the hardened scorer and stamps oracle identities into the final
  SCORES.json — the pilot's provenance becomes retroactively verifiable.
  The Task 25 freeze now has teeth on the measurement chain, not only on
  the statistical plan. lab.py changes (F1 schema bindings, F3 chain hash,
  F4 pack re-hash, F6 required confirmation fields) are sequenced strictly
  after `PILOT_R3_RESUME_DONE` to avoid disturbing the in-flight resume.
- **Alternatives.** Land all of F1 in the scorer only (rejected: the
  campaign config is the artifact the freeze seals — bindings must be
  expressible there); defer everything to Task 25 (rejected: F2/F6/F7 are
  exactly the prose a freeze forgets, and F1's scorer half must be in
  place before the r3 final scoring for the record to carry identities);
  reject F7 as RFC scope creep (rejected: the analysis plan predating the
  RFC's normative control-pair rules is a real desync — the launch bar
  would certify rounded-up controls the L6 guard cannot see).
