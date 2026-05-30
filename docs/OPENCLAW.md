# DeepWorkPlan skill pack — OpenClaw notes

## Install the pack

- **Registry:** `openclaw skills install deepworkplan`
- **Manual:** Clone `https://github.com/DailybotHQ/deepworkplan-skill` into
  `<workspace>/skills/deepworkplan/` (or `~/.openclaw/skills/deepworkplan/`).

The runnable skill is the `skills/deepworkplan/` directory inside this repo — the
router `SKILL.md` plus the six sub-skills, the spec, the shared helpers, and the
opt-in addons. There is no separate API document to fetch; DeepWorkPlan is
markdown-first and makes no network calls.

## How it loads

OpenClaw loads the pack natively per eligible session — no auto-activation
trigger files are needed. The router `SKILL.md` describes all capabilities and
routes the developer's intent to the right sub-skill (`onboard`, `create`,
`execute`, `refine`, `resume`, `status`).

The pack advertises an OpenClaw metadata block in the router frontmatter:

```yaml
metadata: {"openclaw":{"emoji":"🧠","homepage":"https://deepworkplan.com","requires":{"anyBins":["git","bash"]}}}
```

`requires.anyBins` lists `git` and `bash` because the only executable code in the
pack is [`shared/context.sh`](../skills/deepworkplan/shared/context.sh), which
reads local git/filesystem state and emits a single-line JSON object. No API key,
no `primaryEnv`, no install step.

## On first use

There is nothing to authenticate or install. When the developer asks to onboard a
repo or create a plan, the agent reads the relevant `SKILL.md` and acts. Plan
output lands under a gitignored `.dwp/` directory at the repo root, overridable
via the `DWP_DIR` environment variable (see
[`shared/dwp-paths.md`](../skills/deepworkplan/shared/dwp-paths.md)).

## Optional Dailybot addon

If the workspace also uses Dailybot, the opt-in
[`addons/dailybot`](../skills/deepworkplan/addons/dailybot/SKILL.md) addon can
wire best-effort progress reporting into plan execution. It is deferred,
consent-gated, and **never blocks** the plan — core DeepWorkPlan has zero Dailybot
dependency. Leave it off if you don't use Dailybot.

## Updates

```bash
openclaw skills update deepworkplan
```

## See also

- [`INSTALLATION.md`](INSTALLATION.md) — all install methods, compare / update / uninstall
- [`DESIGN.md`](DESIGN.md) — why the pack is laid out the way it is
- [`../skills/deepworkplan/spec/AGENT_PROTOCOL.md`](../skills/deepworkplan/spec/AGENT_PROTOCOL.md) — cross-agent behavior, including OpenClaw
