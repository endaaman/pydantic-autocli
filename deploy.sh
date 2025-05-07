#!/bin/bash
set -e

# Clean up previous builds
rm -rf build/ dist/ *.egg-info/

# Build package
/usr/bin/python -m build

# Check package integrity
/usr/bin/python -m twine check dist/*

# Upload to PyPI
/usr/bin/python -m twine upload dist/*

echo "Deployment completed successfully!" 