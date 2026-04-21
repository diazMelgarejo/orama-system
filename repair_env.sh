#!/bin/bash
echo "Repairing environment for orama-system..."
cd "$(dirname "$0")"

# Remove broken venv
if [ -d ".venv" ]; then
    echo "Removing old .venv..."
    rm -rf .venv
fi

# Create new venv
echo "Creating new venv..."
python3 -m venv .venv

# Install requirements
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies..."
    ./.venv/bin/pip install --upgrade pip
    ./.venv/bin/pip install -r requirements.txt
else
    echo "requirements.txt not found, skipping pip install."
fi

# Remove old .paths to force regeneration
if [ -f ".paths" ]; then
    echo "Removing stale .paths..."
    rm .paths
fi

echo "Environment repaired. Running start.sh..."
./start.sh --status
