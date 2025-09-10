#!/bin/bash

# Alpaca Bot - Raspberry Pi Initial Installation Script
# This script sets up a fresh Raspberry Pi for the alpaca-bot application

set -e  # Exit on any error

# Configuration
PI_USER="jarvis"
PI_HOST="jarvis.local"
APP_NAME="alpaca-bot"
REPO_URL="https://github.com/yourusername/alpaca-bot.git"  # Update with your repo URL
REMOTE_DIR="/home/$PI_USER/$APP_NAME"
VENV_NAME="alpaca-venv"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

log_install() {
    echo -e "${PURPLE}[INSTALL]${NC} $1"
}

# Show usage
show_usage() {
    echo "Alpaca Bot - Raspberry Pi Installation Script"
    echo
    echo "This script will:"
    echo "1. Update the Raspberry Pi system"
    echo "2. Install required system packages"
    echo "3. Clone the alpaca-bot repository"
    echo "4. Set up Python virtual environment"
    echo "5. Install Python dependencies"
    echo "6. Configure systemd service"
    echo "7. Set up monitoring and management scripts"
    echo
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --repo-url URL    Git repository URL (default: $REPO_URL)"
    echo "  --branch BRANCH   Git branch to checkout (default: main)"
    echo "  --skip-update     Skip system update"
    echo "  --help            Show this help message"
    echo
    echo "Example:"
    echo "  $0 --repo-url https://github.com/myuser/alpaca-bot.git --branch develop"
    echo
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --repo-url)
                REPO_URL="$2"
                shift 2
                ;;
            --branch)
                BRANCH="$2"
                shift 2
                ;;
            --skip-update)
                SKIP_UPDATE=true
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Check if running on Raspberry Pi
check_pi_environment() {
    log_info "Checking if running on Raspberry Pi..."
    
    if [[ ! -f /proc/cpuinfo ]] || ! grep -q "Raspberry Pi\|BCM" /proc/cpuinfo; then
        log_error "This script must be run on a Raspberry Pi"
        exit 1
    fi
    
    local pi_model=$(cat /proc/device-tree/model 2>/dev/null | tr -d '\0' || echo "Unknown")
    log_success "Running on: $pi_model"
}

# Update system packages
update_system() {
    if [[ "$SKIP_UPDATE" == "true" ]]; then
        log_info "Skipping system update"
        return 0
    fi
    
    log_install "Updating system packages..."
    
    sudo apt update
    sudo apt upgrade -y
    
    log_success "System updated successfully"
}

# Install required system packages
install_system_packages() {
    log_install "Installing required system packages..."
    
    local packages=(
        "python3"
        "python3-pip"
        "python3-venv"
        "python3-dev"
        "git"
        "htop"
        "screen"
        "tmux"
        "curl"
        "wget"
        "build-essential"
        "libssl-dev"
        "libffi-dev"
        "sqlite3"
        "rsync"
        "nano"
        "vim"
    )
    
    sudo apt install -y "${packages[@]}"
    
    log_success "System packages installed successfully"
}

# Install Pi-specific packages
install_pi_packages() {
    log_install "Installing Raspberry Pi specific packages..."
    
    # Install GPIO libraries
    sudo apt install -y python3-rpi.gpio python3-gpiozero
    
    # Install monitoring tools
    sudo apt install -y lm-sensors
    
    log_success "Pi-specific packages installed"
}

# Clone repository
clone_repository() {
    log_install "Cloning repository from $REPO_URL..."
    
    # Remove existing directory if it exists
    if [[ -d "$REMOTE_DIR" ]]; then
        log_warning "Directory $REMOTE_DIR already exists, removing..."
        rm -rf "$REMOTE_DIR"
    fi
    
    # Clone repository
    git clone "$REPO_URL" "$REMOTE_DIR"
    
    # Checkout specific branch if specified
    if [[ -n "$BRANCH" ]]; then
        cd "$REMOTE_DIR"
        git checkout "$BRANCH"
        log_info "Checked out branch: $BRANCH"
    fi
    
    log_success "Repository cloned successfully"
}

# Setup Python virtual environment
setup_virtual_environment() {
    log_install "Setting up Python virtual environment..."
    
    cd "$REMOTE_DIR"
    
    # Create virtual environment
    python3 -m venv "$VENV_NAME"
    
    # Activate virtual environment
    source "$VENV_NAME/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install wheel for better package compilation
    pip install wheel
    
    log_success "Virtual environment created"
}

# Install Python dependencies
install_python_dependencies() {
    log_install "Installing Python dependencies..."
    
    cd "$REMOTE_DIR"
    source "$VENV_NAME/bin/activate"
    
    # Install dependencies based on available requirements files
    if [[ -f "requirements/pi.txt" ]]; then
        log_info "Installing Pi-specific requirements..."
        pip install -r requirements/pi.txt
    elif [[ -f "requirements/base.txt" ]]; then
        log_info "Installing base requirements..."
        pip install -r requirements/base.txt
    elif [[ -f "requirements.txt" ]]; then
        log_info "Installing requirements from requirements.txt..."
        pip install -r requirements.txt
    else
        log_warning "No requirements file found, skipping dependency installation"
    fi
    
    log_success "Python dependencies installed"
}

# Setup directory structure
setup_directories() {
    log_install "Setting up directory structure..."
    
    cd "$REMOTE_DIR"
    
    # Create necessary directories
    mkdir -p logs
    mkdir -p data
    mkdir -p backups
    mkdir -p config
    
    # Set proper permissions
    chmod 755 logs data backups config
    
    log_success "Directory structure created"
}

# Setup environment configuration
setup_environment_config() {
    log_install "Setting up environment configuration..."
    
    cd "$REMOTE_DIR"
    
    # Copy Pi-specific environment file if it exists
    if [[ -f ".env.pi" ]]; then
        cp ".env.pi" ".env"
        log_info "Copied .env.pi to .env"
    elif [[ -f ".env.example" ]]; then
        cp ".env.example" ".env"
        log_info "Copied .env.example to .env"
    else
        log_warning "No environment template found, creating basic .env file"
        cat > .env << 'EOF'
# Alpaca Bot Configuration
TRADING_MODE=ultra_safe
ENVIRONMENT=production
LOG_LEVEL=INFO
LOG_FILE=logs/alpaca_bot.log
DATABASE_URL=sqlite:///data/alpaca_bot.db
EOF
    fi
    
    log_success "Environment configuration setup completed"
    log_warning "Please edit .env file with your API keys and configuration"
}

# Create systemd service
create_systemd_service() {
    log_install "Creating systemd service..."
    
    # Create service file
    sudo tee /etc/systemd/system/alpaca-bot.service > /dev/null << EOF
[Unit]
Description=Alpaca Trading Bot
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$PI_USER
Group=$PI_USER
WorkingDirectory=$REMOTE_DIR
Environment=PATH=$REMOTE_DIR/$VENV_NAME/bin
ExecStart=$REMOTE_DIR/$VENV_NAME/bin/python src/alpaca_bot/main.py
Restart=always
RestartSec=10
KillMode=mixed
KillSignal=SIGINT
TimeoutStopSec=30

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=alpaca-bot

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$REMOTE_DIR

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable alpaca-bot.service
    
    log_success "Systemd service created and enabled"
}

# Create management scripts
create_management_scripts() {
    log_install "Creating management scripts..."
    
    cd "$REMOTE_DIR"
    
    # Start script
    cat > start_bot.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
sudo systemctl start alpaca-bot.service
echo "Bot started. Check status with: sudo systemctl status alpaca-bot.service"
EOF
    
    # Stop script
    cat > stop_bot.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
sudo systemctl stop alpaca-bot.service
echo "Bot stopped."
EOF
    
    # Status script
    cat > status_bot.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
echo "=== Service Status ==="
sudo systemctl status alpaca-bot.service --no-pager
echo
echo "=== Recent Logs ==="
sudo journalctl -u alpaca-bot.service -n 20 --no-pager
EOF
    
    # Update script
    cat > update_bot.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
echo "Updating alpaca-bot..."
sudo systemctl stop alpaca-bot.service
git pull origin main
source alpaca-venv/bin/activate
pip install -r requirements/pi.txt
sudo systemctl start alpaca-bot.service
echo "Update completed. Checking status..."
sleep 3
sudo systemctl status alpaca-bot.service --no-pager
EOF
    
    # Logs script
    cat > logs_bot.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
echo "=== Live Logs (Ctrl+C to exit) ==="
sudo journalctl -u alpaca-bot.service -f
EOF
    
    # Health check script
    cat > health_bot.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
echo "=== System Health ==="
echo "Uptime: $(uptime -p)"
echo "Memory: $(free -h | grep Mem | awk '{print $3"/"$2}')"
echo "Disk: $(df -h / | tail -1 | awk '{print $3"/"$2" ("$5" used)"}')"
if command -v vcgencmd >/dev/null 2>&1; then
    echo "CPU Temp: $(vcgencmd measure_temp | cut -d= -f2)"
fi
echo
echo "=== Service Status ==="
sudo systemctl is-active alpaca-bot.service
echo
echo "=== Recent Errors ==="
sudo journalctl -u alpaca-bot.service -p err -n 5 --no-pager
EOF
    
    # Make all scripts executable
    chmod +x *.sh
    
    log_success "Management scripts created"
}

# Setup log rotation
setup_log_rotation() {
    log_install "Setting up log rotation..."
    
    sudo tee /etc/logrotate.d/alpaca-bot > /dev/null << EOF
$REMOTE_DIR/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 $PI_USER $PI_USER
    postrotate
        sudo systemctl reload alpaca-bot.service > /dev/null 2>&1 || true
    endscript
}
EOF
    
    log_success "Log rotation configured"
}

# Final setup and verification
final_setup() {
    log_install "Performing final setup..."
    
    cd "$REMOTE_DIR"
    
    # Set proper ownership
    sudo chown -R "$PI_USER:$PI_USER" "$REMOTE_DIR"
    
    # Test virtual environment
    source "$VENV_NAME/bin/activate"
    python --version
    pip list | head -5
    
    log_success "Installation completed successfully!"
}

# Show post-installation instructions
show_post_install_instructions() {
    echo
    log_success "=== Installation Complete ==="
    echo
    log_info "Next steps:"
    echo "1. Edit configuration: nano $REMOTE_DIR/.env"
    echo "2. Add your Alpaca API keys to the .env file"
    echo "3. Test the application: cd $REMOTE_DIR && ./start_bot.sh"
    echo "4. Check status: ./status_bot.sh"
    echo "5. View logs: ./logs_bot.sh"
    echo
    log_info "Management commands:"
    echo "- Start:  ./start_bot.sh"
    echo "- Stop:   ./stop_bot.sh"
    echo "- Status: ./status_bot.sh"
    echo "- Update: ./update_bot.sh"
    echo "- Logs:   ./logs_bot.sh"
    echo "- Health: ./health_bot.sh"
    echo
    log_info "Service commands:"
    echo "- sudo systemctl start alpaca-bot.service"
    echo "- sudo systemctl stop alpaca-bot.service"
    echo "- sudo systemctl status alpaca-bot.service"
    echo "- sudo systemctl enable alpaca-bot.service"
    echo
    log_warning "Remember to:"
    echo "- Configure your .env file with API keys"
    echo "- Test in paper trading mode first"
    echo "- Monitor the logs for any issues"
    echo "- Set up proper firewall rules if needed"
    echo
}

# Main installation function
main() {
    log_install "Starting Alpaca Bot installation on Raspberry Pi..."
    
    check_pi_environment
    update_system
    install_system_packages
    install_pi_packages
    clone_repository
    setup_directories
    setup_virtual_environment
    install_python_dependencies
    setup_environment_config
    create_systemd_service
    create_management_scripts
    setup_log_rotation
    final_setup
    show_post_install_instructions
    
    log_success "Alpaca Bot installation completed successfully!"
}

# Parse arguments and run main function
parse_args "$@"
main