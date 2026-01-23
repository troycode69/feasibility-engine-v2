#!/bin/bash
# Install Playwright browsers after dependencies
echo "Installing Playwright browsers..."
python -m playwright install chromium --with-deps
echo "Playwright installation complete!"
