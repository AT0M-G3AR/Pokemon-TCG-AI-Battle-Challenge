#!/bin/bash
# Prevent macOS from adding ._* resource fork files to the tarball
export COPYFILE_DISABLE=1

# Ensure we always build in the agent/ directory regardless of how this is invoked
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Pre-flight syntax check using the project's Python 3.11 virtual environment
PYTHON_CMD="../venv/bin/python3"
if [ ! -f "$PYTHON_CMD" ]; then
    PYTHON_CMD="python3" # Fallback if venv is missing
fi

echo "Running pre-flight syntax check..."
$PYTHON_CMD -m py_compile main.py policy.py search_api.py
if [ $? -ne 0 ]; then
    echo "❌ Syntax check failed! Aborting build."
    exit 1
fi
echo "✅ Syntax check passed."

# Use explicit paths from the working directory. tar does not use git.
tar --exclude='__pycache__' --exclude='*.pyc' \
    -czvf submission.tar.gz \
    main.py \
    policy.py \
    search_api.py \
    deck.csv \
    cg

echo "Built submission.tar.gz in $DIR — upload to Kaggle My Submissions tab."
