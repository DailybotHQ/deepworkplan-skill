# CONFIG.md — DeepWorkPlan configuration file (Normative)

> Status: **7.0.0-beta.1 line**. Defines `.dwp/config.json` and
> `~/.dwp/config.json`: one file shape, one parser
> ([`../shared/config.py`](../shared/config.py)), two keys — `benchmark`
> ([`BENCHMARK.md`](BENCHMARK.md) §1) and `addons` (the addon registry,
> §3 below). Published as
> [`schema/dwp-config-v1.schema.json`](schema/dwp-config-v1.schema.json)
> (`https://deepworkplan.com/schema/dwp-config/v1.json`). RFC-2119 language.

**Governing principle.** The methodology works with no configuration file
and no addon. Nothing in this file can make a plan, a flow or conformance
depend on an addon: the registry records what a repository *opted into*, so
flows may **offer** or **amplify** — never require.

## 1. Locations and precedence

| Precedence | Path | Scope |
|---|---|---|
| 1 (highest) | `<repo-root>/.dwp/config.json` | the repository that owns the plan (the plan's `.dwp` ancestor), or the repository a flow runs in when there is no plan |
| 2 | `~/.dwp/config.json` | every repository of the local user |
| 3 | absent | everything disabled |

Both files share one shape:

```json
{
  "benchmark": { "enabled": true, "learnings": true },
  "addons": {
    "ai-diff-reviewer": { "enabled": true, "version": "v3.2.3" },
    "herdr":            { "enabled": true, "version": "v0.1.0" },
    "agentkit":         { "enabled": false },
    "devcontainer":     { "enabled": true, "version": "v0.1.0" },
    "vim":              { "enabled": true, "version": "v0.4.0" },
    "dailybot":         { "enabled": true, "version": "v3.23.3" }
  }
}
```

- An optional top-level `"schema"` MAY name
  `https://deepworkplan.com/schema/dwp-config/v1.json`; readers do not
  require it. Unknown top-level keys are ignored (forward compatibility).
- **Resolution differs by key.** `benchmark` resolves **wholesale**: a
  repository file that carries the object overrides the user file for both
  of its flags (`BENCHMARK.md` §1). `addons` resolves **per addon key**:
  the repository entry for a key wins over the user entry for that key; a
  repository file that omits a key defers to the user file for it.

## 2. Fail-closed reading (both keys)

- A missing file is the ordinary "omits everything" case — no warning.
- An unreadable path or invalid JSON: the file contributes nothing, with
  exactly **one** warning naming the file and the reason; the other file
  still applies.
- A wrong-typed value disables only what it affects, with **one** warning
  naming the file, the key and the reason (`benchmark` keeps its §1 rules;
  `addons` per §3).
- A reader MUST NOT raise, MUST NOT abort a flow, and MUST NOT be silent
  about a value it discarded.

## 3. The addon registry (`addons`)

- **Key set.** The registry keys are the **in-pack addon directory names**
  (`addons/<key>/`; ecosystem contract amendment A1) — today
  `ai-diff-reviewer`, `agentkit`, `dailybot`, `dependency-upgrade`,
  `design-system`, `devcontainer`, `herdr`, `vim`. Each addon ships an
  `addon.json` descriptor whose `key` equals its directory name
  ([`ADDONS.md`](ADDONS.md) §7). The reader derives the set by listing
  directories; it never opens a file inside an addon to do so. A key
  outside the set is **ignored with one warning** (a newer pack's addon, a
  typo) — never an error.
- **Entry shape (closed).** `enabled` (boolean, **required to enable**;
  only `true` enables) and optional `version` (string matching
  `^v\d+\.\d+\.\d+(-[0-9A-Za-z.]+)?$`). Any other field, a missing
  `enabled`, a non-boolean `enabled` or a malformed `version` makes that
  entry **not enabled** with one warning naming the file, key and reason.
  A malformed entry in the repository file decides its key (fail-closed);
  it does not fall through to the user file.
- **`"addons"` itself** must be an object; anything else contributes no
  entry from that file, with one warning.
- **Absent = not enabled.** Nothing is enabled by default. Only what
  onboarding recorded with consent, an addon's own install step, or the
  human enables anything.
- **The AI Diff Reviewer baseline is unchanged.** Its local review stays
  part of the Final Review (`ADDONS.md` §6.5); a missing installation is the
  recorded `local reviewer not installed` finding whether or not the
  registry names it. The registry adds no requirement.
- **`version` is informative in 7.0.0.** `verify` MAY warn when it differs
  from the installed product's observed version; it MUST NOT fail on it.
- **Enabled is necessary, not sufficient.** An addon contributes abilities
  only when it is enabled **and** its descriptor's detection succeeds with
  a compatible interface major (`V7_ABILITIES.md`); being listed never
  makes a product present.

## 4. Writers and readers

| Role | Who | How |
|---|---|---|
| Writer | `onboard` Phase 7b, on the developer's acceptance of one addon's offer | `python3 <pack>/shared/config.py enable <key> [--version <tag>] --repo <repo>` (a decline writes nothing; an explicit "turn it off" is `disable <key>`) |
| Writer | an addon's own install step, or the human | the same command, or a hand edit |
| Reader | `execute`, `create`, `verify`, `status` | `python3 <pack>/shared/config.py show` / `enabled` (`--plan <dir>` resolves the plan's repository) |
| Reader | `shared/benchmark.py` | the `benchmark` key only, at its emission point |

The writer **reconciles**: it preserves every other top-level key and every
other addon entry, writes atomically, and **refuses** (exit 2, nothing
written) an unknown key, a malformed version, or an existing file it cannot
parse — it never overwrites what it cannot read.

The `show` view is `{"benchmark": {...}, "addons": {key: {"enabled",
"version", "source"}}}` with warnings on stderr; `enabled` prints the
enabled keys one per line. Both are read-only.

## 5. Conformance

- A repository with no configuration file is fully conformant, and every
  flow behaves identically with no file, with every addon disabled, or with
  only unknown keys (`tests/standalone-methodology.bats`).
- The configuration file is never a plan artifact: plans never persist the
  registry or the abilities it contributes (`V7_ABILITIES.md`); a plan
  records only what it **used**, in its journal.
