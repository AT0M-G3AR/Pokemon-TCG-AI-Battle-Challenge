#!/bin/bash
cd "$(dirname "$0")"
tar --exclude='__pycache__' --exclude='*.pyc' \
    -czvf submission.tar.gz main.py policy.py deck.csv cg/ search_api.py
echo "Built submission.tar.gz — upload to Kaggle My Submissions tab."
