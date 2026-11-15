#!/usr/bin/env bats
# Tests for the herdr addon's plan-loop notifier
# (skills/deepworkplan/addons/herdr/scripts/notify-dailybot.py).
#
# Contract (addons/herdr/SPEC.md §6.5): the script is the --notify command
# for `herdr-peers autopilot --loop`. It reads a plan-event-v1 document on
# stdin, sends one Dailybot report when the CLI is present, and exits 0
# silently in EVERY other case — the daemon's notify path must never break.

setup() {
    REPO_ROOT="$( cd "$BATS_TEST_DIRNAME/.." && pwd )"
    NOTIFY="$REPO_ROOT/skills/deepworkplan/addons/herdr/scripts/notify-dailybot.py"
    [ -x "$NOTIFY" ]

    # A PATH with the interpreter but without the Dailybot CLI (which lives
    # in /opt/homebrew/bin or similar on dev machines, and nowhere on CI).
    NO_CLI_PATH="/usr/bin:/bin"

    # A fake dailybot that records its argv, for the happy-path tests.
    FAKE_BIN="$(mktemp -d)"
    cat > "$FAKE_BIN/dailybot" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" >> "${FAKE_LOG:?}"
exit 0
EOF
    chmod +x "$FAKE_BIN/dailybot"
    export FAKE_LOG="$FAKE_BIN/log"
    : > "$FAKE_LOG"
}

teardown() {
    [ -n "${FAKE_BIN:-}" ] && rm -rf "$FAKE_BIN"
}

event_json() {
    printf '%s' "{\"schema\":\"plan-event-v1\",\"event\":\"$1\",\"plan\":\"/x/proj/.dwp/plans/PLAN_09_loop\",\"machine\":\"local\",\"lead\":\"local:wP:p2J\",\"repo_root\":\"/Users/dev/proj\",\"blocker_class\":\"$2\",\"at\":\"2026-11-15T18:00:00Z\"}"
}

@test "valid event with no dailybot CLI: exit 0, silent" {
    run env PATH="$NO_CLI_PATH" "$NOTIFY" <<< "$(event_json plan_completed '')"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "invalid JSON: exit 0, silent, nothing sent" {
    run env PATH="$FAKE_BIN:/usr/bin:/bin" "$NOTIFY" <<< 'not json at all'
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ ! -s "$FAKE_LOG" ]
}

@test "unknown event: exit 0, silent, nothing sent" {
    run env PATH="$FAKE_BIN:/usr/bin:/bin" "$NOTIFY" <<< "$(event_json plan_exploded '')"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ ! -s "$FAKE_LOG" ]
}

@test "wrong schema: exit 0, nothing sent" {
    run env PATH="$FAKE_BIN:/usr/bin:/bin" "$NOTIFY" \
        <<< '{"schema":"other-v9","event":"plan_completed","plan":"p"}'
    [ "$status" -eq 0 ]
    [ ! -s "$FAKE_LOG" ]
}

@test "completed event: one report with event, repo and plan names" {
    run env PATH="$FAKE_BIN:/usr/bin:/bin" "$NOTIFY" <<< "$(event_json plan_completed '')"
    [ "$status" -eq 0 ]
    grep -q "plan update" "$FAKE_LOG"         # the CLI subcommand was used
    grep -q "PLAN_09_loop" "$FAKE_LOG"       # plan basename, not the raw path
    grep -q "proj" "$FAKE_LOG"               # repo basename, not /Users/dev/proj
    ! grep -q "/Users/dev/proj" "$FAKE_LOG"  # no raw filesystem paths leaked
    grep -q "deepworkplan-loop" "$FAKE_LOG"  # agent name
}

@test "blocked event: message names the blocker class" {
    run env PATH="$FAKE_BIN:/usr/bin:/bin" "$NOTIFY" <<< "$(event_json plan_blocked C1)"
    [ "$status" -eq 0 ]
    grep -q "C1" "$FAKE_LOG"
    grep -q "blocked" "$FAKE_LOG"
}

@test "a failing dailybot CLI still exits 0 silently" {
    cat > "$FAKE_BIN/dailybot" <<'EOF'
#!/usr/bin/env bash
echo "not logged in" >&2
exit 2
EOF
    chmod +x "$FAKE_BIN/dailybot"
    run env PATH="$FAKE_BIN:/usr/bin:/bin" "$NOTIFY" <<< "$(event_json plan_stalled '')"
    [ "$status" -eq 0 ]
}
