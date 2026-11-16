# v8 loop: instruction bytes and local daemon records

This is a bounded snapshot, not a live-session efficiency study. It compares declared instruction bytes at `origin/main` with release `v7.12.2`, then summarizes one local Herdr log window and fleet map. Filesystem bytes are not tokens, cost, latency or total context.

## Instruction bytes

Measured 2026-11-16 with `bash tests/efficiency/measure-instruction-load.sh .` at `origin/main` (`9e7eb9ff1ae80ffc47926b6c06db097bb74dc04c`) and the same tagged script on a `git archive` export of `v7.12.2` (`9569b69442e19ccf029d895b6eee302c8846bc98`). Each arm ran once (`n = 1` inventory per arm); values are filesystem bytes per flow and delta is candidate minus tag.

| Flow | `v7.12.2` bytes/flow | `origin/main` bytes/flow | Delta bytes/flow |
| --- | ---: | ---: | ---: |
| create | 74,979 | 74,979 | 0 |
| execute | 55,124 | 55,124 | 0 |
| resume | 32,021 | 32,021 | 0 |
| refine | 76,356 | 76,356 | 0 |
| onboard | 82,049 | 82,049 | 0 |
| status | 27,309 | 27,309 | 0 |
| verify | 36,596 | 36,596 | 0 |

The same 2026-11-16 command emitted `n = 15` named end-to-end path rows per arm. Only `resume-v6` changed:

| Named path | `v7.12.2` bytes/path | `origin/main` bytes/path | Delta bytes/path |
| --- | ---: | ---: | ---: |
| resume-v6 | 105,415 | 105,587 | +172 |

The `resume-v6` path includes [`spec/V6_LIFECYCLE.md`](../../skills/deepworkplan/spec/V6_LIFECYCLE.md); its added v8 contract row points to the optional `autonomy` block in [`spec/LOOP_ENGINEERING.md`](../../skills/deepworkplan/spec/LOOP_ENGINEERING.md). The lifecycle file is 13,832 bytes at the tag and 14,004 bytes at the candidate (`n = 1` file per arm, `wc -c`, 2026-11-16). The other 14 named path rows matched. Reproduce the inventory with `bash tests/efficiency/measure-instruction-load.sh .`, then `scratch="$(mktemp -d)"; git archive v7.12.2 | tar -x -C "$scratch"; bash "$scratch/tests/efficiency/measure-instruction-load.sh" "$scratch"`.

The measured entry file sets and byte totals are unchanged. The changed-file inventory is `git diff --name-status v7.12.2 9e7eb9ff1ae80ffc47926b6c06db097bb74dc04c -- skills/deepworkplan`. The path-manifest comparison is `git diff --exit-code v7.12.2 9e7eb9ff1ae80ffc47926b6c06db097bb74dc04c -- tests/efficiency/paths.tsv`; it is unchanged and declares no queue-specific path. Queue wiring is in [`shared/queue.py`](../../skills/deepworkplan/shared/queue.py), not Markdown counted by this script, so no queue-consumer byte delta is measured. Conditional reads, Python helpers, generated plans, repository files, tool output and real session context are outside this inventory. The v8 artifacts were on `origin/main`, not a released v8 tag.

## Local Herdr loop records

Read-only snapshot on 2026-11-16: `herdr-peers --version` reported `2.0.1` (protocol `2`); `herdr-peers autopilot status` reported `n = 1` background daemon with `--loop --appoint --brain`, no `--notify`. The inclusive log window is `2026-11-16T14:58:22Z` (daemon start) through `2026-11-16T15:15:55Z` (last row), containing `n = 18` timestamped rows.

Exact read commands and aggregation:

```bash
herdr-peers --version
herdr-peers log --json
herdr-peers autopilot status
herdr-peers autopilot logs --lines 100000 | python3 tests/efficiency/summarize-herdr-loop.py log --since 2026-11-16T14:58:22Z --until 2026-11-16T15:15:55Z
herdr-peers fleet --json | python3 tests/efficiency/summarize-herdr-loop.py fleet
ak --version
```

The rows below all use that date, inclusive window, `n = 18` log rows and the autopilot-log pipeline above.

| Observation | Count |
| --- | ---: |
| `plan_stalled` events | 0 events |
| `plan_blocked` events | 0 events |
| `plan_completed` events | 0 events |
| Prompt actions (`action=prompt`) | 3 prompt actions |
| `plan_no_lead` observations | 3 observations |
| Brain launches (`brain_launched`) | 2 launches |
| Brain retirements (`brain_replaced`) | 2 retirements |
| Retirement reason `permission_mode` | 2 retirements |
| `brain_launch_failed` | 1 failed launch |

The daemon status attributed both retirements to profiles starting in a mode that skips approvals; it said installed coding-agents-kit `1.4.0` does not pass the CLI ask flag and recommended `1.5.0` or an ask-mode profile default. This is the daemon's diagnosis, not a controlled cause test. The three prompt actions were two brain-launch prompts and one nudge after a prose question; no plan-lead prompt was recorded. Without `--notify`, this snapshot says nothing about notifier delivery. The [pinned Herdr v2.0.0 operator manual](https://github.com/DailybotHQ/herdr-peers/blob/v2.0.0/skills/herdr-peers/autopilot.md) documents the event classes; the live observation used the installed helper, not a controlled run of that tag.

The fleet command above read a map generated at `2026-11-16T15:19:10Z`, `51` seconds old and not stale: `n = 33` plan rows (15 completed, 4 open, 14 unreadable), `n = 14` machine rows and `n = 43` agent rows. These are one-snapshot map classifications, not events or completion rates; unreadable plans were not assigned another state.

`herdr-peers log --json` is the separate delegation/message record, not the daemon action log, so it was not used for prompt/event counts. The installed helper rejects a `--pane` selector both globally and after the verb; these local-machine reads used no pane selector. No daemon control command ran. [`summarize-herdr-loop.py`](../../tests/efficiency/summarize-herdr-loop.py) reads stdin and prints only aggregate counts/timestamps; it saves no log, plan IDs, pane addresses, branch names or paths.

## Coding-agents-kit cached path

Not measured. The installed kit reported `1.4.0`; its [tagged run documentation](https://github.com/DailybotHQ/coding-agents-kit/blob/v1.4.0/docs/run.md#output-format-json) documents `duration_s` for a general `ak run --output-format json`, not a timing command that isolates a cached path. Its [cache documentation](https://github.com/DailybotHQ/coding-agents-kit/blob/v1.4.0/docs/usage.md#the-usage-cache) covers cached usage readings. General run duration mixes lookup, agent startup and execution. The source search was `git grep -inE 'cache.*tim|tim.*cache|duration_s' v1.4.0 -- README.md docs skills`.

## Re-verify at `8.0.0`

- Repeat entry and named-path byte measurements against the released pack tag; confirm the v8 contract and queue instructions in the declared read sets.
- Recheck loop behavior against the released Herdr helper; repeat a log/map observation only if a contemporaneous read-only window is available.
- Check again for a coding-agents-kit cache-specific timing command; otherwise retain “not measured.”
