#!/usr/bin/env bash

set -e

echo "Formatting with Black..."
black .

echo
echo "Linting with Ruff..."
ruff check --fix .

echo
echo "Running tests..."
pytest

echo
echo "✓ Code formatted and verified."