#!/bin/bash

# Set workdir to repository root
REPO_ROOT=$(git rev-parse --show-toplevel)
cd "${REPO_ROOT}"

echo "Running tests via act..."
act push -j test --bind
