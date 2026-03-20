#!/bin/bash

# Usage: ./run-report.sh [options]
# Examples:
#   ./run-report.sh                    # Run without LOC counting
#   ./run-report.sh --count-loc        # Run with LOC counting
#   ./run-report.sh --count-loc --output custom.csv

source .venv/bin/activate
source .env

# Pass all command line arguments to the Python script
python3 gitlab-groups.py "$@"
