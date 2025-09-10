#!/bin/bash

# Alpaca Bot - Raspberry Pi Deployment Script
# This script deploys the alpaca-bot to a Raspberry Pi with proper virtual environment setup

set -e  # Exit on any error

# Configuration
PI_USER="jarvis"
PI_HOST="jarvis.local"
REMOTE_DIR="/home/jarvis/alpaca-bot"
LOCAL_DIR="$(pwd)"
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

# Create remote directory structure
setup_remote_directory() {
    log_info "Setting up remote directory structure..."
    ssh "$PI_USER@$PI_HOST" << 'EOF'
        mkdir -p ~/alpaca-bot
        mkdir -p ~/alpaca-bot/logs
        mkdir -p ~/alpaca-bot/data
        mkdir -p ~/alpaca-bot/backups
EOF
    log_success "Remote directory structure created"
}

# Install system dependencies on Pi
install_system_dependencies() {
    log_info "Installing system dependencies on Raspberry Pi..."
    ssh "$PI_USER@$PI_HOST" << 'EOF'
        sudo apt update
        sudo apt install -y python3 python3-pip python3-venv git htop screen
        sudo apt install -y build-essential libssl-dev libffi-dev python3-dev
EOF
    log_success "System dependencies installed"
}

# Sync project files to Pi
sync_files() {
    log_info "Syncing project files to Raspberry Pi..."
    
    # Exclude unnecessary files
    rsync -avz --delete \
        --exclude='.git/' \
        --exclude='__pycache__/' \
        --exclude='*.pyc' \
        --exclude='.env' \
        --exclude='venv/' \
        --exclude='.trae/' \
        --exclude='*.log' \
        "$LOCAL_DIR/" "$PI_USER@$PI_HOST:$REMOTE_DIR/"
    
    log_success "Files synced successfully"
}

# Setup virtual environment and install dependencies
setup_virtual_environment() {
    log_info "Setting up virtual environment on Raspberry Pi..."
    ssh "$PI_USER@$PI_HOST" << EOF
        cd $REMOTE_DIR
        
        # Remove existing virtual environment if it exists
        if [ -d "$VENV_NAME" ]; then
            rm -rf "$VENV_NAME"
        fi
        
        # Create new virtual environment
        python3 -m venv "$VENV_NAME"
        
        # Activate virtual environment and install dependencies
        source "$VENV_NAME/bin/activate"
        
        # Upgrade pip
        pip install --upgrade pip
        
        # Install requirements (Pi-specific)
        if [ -f "requirements/pi.txt" ]; then
            pip install -r requirements/pi.txt
        elif [ -f "requirements/base.txt" ]; then
            pip install -r requirements/base.txt
        elif [ -f "requirements.txt" ]; then
            pip install -r requirements.txt
        else
            echo "No requirements file found"
        fi
EOF
    log_success "Virtual environment setup completed"
}

# Copy and setup environment file
setup_environment() {
    log_info "Setting up environment configuration..."
    
    # Copy .env.example to Pi and rename it
    if [ -f ".env.example" ]; then
        scp ".env.example" "$PI_USER@$PI_HOST:$REMOTE_DIR/.env"
        log_success "Environment file copied (please configure it on the Pi)"
    else
        log_warning "No .env.example file found"
    fi
}

# Create systemd service for auto-start
create_systemd_service() {
    log_info "Creating systemd service for auto-start..."
    
    # Create service file content
    cat > /tmp/alpaca-bot.service << EOF
[Unit]
Description=Alpaca Trading Bot
After=network.target

[Service]
Type=simple
User=$PI_USER
WorkingDirectory=$REMOTE_DIR
Environment=PATH=$REMOTE_DIR/$VENV_NAME/bin
ExecStart=$REMOTE_DIR/$VENV_NAME/bin/python src/alpaca_bot/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # Copy service file to Pi and enable it
    scp /tmp/alpaca-bot.service "$PI_USER@$PI_HOST:/tmp/"
    ssh "$PI_USER@$PI_HOST" << 'EOF'
        sudo mv /tmp/alpaca-bot.service /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable alpaca-bot.service
EOF
    
    rm /tmp/alpaca-bot.service
    log_success "Systemd service created and enabled"
}

# Create management scripts on Pi
create_management_scripts() {
    log_info "Creating management scripts on Raspberry Pi..."
    
    ssh "$PI_USER@$PI_HOST" << EOF
        cd $REMOTE_DIR
        
        # Create start script
        cat > start_bot.sh << 'SCRIPT_EOF'
#!/bin/bash
cd $REMOTE_DIR
source $VENV_NAME/bin/activate
python src/alpaca_bot/main.py
SCRIPT_EOF
        
        # Create stop script
        cat > stop_bot.sh << 'SCRIPT_EOF'
#!/bin/bash
sudo systemctl stop alpaca-bot.service
SCRIPT_EOF
        
        # Create status script
        cat > status_bot.sh << 'SCRIPT_EOF'
#!/bin/bash
sudo systemctl status alpaca-bot.service
SCRIPT_EOF
        
        # Create update script
        cat > update_bot.sh << 'SCRIPT_EOF'
#!/bin/bash
cd $REMOTE_DIR
git pull origin main
source $VENV_NAME/bin/activate
pip install -r requirements/base.txt
sudo systemctl restart alpaca-bot.service
SCRIPT_EOF
        
        # Make scripts executable
        chmod +x *.sh
EOF
    
    log_success "Management scripts created"
}

# Main deployment function
main() {
    log_info "Starting Alpaca Bot deployment to Raspberry Pi..."
    
    check_connection
    setup_remote_directory
    install_system_dependencies
    sync_files
    setup_virtual_environment
    setup_environment
    create_systemd_service
    create_management_scripts
    
    log_success "Deployment completed successfully!"
    echo
    log_info "Next steps:"
    echo "1. SSH to your Pi: ssh $PI_USER@$PI_HOST"
    echo "2. Configure your .env file: nano $REMOTE_DIR/.env"
    echo "3. Start the bot: sudo systemctl start alpaca-bot.service"
    echo "4. Check status: sudo systemctl status alpaca-bot.service"
    echo
    log_info "Management commands on Pi:"
    echo "- Start bot: ./start_bot.sh"
    echo "- Stop bot: ./stop_bot.sh"
    echo "- Check status: ./status_bot.sh"
    echo "- Update from git: ./update_bot.sh"
}

# Run main function
main "$@"