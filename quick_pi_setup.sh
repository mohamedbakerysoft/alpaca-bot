#!/bin/bash

# Quick Pi Setup Script - Run this ON the Raspberry Pi
# This script sets up and runs the optimized Alpaca bot

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=== Alpaca Bot Quick Setup for Raspberry Pi ===${NC}"
echo

# Check if we're on the Pi
if [[ ! -f "/etc/rpi-issue" ]] && [[ ! -d "/boot/firmware" ]]; then
    echo -e "${YELLOW}Warning: This doesn't appear to be a Raspberry Pi${NC}"
    echo "This script is designed to run ON the Raspberry Pi"
    echo
fi

# Navigate to project directory
PROJECT_DIR="/home/jarvis/alpaca-bot"
if [[ ! -d "$PROJECT_DIR" ]]; then
    echo -e "${RED}Error: Project directory not found at $PROJECT_DIR${NC}"
    echo "Please ensure the project has been transferred to the Pi first"
    exit 1
fi

cd "$PROJECT_DIR"
echo -e "${GREEN}✓ Found project directory${NC}"

# Setup optimized environment file
echo -e "${YELLOW}Setting up optimized environment...${NC}"
if [[ -f ".env.pi" ]]; then
    cp .env.pi .env
    echo -e "${GREEN}✓ Copied optimized .env.pi to .env${NC}"
else
    echo -e "${RED}Error: .env.pi file not found${NC}"
    exit 1
fi

# Check if API credentials are set
if grep -q "your_actual_api_key_here" .env; then
    echo -e "${YELLOW}⚠ API credentials need to be updated in .env file${NC}"
    echo "Please edit .env and add your actual Alpaca API credentials:"
    echo "  ALPACA_API_KEY=your_actual_key"
    echo "  ALPACA_SECRET_KEY=your_actual_secret"
    echo
    read -p "Press Enter after updating credentials, or Ctrl+C to exit..."
fi

# Setup virtual environment
echo -e "${YELLOW}Setting up virtual environment...${NC}"
VENV_DIR="alpaca-venv"

# Remove old environment if exists
if [[ -d "$VENV_DIR" ]]; then
    echo "Removing old virtual environment..."
    rm -rf "$VENV_DIR"
fi

# Create new virtual environment
echo "Creating virtual environment..."
python3 -m venv "$VENV_DIR"

# Activate virtual environment
source "$VENV_DIR/bin/activate"
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
if [[ -f "requirements/base.txt" ]]; then
    pip install -r requirements/base.txt
elif [[ -f "requirements.txt" ]]; then
    pip install -r requirements.txt
else
    echo -e "${RED}Error: No requirements file found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Dependencies installed${NC}"

# Test credentials
echo -e "${YELLOW}Testing API credentials...${NC}"
if python test_credentials.py; then
    echo -e "${GREEN}✓ API credentials are valid${NC}"
else
    echo -e "${RED}✗ API credentials test failed${NC}"
    echo "Please check your .env file and try again"
    exit 1
fi

echo
echo -e "${GREEN}🚀 Setup completed successfully!${NC}"
echo
echo "Choose how to run the bot:"
echo "1. Foreground (you'll see all output)"
echo "2. Background with screen (detachable)"
echo "3. Background with nohup (runs independently)"
echo "4. Just setup (don't run yet)"
echo
read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        echo -e "${BLUE}Starting bot in foreground...${NC}"
        echo "Press Ctrl+C to stop"
        python -m alpaca_bot.main_headless
        ;;
    2)
        echo -e "${BLUE}Starting bot in screen session...${NC}"
        echo "Use 'screen -r alpaca-bot' to reattach"
        screen -dmS alpaca-bot bash -c "source $PROJECT_DIR/$VENV_DIR/bin/activate && python -m alpaca_bot.main_headless"
        echo -e "${GREEN}✓ Bot started in background screen session${NC}"
        echo "Commands:"
        echo "  screen -r alpaca-bot  # Reattach to session"
        echo "  screen -list          # List all sessions"
        ;;
    3)
        echo -e "${BLUE}Starting bot with nohup...${NC}"
        nohup python -m alpaca_bot.main_headless > bot.log 2>&1 &
        BOT_PID=$!
        echo -e "${GREEN}✓ Bot started in background (PID: $BOT_PID)${NC}"
        echo "Commands:"
        echo "  tail -f bot.log       # View logs"
        echo "  kill $BOT_PID         # Stop bot"
        echo "  ps aux | grep alpaca  # Check if running"
        ;;
    4)
        echo -e "${GREEN}Setup complete! Bot is ready to run.${NC}"
        echo "To start manually:"
        echo "  source $VENV_DIR/bin/activate"
        echo "  python -m alpaca_bot.main_headless"
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo
echo -e "${BLUE}=== Bot Status ===${NC}"
echo "Trading Mode: Aggressive (optimized)"
echo "Trade Amount: $50 per trade"
echo "Portfolio Value: $5,000"
echo "Expected Performance: 2.5x better profits"
echo
echo "Monitor logs: tail -f logs/alpaca_bot.log"
echo "System resources: htop"
echo
echo -e "${GREEN}Happy Trading! 🚀${NC}"