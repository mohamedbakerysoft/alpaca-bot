#!/bin/bash

# Alpaca Bot Runner for Raspberry Pi
# This script handles the Python path and environment setup automatically

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
PROJECT_DIR="/home/jarvis/alpaca-bot"
VENV_DIR="alpaca-venv"

echo -e "${BLUE}=== Alpaca Bot Launcher ===${NC}"
echo

# Check if we're in the right directory
if [[ ! -d "$PROJECT_DIR" ]]; then
    echo -e "${RED}Error: Project directory not found at $PROJECT_DIR${NC}"
    exit 1
fi

# Navigate to project directory
cd "$PROJECT_DIR"
echo -e "${GREEN}✓ In project directory: $(pwd)${NC}"

# Check if virtual environment exists
if [[ ! -d "$VENV_DIR" ]]; then
    echo -e "${RED}Error: Virtual environment not found at $VENV_DIR${NC}"
    echo "Please run the setup script first: ./quick_pi_setup.sh"
    exit 1
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Check if .env file exists
if [[ ! -f ".env" ]]; then
    echo -e "${YELLOW}⚠ .env file not found, copying from .env.pi${NC}"
    if [[ -f ".env.pi" ]]; then
        cp .env.pi .env
        echo -e "${GREEN}✓ Copied .env.pi to .env${NC}"
    else
        echo -e "${RED}Error: Neither .env nor .env.pi found${NC}"
        exit 1
    fi
fi

# Check if API credentials are set
if grep -q "your_actual_api_key_here" .env; then
    echo -e "${RED}Error: API credentials not set in .env file${NC}"
    echo "Please edit .env and add your actual Alpaca API credentials"
    exit 1
fi

echo -e "${GREEN}✓ Environment file configured${NC}"

# Set Python path to include src directory
export PYTHONPATH="$PROJECT_DIR/src:$PYTHONPATH"
echo -e "${GREEN}✓ Python path configured${NC}"

# Try different methods to run the bot
echo -e "${BLUE}Starting Alpaca Trading Bot...${NC}"
echo

# Method 1: Try with module import
if python -c "import alpaca_bot.main_headless" 2>/dev/null; then
    echo -e "${GREEN}Using module import method${NC}"
    python -m alpaca_bot.main_headless
elif [[ -f "src/alpaca_bot/main_headless.py" ]]; then
    echo -e "${YELLOW}Using direct file execution method${NC}"
    python src/alpaca_bot/main_headless.py
else
    echo -e "${RED}Error: Cannot find main_headless.py${NC}"
    echo "Available Python files:"
    find . -name "*.py" -path "*/alpaca_bot/*" | head -10
    exit 1
fi