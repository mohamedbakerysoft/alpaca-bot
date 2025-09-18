#!/bin/bash

# Alpaca Bot - Pi GUI Deployment Fix Script
# This script deploys the GUI version (main.py) to the Raspberry Pi

set -e  # Exit on any error

# Configuration
PI_USER="jarvis"
PI_HOST="jarvis.local"
REMOTE_DIR="/home/jarvis/alpaca-bot"
VENV_NAME="alpaca-venv"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Main deployment function
main() {
    log_info "Starting GUI version deployment to Raspberry Pi..."
    
    # Check connection
    check_connection
    
    # Copy the GUI main.py file to the Pi
    log_info "Deploying GUI version (main.py)..."
    scp "src/alpaca_bot/main.py" "$PI_USER@$PI_HOST:$REMOTE_DIR/src/alpaca_bot/"
    
    # Copy the entire GUI directory
    log_info "Copying GUI components..."
    scp -r "src/alpaca_bot/gui" "$PI_USER@$PI_HOST:$REMOTE_DIR/src/alpaca_bot/"
    
    # Copy environment file
    if [ -f ".env.pi" ]; then
        log_info "Copying Pi environment configuration..."
        scp ".env.pi" "$PI_USER@$PI_HOST:$REMOTE_DIR/.env"
    fi
    
    # Update start_bot.sh to use GUI version
    log_info "Creating startup script for GUI mode..."
    ssh "$PI_USER@$PI_HOST" "cd $REMOTE_DIR && cat > start_bot.sh << 'SCRIPT_EOF'
#!/bin/bash
cd $REMOTE_DIR
source $VENV_NAME/bin/activate
export DISPLAY=:0
python src/alpaca_bot/main.py
SCRIPT_EOF"
    
    # Make the script executable
    ssh "$PI_USER@$PI_HOST" "chmod +x $REMOTE_DIR/start_bot.sh"
    
    # Update systemd service for GUI mode
    log_info "Updating systemd service for GUI mode..."
    ssh "$PI_USER@$PI_HOST" "sudo tee /etc/systemd/system/alpaca-bot.service > /dev/null << 'SERVICE_EOF'
[Unit]
Description=Alpaca Trading Bot (GUI Mode)
After=network.target graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
User=$PI_USER
WorkingDirectory=$REMOTE_DIR
Environment=DISPLAY=:0
Environment=PYTHONPATH=$REMOTE_DIR/src
ExecStart=$REMOTE_DIR/$VENV_NAME/bin/python src/alpaca_bot/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=graphical.target
SERVICE_EOF"
    
    # Stop the service if it's running
    log_info "Stopping existing service..."
    ssh "$PI_USER@$PI_HOST" "sudo systemctl stop alpaca-bot.service || true"
    
    # Reload systemd and enable the service
    log_info "Reloading systemd configuration..."
    ssh "$PI_USER@$PI_HOST" "sudo systemctl daemon-reload"
    ssh "$PI_USER@$PI_HOST" "sudo systemctl enable alpaca-bot.service"
    
    # Test GUI imports
    log_info "Testing GUI imports on Pi..."
    if ssh "$PI_USER@$PI_HOST" "cd $REMOTE_DIR && source $VENV_NAME/bin/activate && python -c 'import sys; sys.path.insert(0, \"src\"); from alpaca_bot.main import main; print(\"GUI imports successful!\")'"; then
        log_success "GUI imports test passed!"
    else
        log_error "GUI imports test failed!"
        exit 1
    fi
    
    # Check if X11 is available for GUI
    log_info "Checking X11 display availability..."
    if ssh "$PI_USER@$PI_HOST" "DISPLAY=:0 xset q >/dev/null 2>&1"; then
        log_success "X11 display is available for GUI"
    else
        log_warning "X11 display not available. You may need to:"
        log_warning "1. Enable desktop environment on Pi"
        log_warning "2. Set up VNC or connect a monitor"
        log_warning "3. Use 'export DISPLAY=:0' before running"
    fi
    
    log_success "GUI deployment completed successfully!"
    echo ""
    log_info "Next steps:"
    echo "1. Connect to your Pi via SSH or VNC"
    echo "2. Test the GUI: cd $REMOTE_DIR && ./start_bot.sh"
    echo "3. Start the service: sudo systemctl start alpaca-bot.service"
    echo "4. Check status: sudo systemctl status alpaca-bot.service"
    echo ""
    log_info "For GUI access, ensure you have:"
    echo "- A desktop environment running on the Pi"
    echo "- VNC enabled, or a monitor connected"
    echo "- X11 forwarding enabled for SSH (ssh -X)"
}

# Run the main function
main "$@"