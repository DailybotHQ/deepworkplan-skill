# V7_ABILITIES.md — Addon-provided abilities (Normative)

> Status: **7.0.0**. Extends [`V6_RESOURCES.md`](V6_RESOURCES.md)
> §1 (host capability negotiation) without changing it: the closed ability
> set, the all-False minimal host and the refusal of unknown keys stand.
> What v7 adds is a second, **runtime-only** source of abilities — the
> addons a repository enabled. Implemented by `shared/resources.py`
> (`effective_abilities`, CLI `abilities`). RFC-2119 language.

## 1. The union rule

```
effective = host-declared abilities
          ∪ provides_abilities(addon)  for every addon that is
                                       (a) enabled in the registry (CONFIG.md §3),
                                       (b) described by a valid addon.json (ADDONS.md §7),
                                       (c) detected (§2), and
                                       (d) on a compatible interface major (§3)
```

- The host side is exactly v6: declared abilities over the all-False floor
  — the machine-readable record (`.dwp/config.json` / `~/.dwp/config.json`
  key `host`, [`CONFIG.md`](CONFIG.md) §3a) overlaid by an explicit
  `resources.py --caps`, per capability (F-17). An unknown
  ability key — from the host **or** from a descriptor — MUST be refused;
  a capability is never invented.
- An addon that fails (a)–(d) contributes **nothing**. Failing (b)–(d) for an
  addon that would contribute an ability produces **exactly one warning**
  naming the addon and the reason; it is never an error of the plan, the
  flow or the repository.
- An addon that is not enabled MUST NOT be consulted: its descriptor is not
  opened and its detect command is not run
  (`tests/standalone-methodology.bats` traces this).
- The union is **monotone**: enabling an addon can only add abilities;
  disabling it removes exactly what it contributed. The **minimal host**
  with no enabled addon stays a supported posture.

## 2. Detection

A descriptor's `detect` is read-only:

- `command` — an argv line (no shell metacharacters by schema) run
  **without a shell**, stdin closed, bounded by a 10-second timeout. Exit 0
  means present. A missing binary is "not installed"; a timeout or a
  non-zero exit is "not detected". Nothing it prints is executed.
- `paths` — present when at least one listed file exists (repository
  relative, or `~/` for machine-level installs).

## 3. Interface compatibility

When the descriptor pins `product.interface`, the integer the product
reports MUST equal it. The value is read by `detect.interface_from`:
`json:<field>` (the command's stdout is one JSON object, e.g. `ak doctor
--json` → `"interface": 1`), `regex:<pattern>` (first group, e.g.
`herdr-peers --version` → `(protocol 1)`), or `file-json:<path>#<field>`
(e.g. the editor's `addon/surface.json`). An unreadable value or a
different major is "not available" with one warning — the integrator
refuses a product it cannot speak to rather than guess. A product that
publishes no interface (no `product.interface` in its descriptor) is
compatible when detected.

## 4. Never persisted

Effective abilities are recomputed on every call from the host
declaration, the registry and live detection. They MUST NOT be written to
a plan — not to `contract.json`, `state.json`, the views or the journal —
and a plan MUST NOT treat an ability observed in one session as available
in another. What a plan records is what it **used**: a delegation journal
event (`V7_CONTRACT.md`) names the transport and the addon that carried
it. `resources.py abilities` and `routing` are read-only over the plan.

## 5. Abilities are not authority

An ability is what the environment can do; a **grant** is what the plan's
contract authorizes (`V6_CONTRACT.md` §1). Every posture that needs an
ability still needs its grant:

- parallel dispatch / delegation — the `agent_delegation` grant **and** the
  `subagents` ability (`V6_RESOURCES.md` §6; delegation adds the
  conditions of `V7_CONTRACT.md`);
- model switching — the `model_routing` grant **and** ability;
- `telemetry` contributed by the Dailybot addon is reporting capability
  only: sending anything still requires the developer's consent and the
  addon's own authorization (`ADDONS.md` §6.2). An ability never implies
  consent.

`resources.py routing` reports, next to each posture, which source
supplied each ability (`host` or `addon:<key>`), so a posture that depends
on an addon is visible as such. A posture is a permission statement,
never an efficacy claim.

## 6. Conformance

- A repository with no registry, or with every addon disabled, computes
  exactly the v6 host abilities.
- The `addons` section of the registry and the descriptors are the only
  inputs besides the host declaration; nothing else may add an ability.
- The resolution is deterministic for identical inputs (registry, descriptors,
  detection outcomes); detection itself observes the live environment and
  is therefore never cached across sessions.
