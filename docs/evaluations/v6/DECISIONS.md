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
