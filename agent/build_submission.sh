#!/bin/bash
# Packages the agent into a clean submission.tar.gz for Kaggle upload
# Excludes __pycache__ and .pyc files automatically
cd "$(dirname "$0")"
tar --exclude='__pycache__' --exclude='*.pyc' -czvf submission.tar.gz main.py policy.py deck.csv cg/
echo "Built submission.tar.gz — upload this to the Kaggle My Submissions tab."
