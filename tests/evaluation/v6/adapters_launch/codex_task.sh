#!/usr/bin/env bash
# Benchmark actor launcher: codex CLI, one fresh headless run in its own
# disposable workspace. Same contract as claude_task.sh: the runner passes
# --workspace/--task; the prompt is TASK.md inside the workspace.
#
# --full-auto grants workspace-write with no approvals (an autonomous actor
# in a disposable workspace); --skip-git-repo-check allows a non-git
# workspace.
# Usage (called by the lab driver): codex_task.sh --workspace DIR --task ID
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
	echo "usage: codex_task.sh --workspace DIR [--task ID]" >&2
	exit 2
}
cd "$WS"
[ -f TASK.md ] || {
	echo "TASK.md missing in $WS" >&2
	exit 2
}
# Sandbox parity: the claude actor runs unsandboxed (--dangerously-skip-permissions);
# the codex actor gets the same capability. Isolation is the RUNNER's job
# (scrubbed, disposable workspaces), not the actor's.
exec codex exec --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox "$(cat TASK.md)" < /dev/null
