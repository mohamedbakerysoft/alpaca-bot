#!/bin/bash

# Quick fix script for Raspberry Pi import issue
# This script updates the existing Pi installation to use main_headless.py instead of main.py

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PI_USER="jarvis"
PI_HOST="jarvis.local"
REMOTE_DIR="/home/jarvis/alpaca-bot"
VENV_NAME="alpaca-venv"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we can connect to Pi
check_connection() {
    log_info "Checking connection to Raspberry Pi..."
    if ssh -o ConnectTimeout=5 "$PI_USER@$PI_HOST" "echo 'Connection successful'" >/dev/null 2>&1; then
        log_success "Connected to $PI_HOST"
    else
        log_error "Cannot connect to $PI_HOST. Please check your SSH setup."
        exit 1
    fi
}

# Fix the scripts and service on Pi
fix_pi_installation() {
    log_info "Fixing Pi installation to use main_headless.py..."
    
    ssh "$PI_USER@$PI_HOST" << EOF
        cd $REMOTE_DIR
        
        # Stop the service if it's running
        sudo systemctl stop alpaca-bot.service 2>/dev/null || true
        
        # Update start_bot.sh script
        cat > start_bot.sh << 'SCRIPT_EOF'
#!/bin/bash
cd $REMOTE_DIR
source $VENV_NAME/bin/activate
python src/alpaca_bot/main_headless.py
SCRIPT_EOF
        
        # Make it executable
        chmod +x start_bot.sh
        
        # Update systemd service file
        sudo tee /etc/systemd/system/alpaca-bot.service > /dev/null << 'SERVICE_EOF'
[Unit]
Description=Alpaca Trading Bot
After=network.target

[Service]
Type=simple
User=$PI_USER
WorkingDirectory=$REMOTE_DIR
Environment=PATH=$REMOTE_DIR/$VENV_NAME/bin
ExecStart=$REMOTE_DIR/$VENV_NAME/bin/python src/alpaca_bot/main_headless.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE_EOF
        
        # Reload systemd and enable the service
        sudo systemctl daemon-reload
        sudo systemctl enable alpaca-bot.service
        
        echo "Fix completed successfully!"
EOF
    
    log_success "Pi installation fixed successfully!"
}

# Main function
main() {
    log_info "Starting Pi import fix..."
    
    check_connection
    fix_pi_installation
    
    log_success "Fix completed successfully!"
    echo
    log_info "Next steps:"
    echo "1. SSH to your Pi: ssh $PI_USER@$PI_HOST"
    echo "2. Test the fix: cd $REMOTE_DIR && ./start_bot.sh"
    echo "3. If working, start the service: sudo systemctl start alpaca-bot.service"
    echo "4. Check status: sudo systemctl status alpaca-bot.service"
}

# Run main function
main "$@"