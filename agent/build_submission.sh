#!/bin/bash
# Packages the agent into a submission.tar.gz for Kaggle upload
cd "$(dirname "$0")"
tar -czvf submission.tar.gz main.py policy.py deck.csv cg/
echo "Built submission.tar.gz — upload this to the Kaggle My Submissions tab."
