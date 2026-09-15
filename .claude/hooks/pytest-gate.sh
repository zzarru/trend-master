#!/usr/bin/env bash
# PreToolUse hook (matcher: Bash, if: Bash(git commit*))
# Runs the test suite before allowing a `git commit` and denies the commit
# if any test fails, surfacing the failure output as the deny reason.

output=$(python -m pytest -q 2>&1)
ec=$?

if [ $ec -ne 0 ]; then
  printf '%s' "$output" | tail -c 1500 | python -c "
import json, sys
reason = 'pytest failed - fix tests before committing:\n' + sys.stdin.read()
print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'deny',
        'permissionDecisionReason': reason,
    }
}))
"
else
  echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow"}}'
fi
