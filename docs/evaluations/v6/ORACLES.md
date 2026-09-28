# v6 oracles — independent, arm-blind outcome scoring

The oracles ([`tests/evaluation/v6/oracles/`](../../../tests/evaluation/v6/oracles/))
score actual product outcomes independently of DWP artifacts and agent
self-reports. They follow the house oracle rule
(`tests/reliability/oracles/score-acceptance.py`): judge the artifact, never
the narration; a missing artifact is UNVERIFIED — a failure, never a pass.

## Arm-blindness (structural, not promised)

An oracle's entire input is a workspace directory plus the pristine seed for
comparison. Arm labels, agent narratives, `.dwp/` artifacts and receipts are
not inputs and cannot change a score — a no-DWP actor needs no DWP file to
pass. `test_oracles.py` proves this structurally: a workspace carrying a fake
`narration.json` claiming success still scores FAIL.

## Calibration before use

Development oracles are proven against known-good and seeded-broken variants
BEFORE they score any agent (`oracles/calibrate.py`). For every calibration
case the matrix must hold: pristine seed → FAIL (task not done); seed +
reference fix → PASS; seed + sabotage (a plausible wrong repair) → FAIL.
Current calibrated cases — one per family, proving the framework end to end:

| Case | Family | Reference | Sabotage caught |
| --- | --- | --- | --- |
| AC-1 reading-time field | astro | schema + render + data | render dropped (build passes, behavior absent) |
| SC-9 `GET /events/{id}` | service | endpoint added | unknown ids leak another event's payload |
| LC-3 K1 repair | legacy | transliteration added | partial repair drops Cyrillic |

Remaining public cases (see `partitions/development.json`) gain calibrated
oracles the same way before any campaign uses them.

## What is recorded, separately

Product success (oracle verdicts), completion-claim truth (claims compared
against oracle outcomes — never summed into success), critical defects,
interventions, and lifecycle-only conformance (a DWP-conformant plan with a
broken product is a conformance pass and a product failure) are recorded as
distinct fields. No `.dwp` file or receipt is ever a no-DWP success
requirement.

## Subjective UI craft

Visual/craft quality is a SECONDARY blinded score with a fixed rubric and
rater-agreement checks, run separately from functional oracles; a visual
score can never compensate for broken functionality (a functional FAIL is
final regardless of craft).

## Sealed heldout oracles

Sealed confirmation oracles and reference solutions are authored by the
restricted custodian under enforced separation; the implementer sees counts,
strata and hash commitments only (`partitions/sealed.json`). On hosts without
enforced separation, sealed authoring and confirmation stay blocked;
development runs remain exploratory. Neither actors nor the implementer can
modify the external evaluator: scorers run from this committed, hash-pinned
directory in their own copy, and actors never receive scorer paths.
