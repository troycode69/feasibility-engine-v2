#!/bin/bash

# Storage OS - Startup Script
echo "🚀 Starting Storage OS..."

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Navigate to project directory
cd "$SCRIPT_DIR"

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "📦 Installing Streamlit and dependencies..."
    pip3 install -r requirements.txt 2>&1 | grep -E "(Successfully|Requirement already)"
fi

# Run the app
echo "✅ Launching Storage OS..."
echo "📍 Navigate to 💰 Underwriting page to see the 7-year projections"
echo ""
python3 -m streamlit run app.py
