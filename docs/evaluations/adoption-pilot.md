# Adoption pilot — upgrading an existing repository

Installing a newer skill is easy. The question this pilot answers is harder: when
a repository was already onboarded under an older standard, and it carries
handwritten rules, a team's own skill and a half-finished plan, **does upgrading
preserve all of it — and does the developer get something useful out of the
upgrade without re-onboarding from scratch?**

## What was piloted

Three isolated fixtures, all non-Astro, none of them this website:

| Fixture | Shape | What it tests |
| --- | --- | --- |
| `legacy-py-service` | Python billing service, onboarded at DWP 2.1.0, in-flight 2.2.0 plan | The full upgrade path end to end, with a **runnable** gate |
| `legacy-go-service` | Go orders service, onboarded, in-flight 2.2.0 plan | Preservation and idempotency on a second stack |
| `fresh-rust-cli` | Rust CLI, never onboarded | Fresh install and entry-point discovery |

Only the Python fixture has a toolchain available in this environment. That is
stated up front because it bounds what the other two can show: **no Go or Rust
compiler is installed here, so those fixtures prove file-level preservation and
discovery, never a passing gate.** No fixture is a third-party production
repository.

## The upgrade path — no new installer

There is no separate upgrade tool. Reinstalling the skill *is* the upgrade, and
the router decides what to do next from three repository states:

1. **Not AI-first** → onboard.
2. **AI-first but predating the shipped standard** — no `DWP standard:`
   provenance line, an older one, or a `docs/TESTING_GUIDE.md` without the
   scoped-invocation and mapping content the standard requires → **offer the
   targeted harness upgrade**.
3. **AI-first and current** → route by intent, silently.

State 2 is what this pilot exercises.

## Legacy Python service — the whole path

**Before.** `AGENTS.md` with three handwritten house rules and a
`DWP standard: 2.1.0 (onboarded 2026-05-12; skill 2.1.0)` line; a
`docs/TESTING_GUIDE.md` that documented only the full-suite command; a
team-authored `.agents/skills/custom-deploy`; a frozen
`internal/legacy_report.py`; the **real** pre-upgrade pack (`main` at `eaf5499`)
vendored under `.agents/skills/deepworkplan`; and `PLAN_billing_rounding`, an
in-flight plan at spec 2.2.0 with the three legacy final tasks, 1 of 5 done.

**The steps.** Six, and the operator was asked **zero** questions — every input
came from the repository itself:

| # | Step | Result |
| --- | --- | --- |
| 1 | Reinstall the pack over the old one | 43 files modified, 15 added (the guide split, `shared/troubleshooting.md`, the new sub-skill branches) |
| 2 | Detect harness age | repo declares 2.1.0, pack ships 2.3.0, testing guide has 0 scoped-invocation mentions → targeted upgrade |
| 3 | Verify scoped commands **before** documenting them | all four patterns run: full suite, by module, by test name, by pattern. No `ruff`/`flake8`/`black`/`mypy` → recorded as an honest absence, not a guessed lint gate |
| 4 | Reconcile only what the standard requires | provenance line, one appended DWP-owned testing rule, seven `.agents/commands/` delegators refreshed from the pack, and the §3.4 content written between markers **below** the original handwritten text |
| 5 | Re-run the reconciliation | byte-identical (`sha256sum -c` on all nine touched files: OK) |
| 6 | Resume the in-flight legacy task | `split_evenly` + 4 tests; gate escalated to the full suite because `src/money.py` is shared core; `Ran 5 tests … OK`; `git diff --check` clean; committed |

**Preservation, by checksum.** Everything handwritten survived byte-for-byte:

```
.agents/skills/custom-deploy/SKILL.md   OK
internal/legacy_report.py               OK
src/money.py                            OK   (before task 6 touched it)
tests/test_money.py                     OK
.dwp/plans/PLAN_billing_rounding/*      OK   (README, manifest, state, task file)
```

`AGENTS.md` changed — and only as intended: `14 insertions(+), 1 deletion(-)`,
being the provenance line and one appended marker-delimited section. The three
house rules are unchanged. `docs/TESTING_GUIDE.md` kept its original prose above
the marker.

**The legacy plan was not migrated.** After the upgrade its `manifest.json` still
reads `spec_version: 2.2.0` with
`["Security Review", "Skills & Agents Discovery", "Executive Report"]`, and task 2
was executed and closed *under that lifecycle*. Migration is a separate, explicit
`refine migrate` — never a side effect of upgrading the harness.

**Both lifecycles coexist and both are checked.** A new plan in the same
repository declaring 2.3.0 with a single Final Review passes alongside it:

```
Plan: PLAN_billing_rounding   [x] plan standard: DWP spec 2.2.0
                              [x] mandatory task: security review
                              [x] mandatory task: skills & agents discovery
                              [x] mandatory task: executive report
Plan: PLAN_currency_format    [x] plan standard: DWP spec 2.3.0
                              [x] mandatory final task: Final Review is task 2 (last)
                              [x] Final Review names its three parts
```

The checker also *earned* those passes. A first run rejected a Final Review whose
filename was right but whose body never mentioned the security pass, the
final-state validation or the skills reconciliation — "the filename alone does not
prove coverage". It also caught a mis-numbered legacy discovery task and a
non-canonical plan-status line in the fixture. Those were fixture defects, and
they are recorded here rather than quietly corrected, because a checker that only
ever passes is not evidence of anything.

## The honest limit of a targeted upgrade

After a complete, faithful upgrade the repository is **still not conformant**:

```
[ ] .agents/agents/
[ ] .agents/docs/
Verdict: NOT CONFORMANT — 2 issue(s) (45 passed, 4 advisory)
```

That is correct behavior, not a defect. The fixture was never fully onboarded, so
those directories never existed, and a *targeted* upgrade is not entitled to
invent a kit the repository never had. But it is the pilot's main finding, and it
changed the shipped instructions: `onboard/SKILL.md`'s upgrade path now requires
the agent to **name what the upgrade deliberately did not create** and say that a
full onboarding is the way to close it — never to imply the upgrade made the
repository conformant when a conformance run would still report findings.

## What made the benefit observable

The developer sees value without adopting a single addon and without replacing
the test suite:

- The gate a task runs is now *derived*, not guessed. `src/money.py` is declared
  shared core, so task 6's validation widened to the full suite by rule.
- The absence of a linter is written down, so no agent will ever report a lint
  gate as passing here.
- The scoped invocations in `AGENTS.md` were each executed before being written.

## Measurements, and what they are not

- **Steps to the first validated useful task:** six, listed above.
- **Avoidable operator questions:** zero. The declared test command came from
  `AGENTS.md`; the source-to-test mapping was derivable from the mirrored tree.
- **Wall clock** for the mechanical portion of step 6 was 14 seconds. This
  excludes agent reasoning entirely and is **not** a latency or efficiency claim;
  it is recorded only to show the fixture's gate is genuinely fast, which is why
  the guide recommends the full suite over elaborate selection there.

## Remaining bottlenecks

1. **A targeted upgrade cannot close baseline gaps** (above). Repositories
   onboarded partially stay partially onboarded until someone runs the full flow.
2. **The reconciliation is only as good as the repository's declared command.**
   This fixture declared a real one. A repository with none would have produced a
   documented gap at step 3 instead of four verified invocations — correct, but
   much less useful, and the developer has to fix it.
3. **Toolchain availability bounds the evidence.** The Go and Rust fixtures could
   not run any gate in this environment.

## Reproducing it

```bash
# from the skill repo root
bash .dwp/…/adoption/reconcile-legacy-py.sh <fixture-root> <section-file>   # step 4, idempotent
bash skills/deepworkplan/verify/conformance.sh <fixture-root>               # the verdicts above
```

The fixtures live under `tmp/task21-adoption/` (git-ignored scratch). The
reconciliation script and the machine-readable pilot record are kept with the
plan's evaluation records; this document is the durable narrative.

## Runtime guidance shipped with the pack

Everything an *installed, offline* agent needs when this goes wrong is inside the
pack, not here: [`shared/troubleshooting.md`](../../skills/deepworkplan/shared/troubleshooting.md)
carries a compact decision path for discovery failure, stale installation, a
missing test command, an unsupported host capability and inconsistent plan state.
The router links it as a conditional resource — read only when something is
already wrong — so it costs nothing on the healthy path.
