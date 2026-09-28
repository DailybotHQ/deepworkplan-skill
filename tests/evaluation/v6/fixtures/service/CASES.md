# Service fixture — public development cases and mechanism taxonomy

Public material for every arm and the v6 implementer. Sealed confirmation
variants are custodian-authored from this taxonomy; the implementer neither
authors nor inspects them. The mechanisms here are deliberately disjoint from
the Astro UI family: correctness is established by HTTP behavior and stored
state, never by builds or visual output.

## Mechanism taxonomy

| Mechanism | What it exercises |
| --- | --- |
| idempotency | at-least-once delivery vs exactly-once stored effect, replay-after-timeout responses |
| retry-timeout | client-visible behavior when an operation must be safe to repeat |
| transactional-invariant | atomic multi-row writes, refusal paths that record nothing |
| authz-boundary | token-gated surface, observable 401, no data leakage |
| pagination | stable keyset ordering, no duplicates or loss across pages |
| schema-compat | optional-field evolution, forward-version rejection |
| concurrency-barriers | deterministic interleavings instead of sleeps |
| partial-failure | mid-operation interruption; state stays consistent |

## Public development cases

| ID | Mechanism | Size | Objective (human-readable) | External acceptance contract (verified over HTTP and stored state) |
| --- | --- | --- | --- | --- |
| SC-1 | idempotency | small | A client timeout after a successful event delivery must be safe to retry: the same `Idempotency-Key` returns the original response and never creates a second record. | Replayed request returns the original id/payload with a replay marker; the events table holds exactly one row for the key. |
| SC-2 | transactional-invariant | small | An overdrawing transfer is refused with a clear error, and no ledger row or balance change remains. | 409 with the current balance; balances unchanged; ledger entry count unchanged. |
| SC-3 | authz-boundary | small | Admin surface requires the token; wrong and missing tokens are observably rejected. | 401 for missing/incorrect tokens; 200 with the token; no admin body leaks on failure. |
| SC-4 | pagination | medium | Listing events across pages yields every record exactly once in stable order. | Concatenated pages: no duplicates, no loss, stable ordering; `nextCursor` terminates. |
| SC-5 | concurrency-barriers | medium | Four simultaneous duplicate deliveries create exactly one record (barrier-aligned, no sleeps). | Exactly one delivery returns 201, the rest replay; stored row count for the key is one. |
| SC-6 | schema-compat | medium | A schema v2 event with a new optional field is accepted; a v3 marker is rejected with the current version named. | 201 with the optional field stored; 409 naming `current: 2`. |
| SC-7 | retry-timeout | medium | Deliveries that retry after failure converge without duplicates or data loss. | Retried deliveries replay; no duplicate rows; response identity stable. |
| SC-8 | partial-failure | medium | An interrupted transfer sequence leaves balances consistent with the ledger. | Balances always equal ledger-derived values; a refused or partial sequence records nothing. |
| SC-9 | api-surface | small | Add `GET /events/{id}` returning a single event by id with its payload and schema version. | 404 for unknown ids; 200 with the exact stored payload for known ids; replayed events readable the same way; the existing suite still passes. |
| SC-10 | pagination | medium | Add `GET /accounts` listing accounts with `limit`/`cursor` keyset pagination in stable id order. | Every page honors `limit`; concatenated pages contain every account exactly once in stable id order; `nextCursor` terminates; account balances are returned with their accounts; `GET /accounts/{id}` and the existing behavioral suite still pass. |

## Fairness notes

- The same seed, interface documentation and commands go to every arm.
- The check contract (the behavioral suite) is public and must pass on the
  pristine seed; hidden variants change the instance, not the contract.
