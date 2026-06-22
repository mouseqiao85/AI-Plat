#!/usr/bin/env bash
# Run all explicit skill request tests
# Usage: ./run-all.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPTS_DIR="$SCRIPT_DIR/prompts"

echo "=== Running All Explicit Skill Request Tests ==="
echo ""

OK_COUNT=0
ERROR_COUNT=0
SUMMARY_LINES=""

# Test: subagent-driven-development, please
echo ">>> Test 1: subagent-driven-development-please"
if "$SCRIPT_DIR/run-test.sh" "subagent-driven-development" "$PROMPTS_DIR/subagent-driven-development-please.txt"; then
    OK_COUNT=$((OK_COUNT + 1))
    SUMMARY_LINES="$SUMMARY_LINES\nOK: subagent-driven-development-please"
else
    ERROR_COUNT=$((ERROR_COUNT + 1))
    SUMMARY_LINES="$SUMMARY_LINES\nERROR: subagent-driven-development-please"
fi
echo ""

# Test: use systematic-debugging
echo ">>> Test 2: use-systematic-debugging"
if "$SCRIPT_DIR/run-test.sh" "systematic-debugging" "$PROMPTS_DIR/use-systematic-debugging.txt"; then
    OK_COUNT=$((OK_COUNT + 1))
    SUMMARY_LINES="$SUMMARY_LINES\nOK: use-systematic-debugging"
else
    ERROR_COUNT=$((ERROR_COUNT + 1))
    SUMMARY_LINES="$SUMMARY_LINES\nERROR: use-systematic-debugging"
fi
echo ""

# Test: please use brainstorming
echo ">>> Test 3: please-use-brainstorming"
if "$SCRIPT_DIR/run-test.sh" "brainstorming" "$PROMPTS_DIR/please-use-brainstorming.txt"; then
    OK_COUNT=$((OK_COUNT + 1))
    SUMMARY_LINES="$SUMMARY_LINES\nOK: please-use-brainstorming"
else
    ERROR_COUNT=$((ERROR_COUNT + 1))
    SUMMARY_LINES="$SUMMARY_LINES\nERROR: please-use-brainstorming"
fi
echo ""

# Test: mid-conversation execute plan
echo ">>> Test 4: mid-conversation-execute-plan"
if "$SCRIPT_DIR/run-test.sh" "subagent-driven-development" "$PROMPTS_DIR/mid-conversation-execute-plan.txt"; then
    OK_COUNT=$((OK_COUNT + 1))
    SUMMARY_LINES="$SUMMARY_LINES\nOK: mid-conversation-execute-plan"
else
    ERROR_COUNT=$((ERROR_COUNT + 1))
    SUMMARY_LINES="$SUMMARY_LINES\nERROR: mid-conversation-execute-plan"
fi
echo ""

echo "=== Summary ==="
echo -e "$SUMMARY_LINES"
echo ""
echo "Successful: $OK_COUNT"
echo "Unsuccessful: $ERROR_COUNT"
echo "Total: $((OK_COUNT + ERROR_COUNT))"

if [ "$ERROR_COUNT" -gt 0 ]; then
    exit 1
fi
