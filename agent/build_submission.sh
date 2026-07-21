#!/bin/bash
cd "$(dirname "$0")"

# Pre-flight syntax check using the project's Python 3.11 virtual environment
PYTHON_CMD="../venv/bin/python3"
if [ ! -f "$PYTHON_CMD" ]; then
    PYTHON_CMD="python3" # Fallback if venv is missing
fi

$PYTHON_CMD -m py_compile main.py policy.py search_api.py shallow_search.py
if [ $? -ne 0 ]; then
    echo "BUILD ABORTED: syntax error detected, not packaging a broken submission"
    exit 1
fi

# Prevent macOS from adding ._* resource fork files to the tarball
export COPYFILE_DISABLE=1

# Use explicit paths from the working directory. tar does not use git.
tar --exclude='__pycache__' --exclude='*.pyc' \
    -czvf submission.tar.gz \
    main.py \
    policy.py \
    search_api.py \
    shallow_search.py \
    deck.csv \
    cg

echo "Built submission.tar.gz — upload to Kaggle My Submissions tab."
