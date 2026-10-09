# DeepWorkPlan v7 — What Ships and What Follows (Planning Record)

> **Status: NON-NORMATIVE.** A planning record. The normative rules for
> everything that ships live in [`CONFIG.md`](CONFIG.md),
> [`ADDONS.md`](ADDONS.md), [`V7_ABILITIES.md`](V7_ABILITIES.md) and
> [`V7_CONTRACT.md`](V7_CONTRACT.md). Nothing here gates conformance.

## The rule v7 is built on

**The methodology works alone.** The `deepworkplan` skill needs no addon to
create, execute, verify or resume a plan. Every addon is optional and only
amplifies it; no addon gates conformance and no flow requires one
(`tests/standalone-methodology.bats` runs the whole lifecycle with no
configuration, every addon disabled, unknown keys and malformed configs, and
proves no addon file is opened).

The second rule follows from the first: a capability that is useful without
DWP is its **own product** (own repository, license, tags and interface
number), and the pack carries a **thin integrator** for it — never a copy.

## What v7 ships (7.0.0)

| Surface | What it is |
|---|---|
| **Addon registry** | `.dwp/config.json` / `~/.dwp/config.json` → `addons.<key>` (`enabled`, informative `version`); one stdlib reader shared with `benchmark`; per-key precedence; fail-closed with one warning; absent = not enabled ([`CONFIG.md`](CONFIG.md)). |
| **Addon descriptors** | `addons/<key>/addon.json` for every in-pack addon: pinned product (repo, exact tag, interface), read-only detect (argv without a shell, or paths), abilities, grants, transport ([`ADDONS.md`](ADDONS.md) §7). |
| **Addon-provided abilities** | effective abilities = host ∪ abilities of enabled, valid, detected, interface-compatible addons; computed per call, never persisted; an ability is never authority or consent ([`V7_ABILITIES.md`](V7_ABILITIES.md)). |
| **v7 contract generation** | `plan-contract/v7` (v6 + `parallel_safe`), `journal-event/v7` (v6 + `delegation`), `plan-manifest/v7`; default for new plans; v6 plans unchanged ([`V7_CONTRACT.md`](V7_CONTRACT.md)). |
| **Delegation** | `ledger.py delegate launch|observe|collect|cancel` behind a recorded gate (grant, marker, ability); `execute/delegation.md`; a delegate's result stays `asserted` until the plan's own gates observe it. |
| **Thin integrators** | `agentkit` → `coding-agents-kit@v0.3.0` (headless transport, `ak run`; autonomy by default with an always-winning opt-out since `v0.2.0`); `herdr` → `herdr-peers@v0.1.0` (interactive transport; stamp `[herdr-peers]`, protocol owned by herdr-peers); `devcontainer` → `devcontainer-kit@v0.2.0` (`dck init` and the `dck-dockerfile` skill, interface 2, per-repository Dockerfile, vendor-neutral); `vim` → `deepworkplan-vim@v0.5.1` (surface-driven editor offer). |
| **Pre-release channel** | `prerelease.yml` cuts `X.Y.Z-beta.N` on dispatch (never `latest`, with `SHA256SUMS`); stable releases ignore pre-release tags and graduate only on `[graduate]`. |
| **Standard** | DWP standard **7.0.0** (normative additions above); `6.0.0` declarations stay valid. |

Interfaces between the pieces are integers (`interface: 1` everywhere in v7.0; devcontainer-kit moved to `2` at `v0.2.0`);
tags pin what is installed. An unknown interface major is one warning and
"not available" — never an error.

## Release order

1. Product tags: `herdr-peers` `v0.1.0`, `coding-agents-kit` `v0.1.1`
   (supersedes `v0.1.0`, a security patch), `devcontainer-kit` `v0.1.4`
   (after the `v0.1.1` security release and an agents-layer fix),
   `deepworkplan-vim` `v0.4.2`.
2. `deepworkplan-skill` `v7.0.0-beta.1` — a GitHub **pre-release**.
3. A field test in real repositories.
4. `v7.0.0` — graduated from the beta by a `[graduate]` merge.

## Follow-ups (v7.x)

- **`deepworkplan.nvim`** — the editor's `lua/dwp/` modules as a plugin for
  people who keep their own Neovim config (v7.1). The vim addon names this
  route and never offers it before it ships.
- **A v7 benchmark record** — `benchmark-record/v1` pins `generation: "v6"`
  and a plain `X.Y.Z` pack version, so v7 plans (and v6 plans run by a
  pre-release pack) are reported "not measured" today.
- **`addons.version` parity** — informative in 7.0.0; `verify` warns on a
  mismatch. A parity failure mode is a candidate once the field test shows
  how often versions drift.
- **devcontainer-kit workspaces** (satellites, port pools, a proxy) — in the
  kit's own roadmap, not the pack's.
- **Sender authentication between peers** — herdr-peers' `from=` is a claim;
  a scope allow-list (`HERDR_PEERS_SCOPE`) is the mitigation today.
