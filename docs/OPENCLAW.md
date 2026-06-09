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

## Unattended plan execution (the adapter)

OpenClaw's own docs note that skills are not designed as long-running
multi-step workflows. That is exactly the gap DeepWorkPlan fills: the durable
multi-step procedure lives in the **plan** (`.dwp/plans/PLAN_{name}/`), and
OpenClaw's scheduling primitives drive its continuation. The mapping:

| OpenClaw primitive | DWP role |
|--------------------|----------|
| Workspace (`<workspace>/`) | The **agent workspace** archetype (`spec/ARCHETYPES.md` §4): `AGENTS.md`, `.agents/`, `.dwp/` at the workspace root |
| `<workspace>/.agents/skills/` (native tier-2 scan) | Where this pack lives — no adapter shim needed |
| Heartbeat / cron turn | One **scheduled continuation** turn (`spec/AGENT_PROTOCOL.md` §7.4): wake → DWP Resume Protocol → next atomic task → update state → yield |
| `HEARTBEAT.md` checks | Add one line: *"If `.dwp/plans/` has an open plan, resume it for one task."* |
| Task ledger entries | Mirror of the plan's per-task completion (the plan's `state.json` is the source of truth) |
| Standing orders | The plan-approval boundary: which plans may run unattended, and the bounded authority of `spec/AGENT_PROTOCOL.md` §7.2 |

Operationally:

1. A human creates and approves a plan interactively (`create` flow). Approval
   is the control point — unattended turns never create-and-execute in one breath.
2. The plan **must** carry the machine-readable state layer
   (`spec/PLAN_STATE.md`): `manifest.json` + `state.json`. In a workspace
   without git, `state.json` is what makes crash-safe resume possible.
3. Each heartbeat/cron turn executes **at most one** task, passes its
   validation gate, updates `state.json` atomically, and yields.
4. On any stop condition (`spec/AGENT_PROTOCOL.md` §7.3) the agent writes
   `state.json.blocked` and reports through the workspace's normal channel —
   the next human glance (or heartbeat report) sees exactly what is needed.

The result: a multi-hour, multi-day plan that survives restarts, model
changes, and session boundaries, executed overnight by the daemon — with the
same gates a human-supervised run would have.

## Updates

```bash
openclaw skills update deepworkplan
```

## See also

- [`INSTALLATION.md`](INSTALLATION.md) — all install methods, compare / update / uninstall
- [`DESIGN.md`](DESIGN.md) — why the pack is laid out the way it is
- [`../skills/deepworkplan/spec/AGENT_PROTOCOL.md`](../skills/deepworkplan/spec/AGENT_PROTOCOL.md) — cross-agent behavior, including OpenClaw
