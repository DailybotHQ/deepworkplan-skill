#!/usr/bin/env bash
# Benchmark actor launcher: claude CLI, one fresh headless run in its own
# disposable workspace. The lab driver materializes the task prompt as
# TASK.md inside the workspace; the actor's ONLY inputs are that workspace
# and (for arm B) the assigned read-only pack via DWP_EVAL_PACK.
#
# Autonomous actor: full tool access is required to do real work; the
# workspace is disposable and isolation is the runner's job, not the actor's.
# Usage (called by the lab driver): claude_task.sh --workspace DIR --task ID
set -eu
WS=""
while [ $# -gt 0 ]; do
	case "$1" in
	--workspace)
		WS="$2"
		shift 2
		;;
	--task)
		shift 2
		;;
	*)
		shift
		;;
	esac
done
[ -n "$WS" ] || {
	echo "usage: claude_task.sh --workspace DIR [--task ID]" >&2
	exit 2
}
cd "$WS"
[ -f TASK.md ] || {
	echo "TASK.md missing in $WS" >&2
	exit 2
}
exec claude -p "$(cat TASK.md)" --output-format json --dangerously-skip-permissions
