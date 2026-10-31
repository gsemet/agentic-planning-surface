#!/usr/bin/env bash
# Copilot CLI probe for design 5: a Foreman main session with background Driver subagents,
# each running synchronous Coder subagents. Runs in a throwaway lab, never in the repository.
# Usage: bash run-copilot-probe.sh   (about 5 minutes, a few cents of AI credits)
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
lab="$(mktemp -d /tmp/cop-probe.XXXX)"
sid="$(uuidgen | tr '[:upper:]' '[:lower:]')"
echo "$sid" > "$here/../copilot-probe-session-id.txt"
cd "$lab"
date +%T > started.txt
timeout 900 copilot --experimental --allow-all-tools --model claude-opus-5.5 \
  --session-id "$sid" -p "$(cat "$here/copilot-probe-prompt.md")" > cli.out 2>&1 || true
date +%T > ended.txt
out="$here/../copilot-probe"
mkdir -p "$out"
cp records.md cli.out started.txt ended.txt "$out/" 2>/dev/null || true
echo "session $sid, lab $lab"
uv run "$here/../../../design-4-copilot-cli/evidence/scripts/session_cost.py" \
  "$HOME/.copilot/session-state/$sid/events.jsonl"
