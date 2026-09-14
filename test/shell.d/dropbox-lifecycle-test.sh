#!/bin/bash
set -euo pipefail
source "$(dirname "$0")/base-test.sh"
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software /usr/lib/qt6/bin/qmltestrunner \
  -input "$SHELL_TEST_DIR/fixtures/dropbox" \
  -import "$SHELL_TEST_DIR/fixtures/dropbox/imports" -o -,txt
python3 "$SHELL_TEST_DIR/fixtures/dropbox/inventory-test.py"
