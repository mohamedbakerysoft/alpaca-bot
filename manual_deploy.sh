#!/bin/bash

# Manual Deployment Script for Raspberry Pi
# Run this script to deploy optimized changes to your Pi

set -e

# Configuration
PI_USER="jarvis"
PI_HOST="jarvis.local"
REMOTE_DIR="/home/jarvis/alpaca-bot"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Alpaca Bot Manual Deployment ===${NC}"
echo

# Check if we can reach the Pi
echo -e "${YELLOW}Checking connection to Raspberry Pi...${NC}"
if ping -c 1 $PI_HOST > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Pi is reachable at $PI_HOST${NC}"
else
    echo -e "${YELLOW}⚠ Cannot reach Pi at $PI_HOST${NC}"
    echo "Please ensure:"
    echo "1. Raspberry Pi is powered on and connected to network"
    echo "2. SSH is enabled on the Pi"
    echo "3. You can SSH manually: ssh $PI_USER@$PI_HOST"
    echo
    echo "Alternative: Use git deployment or manual file transfer"
    exit 1
fi

echo
echo -e "${YELLOW}Deploying optimized files to Raspberry Pi...${NC}"

# Create backup on Pi
echo "Creating backup on Pi..."
ssh $PI_USER@$PI_HOST "cd $REMOTE_DIR && cp -r . ../alpaca-bot-backup-\$(date +%Y%m%d_%H%M%S) 2>/dev/null || true"

# Sync project files (excluding unnecessary files)
echo "Syncing project files..."
rsync -avz --progress \
    --exclude='.git/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='logs/' \
    --exclude='*.log' \
    --exclude='venv/' \
    --exclude='alpaca-venv/' \
    --exclude='.DS_Store' \
    ./ $PI_USER@$PI_HOST:$REMOTE_DIR/

# Copy optimized environment file
echo "Setting up optimized environment file..."
ssh $PI_USER@$PI_HOST "cd $REMOTE_DIR && cp .env.pi .env"

echo
echo -e "${GREEN}✓ Deployment completed successfully!${NC}"
echo
echo "Next steps:"
echo "1. SSH to your Pi: ssh $PI_USER@$PI_HOST"
echo "2. Navigate to project: cd $REMOTE_DIR"
echo "3. Update API credentials in .env file"
echo "4. Activate virtual environment: source alpaca-venv/bin/activate"
echo "5. Install/update dependencies: pip install -r requirements/base.txt"
echo "6. Run the bot: python -m alpaca_bot.main_headless"
echo
echo "For detailed instructions, see DEPLOYMENT_GUIDE.md"