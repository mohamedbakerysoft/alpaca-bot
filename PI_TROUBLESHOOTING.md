# Raspberry Pi Troubleshooting Guide

## Module Import Error Fix

### Problem
```bash
ModuleNotFoundError: No module named 'alpaca_bot'
```

### Solutions

**Solution 1: Run from project root with correct path**
```bash
# Make sure you're in the project directory
cd /home/jarvis/alpaca-bot

# Activate virtual environment
source alpaca-venv/bin/activate

# Add current directory to Python path and run
PYTHONPATH=/home/jarvis/alpaca-bot/src python -m alpaca_bot.main_headless
```

**Solution 2: Install package in development mode**
```bash
# From project root with venv activated
cd /home/jarvis/alpaca-bot
source alpaca-venv/bin/activate

# Install the package in development mode
pip install -e .

# Now you can run normally
python -m alpaca_bot.main_headless
```

**Solution 3: Run directly with Python path**
```bash
# From project root
cd /home/jarvis/alpaca-bot
source alpaca-venv/bin/activate

# Run the main file directly
python src/alpaca_bot/main_headless.py
```

**Solution 4: Use the correct module path**
```bash
# If the above don't work, try:
cd /home/jarvis/alpaca-bot/src
python -m alpaca_bot.main_headless
```

### Quick Fix Commands

**One-liner fix:**
```bash
cd /home/jarvis/alpaca-bot && source alpaca-venv/bin/activate && PYTHONPATH=/home/jarvis/alpaca-bot/src python -m alpaca_bot.main_headless
```

**Permanent fix (recommended):**
```bash
cd /home/jarvis/alpaca-bot
source alpaca-venv/bin/activate
pip install -e .
python -m alpaca_bot.main_headless
```

### Alternative: Run GUI version
```bash
# If you want to run with GUI (if display is available)
PYTHONPATH=/home/jarvis/alpaca-bot/src python -m alpaca_bot.main
```

### Verify Installation
```bash
# Check if package is properly installed
pip list | grep alpaca

# Check Python path
python -c "import sys; print(sys.path)"

# Test import
python -c "import sys; sys.path.append('/home/jarvis/alpaca-bot/src'); import alpaca_bot; print('Import successful')"
```

### Environment Setup Script
Create this script to always set up the environment correctly:

```bash
# Create run_bot.sh
cat > /home/jarvis/alpaca-bot/run_bot.sh << 'EOF'
#!/bin/bash
cd /home/jarvis/alpaca-bot
source alpaca-venv/bin/activate
export PYTHONPATH=/home/jarvis/alpaca-bot/src:$PYTHONPATH
python -m alpaca_bot.main_headless
EOF

# Make it executable
chmod +x /home/jarvis/alpaca-bot/run_bot.sh

# Run it
./run_bot.sh
```

### Common Issues

1. **Wrong directory**: Make sure you're in `/home/jarvis/alpaca-bot`
2. **Virtual environment not activated**: Run `source alpaca-venv/bin/activate`
3. **Python path not set**: Use `PYTHONPATH=/home/jarvis/alpaca-bot/src`
4. **Package not installed**: Run `pip install -e .` from project root

### Success Indicators
When working correctly, you should see:
```
[INFO] Starting Alpaca Trading Bot...
[INFO] Loading configuration...
[INFO] Connecting to Alpaca API...
```

If you see these messages, the bot is running successfully!