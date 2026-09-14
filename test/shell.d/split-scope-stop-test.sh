#!/bin/bash
set -euo pipefail
source "$(dirname "$0")/base-test.sh"
python3 "$SHELL_TEST_DIR/fixtures/performance-setup/split-scope.py"
