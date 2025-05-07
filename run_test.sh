#!/bin/bash

# Use the Python from the virtual environment
PYTHON=".venv/bin/python"

# Run the minimal test
echo "Running minimal test..."
$PYTHON minimal_test.py hello -n "Test User"

# Run the full test
echo -e "\nRunning full test..."
$PYTHON test_cli.py greet -n "Test User" -c 2 --verbose 