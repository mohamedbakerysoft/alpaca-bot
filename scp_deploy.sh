#!/bin/bash

# SCP-based Deployment Script for Alpaca Trading Bot
# This script uses SCP to copy files directly to the Pi and manages package installation efficiently

set -e  # Exit on any error

# Configuration
PI_USER="jarvis"
PI_HOST="jarvis.local"
REMOTE_DIR="/home/jarvis/alpaca-bot"
LOCAL_SRC_DIR="src"
LOCAL_REQUIREMENTS_DIR="requirements"
SERVICE_NAME="alpaca-bot.service"

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

log_deploy() {
    echo -e "${GREEN}[DEPLOY]${NC} $1"
}

# Function to check Pi connectivity
check_pi_connectivity() {
    log_info "Checking Pi connectivity..."
    if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "$PI_USER@$PI_HOST" "echo 'Connected'" >/dev/null 2>&1; then
        log_error "Cannot connect to Raspberry Pi at $PI_HOST"
        log_error "Please ensure:"
        log_error "  1. Pi is powered on and connected to network"
        log_error "  2. SSH is enabled on the Pi"
        log_error "  3. SSH keys are properly configured"
        return 1
    fi
    log_success "Pi connectivity verified"
    return 0
}

# Function to get file checksums for comparison
get_local_checksums() {
    log_info "Calculating local file checksums..."
    
    # Create temporary file for checksums
    local checksum_file="/tmp/alpaca_local_checksums.txt"
    > "$checksum_file"
    
    # Calculate checksums for source files
    if [ -d "$LOCAL_SRC_DIR" ]; then
        find "$LOCAL_SRC_DIR" -type f -name "*.py" -exec md5sum {} \; >> "$checksum_file"
    fi
    
    # Calculate checksums for requirements files
    if [ -d "$LOCAL_REQUIREMENTS_DIR" ]; then
        find "$LOCAL_REQUIREMENTS_DIR" -type f -name "*.txt" -exec md5sum {} \; >> "$checksum_file"
    fi
    
    # Calculate checksums for other important files
    for file in "pyproject.toml" ".env.pi" "install_pi.sh" "start_bot.sh" "stop_bot.sh" "status_bot.sh"; do
        if [ -f "$file" ]; then
            md5sum "$file" >> "$checksum_file"
        fi
    done
    
    echo "$checksum_file"
}

# Function to get remote checksums
get_remote_checksums() {
    log_info "Getting remote file checksums..."
    
    local remote_checksums
    remote_checksums=$(ssh "$PI_USER@$PI_HOST" << 'EOF'
        cd /home/jarvis/alpaca-bot 2>/dev/null || cd /home/jarvis
        checksum_file="/tmp/alpaca_remote_checksums.txt"
        > "$checksum_file"
        
        # Calculate checksums for source files
        if [ -d "alpaca-bot/src" ]; then
            find alpaca-bot/src -type f -name "*.py" -exec md5sum {} \; >> "$checksum_file" 2>/dev/null || true
        elif [ -d "src" ]; then
            find src -type f -name "*.py" -exec md5sum {} \; >> "$checksum_file" 2>/dev/null || true
        fi
        
        # Calculate checksums for requirements files
        if [ -d "alpaca-bot/requirements" ]; then
            find alpaca-bot/requirements -type f -name "*.txt" -exec md5sum {} \; >> "$checksum_file" 2>/dev/null || true
        elif [ -d "requirements" ]; then
            find requirements -type f -name "*.txt" -exec md5sum {} \; >> "$checksum_file" 2>/dev/null || true
        fi
        
        # Calculate checksums for other important files
        for file in "pyproject.toml" ".env.pi" "install_pi.sh" "start_bot.sh" "stop_bot.sh" "status_bot.sh"; do
            if [ -f "alpaca-bot/$file" ]; then
                md5sum "alpaca-bot/$file" >> "$checksum_file" 2>/dev/null || true
            elif [ -f "$file" ]; then
                md5sum "$file" >> "$checksum_file" 2>/dev/null || true
            fi
        done
        
        cat "$checksum_file" 2>/dev/null || echo ""
EOF
)
    echo "$remote_checksums"
}

# Function to compare checksums and determine what needs updating
compare_checksums() {
    local local_checksums="$1"
    local remote_checksums="$2"
    
    log_info "Comparing file checksums to determine changes..."
    
    # Create temporary files for comparison
    local sorted_local="/tmp/sorted_local.txt"
    local sorted_remote="/tmp/sorted_remote.txt"
    
    # Sort checksums by filename for comparison
    if [ -f "$local_checksums" ]; then
        sort "$local_checksums" > "$sorted_local"
    else
        touch "$sorted_local"
    fi
    
    if [ -n "$remote_checksums" ]; then
        echo "$remote_checksums" | sort > "$sorted_remote"
    else
        touch "$sorted_remote"
    fi
    
    # Find differences
    local changes_detected=false
    local requirements_changed=false
    
    # If remote is empty, we definitely have changes
    if [ ! -s "$sorted_remote" ]; then
        changes_detected=true
        requirements_changed=true
        log_info "Remote checksums empty - full deployment needed"
    elif ! diff -q "$sorted_local" "$sorted_remote" >/dev/null 2>&1; then
        changes_detected=true
        log_info "File changes detected:"
        
        # Check specifically for requirements changes
        if diff "$sorted_local" "$sorted_remote" 2>/dev/null | grep -q "requirements/" || [ ! -s "$sorted_remote" ]; then
            requirements_changed=true
            log_warning "Requirements files have changed - package installation will be performed"
        fi
        
        # Show what changed (limit output)
        diff "$sorted_local" "$sorted_remote" 2>/dev/null | grep "^[<>]" | head -10 || true
    else
        log_info "No file changes detected"
    fi
    
    # Cleanup
    rm -f "$sorted_local" "$sorted_remote"
    
    # Return status: 0=no changes, 1=changes but no requirements, 2=requirements changed
    if [ "$changes_detected" = false ]; then
        return 0
    elif [ "$requirements_changed" = true ]; then
        return 2
    else
        return 1
    fi
}

# Function to copy files to Pi
copy_files_to_pi() {
    log_deploy "Copying files to Pi..."
    
    # Stop the service before copying files
    log_info "Stopping alpaca-bot service..."
    ssh "$PI_USER@$PI_HOST" "sudo systemctl stop $SERVICE_NAME || true"
    
    # Copy source directory
    if [ -d "$LOCAL_SRC_DIR" ]; then
        log_info "Copying source files..."
        scp -r "$LOCAL_SRC_DIR" "$PI_USER@$PI_HOST:$REMOTE_DIR/"
    fi
    
    # Copy requirements directory
    if [ -d "$LOCAL_REQUIREMENTS_DIR" ]; then
        log_info "Copying requirements files..."
        scp -r "$LOCAL_REQUIREMENTS_DIR" "$PI_USER@$PI_HOST:$REMOTE_DIR/"
    fi
    
    # Copy other important files
    for file in "pyproject.toml" ".env.pi" "install_pi.sh" "start_bot.sh" "stop_bot.sh" "status_bot.sh"; do
        if [ -f "$file" ]; then
            log_info "Copying $file..."
            scp "$file" "$PI_USER@$PI_HOST:$REMOTE_DIR/"
        fi
    done
    
    log_success "Files copied successfully"
}

# Function to install packages on Pi
install_packages() {
    log_deploy "Installing/updating packages on Pi..."
    
    ssh "$PI_USER@$PI_HOST" << EOF
        set -e
        cd "$REMOTE_DIR"
        
        # Activate virtual environment
        if [ -d "alpaca-venv" ]; then
            source alpaca-venv/bin/activate
            echo "Virtual environment activated"
        else
            echo "Creating virtual environment..."
            python3 -m venv alpaca-venv
            source alpaca-venv/bin/activate
        fi
        
        # Upgrade pip
        pip install --upgrade pip
        
        # Install requirements
        if [ -f "requirements/pi.txt" ]; then
            echo "Installing requirements from pi.txt..."
            pip install -r requirements/pi.txt
        elif [ -f "requirements/base.txt" ]; then
            echo "Installing requirements from base.txt..."
            pip install -r requirements/base.txt
        else
            echo "No requirements file found"
        fi
        
        echo "Package installation completed"
EOF
    
    log_success "Package installation completed"
}

# Function to start the service
start_service() {
    log_info "Starting alpaca-bot service..."
    
    ssh "$PI_USER@$PI_HOST" << EOF
        # Make scripts executable
        cd "$REMOTE_DIR"
        chmod +x *.sh 2>/dev/null || true
        
        # Start the service
        sudo systemctl start $SERVICE_NAME
        
        # Wait a moment for service to start
        sleep 3
        
        # Check service status
        sudo systemctl status $SERVICE_NAME --no-pager -l
EOF
    
    log_success "Service started"
}

# Function to show deployment status
show_status() {
    log_info "Deployment Status:"
    
    ssh "$PI_USER@$PI_HOST" << EOF
        cd "$REMOTE_DIR"
        echo "Pi system info:"
        uname -a
        echo ""
        echo "Service status:"
        sudo systemctl is-active $SERVICE_NAME || echo "Service not active"
        echo ""
        echo "Last deployment: \$(date)"
        echo ""
        echo "Recent logs:"
        sudo journalctl -u $SERVICE_NAME --since "1 minute ago" --no-pager | tail -5 || echo "No recent logs"
EOF
}

# Main deployment function
deploy() {
    local force_packages="$1"
    
    log_deploy "Starting SCP-based deployment to Raspberry Pi..."
    
    # Check connectivity
    if ! check_pi_connectivity; then
        return 1
    fi
    
    # Get checksums
    local local_checksums
    local_checksums=$(get_local_checksums)
    local remote_checksums
    remote_checksums=$(get_remote_checksums)
    
    # Compare checksums
    local comparison_result
    compare_checksums "$local_checksums" "$remote_checksums"
    comparison_result=$?
    
    case $comparison_result in
        0)
            if [ "$force_packages" != "force" ]; then
                log_info "No changes detected. Use 'force' to deploy anyway."
                return 0
            else
                log_warning "Forcing deployment despite no changes detected"
            fi
            ;;
        1)
            log_info "File changes detected, copying files..."
            copy_files_to_pi
            ;;
        2)
            log_info "Requirements changes detected, copying files and updating packages..."
            copy_files_to_pi
            install_packages
            ;;
    esac
    
    # If force_packages is specified, always install packages
    if [ "$force_packages" = "force-packages" ] || [ "$force_packages" = "force" ]; then
        install_packages
    fi
    
    # Start the service
    start_service
    
    # Show status
    show_status
    
    # Cleanup
    rm -f "$local_checksums"
    
    log_success "Deployment completed successfully"
    return 0
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  deploy              Deploy changes to Pi (smart deployment based on file changes)"
    echo "  deploy force        Force deployment even if no changes detected"
    echo "  deploy force-packages  Deploy and force package installation"
    echo "  status              Show Pi and service status"
    echo "  copy-only           Copy files without package installation or service restart"
    echo "  packages-only       Install packages only (no file copying)"
    echo "  restart             Restart the service only"
    echo ""
    echo "Examples:"
    echo "  $0 deploy                    # Smart deployment"
    echo "  $0 deploy force             # Force full deployment"
    echo "  $0 deploy force-packages    # Force package installation"
    echo "  $0 status                   # Check status"
    echo "  $0 copy-only               # Copy files only"
    echo "  $0 packages-only           # Install packages only"
    echo "  $0 restart                 # Restart service"
}

# Main script logic
case "${1:-}" in
    "deploy")
        deploy "$2"
        ;;
    "status")
        check_pi_connectivity && show_status
        ;;
    "copy-only")
        check_pi_connectivity && copy_files_to_pi
        ;;
    "packages-only")
        check_pi_connectivity && install_packages
        ;;
    "restart")
        check_pi_connectivity && start_service
        ;;
    "help"|"-h"|"--help")
        show_usage
        ;;
    *)
        log_error "Invalid command: ${1:-}"
        echo ""
        show_usage
        exit 1
        ;;
esac