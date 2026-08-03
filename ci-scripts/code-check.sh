#!/usr/bin/env bash

set -e

echo
echo "========== Black =========="
black --check .

echo
echo "========== Ruff =========="
ruff check .

echo
echo "========== Pytest =========="
pytest

echo
echo "All checks complete."