# Raspberry Pi Deployment Guide

## Quick Deployment Steps

Follow these steps to deploy your optimized Alpaca trading bot to the Raspberry Pi:

### 1. Prepare Files for Transfer

All the optimized changes have been made to:
- `src/alpaca_bot/strategies/scalping_strategy.py` (improved entry/exit logic)
- `src/alpaca_bot/config/settings.py` (optimized parameters)
- `.env.pi` (updated with aggressive trading mode and optimized settings)

### 2. Transfer Files to Raspberry Pi

**Option A: Using SCP (if SSH is set up)**
```bash
# From your Mac, run:
scp -r . jarvis@jarvis.local:/home/jarvis/alpaca-bot/
```

**Option B: Using Git (recommended)**
```bash
# 1. Commit and push changes from Mac
git add .
git commit -m "Deploy optimized trading bot settings"
git push origin main

# 2. On Raspberry Pi, pull changes
ssh jarvis@jarvis.local
cd /home/jarvis/alpaca-bot
git pull origin main
```

**Option C: Manual Transfer**
- Use a USB drive or network share to copy the entire project folder

### 3. Setup Environment on Raspberry Pi

```bash
# SSH into your Raspberry Pi
ssh jarvis@jarvis.local

# Navigate to project directory
cd /home/jarvis/alpaca-bot

# Copy the optimized environment file
cp .env.pi .env

# Edit .env to add your actual Alpaca API credentials
nano .env
```

**Important: Update these values in .env:**
```bash
ALPACA_API_KEY=your_actual_api_key_here
ALPACA_SECRET_KEY=your_actual_secret_key_here
```

### 4. Setup Virtual Environment

```bash
# Create virtual environment
python3 -m venv alpaca-venv

# Activate virtual environment
source alpaca-venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements/pi.txt
# OR if pi.txt doesn't exist:
pip install -r requirements/base.txt
```

### 5. Test the Installation

```bash
# Test credentials
python test_credentials.py

# Run the bot in test mode
python -m alpaca_bot.main_headless
```

### 6. Run the Optimized Bot

```bash
# Activate virtual environment (if not already active)
source alpaca-venv/bin/activate

# Run headless (no GUI)
python -m alpaca_bot.main_headless

# OR run with screen for background execution
screen -S alpaca-bot python -m alpaca_bot.main_headless
```

## Optimizations Applied

### Trading Parameters
- **Trading Mode**: Changed to `aggressive` for maximum opportunities
- **Trade Amount**: Increased to $50 per trade
- **Portfolio Value**: Increased to $5,000
- **Stop Loss**: Widened to 2% (from 1%)
- **Take Profit**: Optimized to 5% (from 10%)

### Strategy Improvements
- **Entry Conditions**: Relaxed from 3 required signals to 2
- **Exit Conditions**: Improved take profit thresholds by 50%
- **RSI Levels**: More relaxed overbought/oversold conditions
- **Position Sizing**: Optimized multipliers for better performance

### Risk Management
- **Support/Resistance Thresholds**: Reduced for more opportunities
- **Volume Requirements**: Lowered for more trading chances
- **Daily Trade Limits**: Increased for maximum activity

## Monitoring and Logs

```bash
# View logs
tail -f logs/alpaca_bot.log

# Monitor system resources
htop

# Check bot status (if running in screen)
screen -r alpaca-bot
```

## Troubleshooting

1. **Import Errors**: Make sure virtual environment is activated
2. **API Errors**: Verify your Alpaca credentials in .env
3. **Permission Errors**: Check file permissions with `ls -la`
4. **Memory Issues**: Monitor with `free -h` and `htop`

## Expected Performance Improvements

- **Reduced micro-profits**: Higher take profit targets (2.5%-5%)
- **Lower transaction costs**: Larger trade amounts ($50 vs $10)
- **Fewer premature exits**: Wider stop losses
- **More opportunities**: Relaxed entry conditions
- **Better position sizing**: Optimized for profitability

The bot should now perform significantly better with these optimizations!