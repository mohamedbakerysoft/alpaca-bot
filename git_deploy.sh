#!/bin/bash

# Alpaca Bot - Git Deployment Workflow Script
# This script handles Git operations and deployment to Raspberry Pi

set -e  # Exit on any error

# Configuration
PI_USER="jarvis"
PI_HOST="jarvis.local"
REMOTE_DIR="/home/jarvis/alpaca-bot"
DEFAULT_BRANCH="main"
BACKUP_DIR="backups"

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

log_deploy() {
    echo -e "${PURPLE}[DEPLOY]${NC} $1"
}

# Show usage information
show_usage() {
    echo "Alpaca Bot Git Deployment Script"
    echo
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo
    echo "Commands:"
    echo "  push [message]     - Add, commit, and push changes to Git"
    echo "  deploy [branch]    - Deploy specific branch to Pi (default: main)"
    echo "  quick [message]    - Quick deploy: push to Git and deploy to Pi"
    echo "  status             - Show Git and Pi deployment status"
    echo "  rollback [commit]  - Rollback Pi deployment to specific commit"
    echo "  backup             - Create backup of current Pi deployment"
    echo "  logs               - Show Pi application logs"
    echo "  restart            - Restart application on Pi"
    echo "  health             - Check Pi system health"
    echo "  setup-hooks        - Setup Git hooks for automated deployment"
    echo
    echo "Examples:"
    echo "  $0 push 'Fix trading algorithm bug'"
    echo "  $0 deploy develop"
    echo "  $0 quick 'Update risk management'"
    echo "  $0 rollback abc1234"
    echo
}

# Check if Git repository is clean
check_git_status() {
    if [[ -n $(git status --porcelain) ]]; then
        log_warning "Working directory has uncommitted changes"
        git status --short
        return 1
    fi
    return 0
}

# Push changes to Git
push_to_git() {
    local commit_message="$1"
    
    if [[ -z "$commit_message" ]]; then
        log_error "Commit message is required"
        return 1
    fi
    
    log_info "Preparing to push changes to Git..."
    
    # Check for changes
    if [[ -z $(git status --porcelain) ]]; then
        log_warning "No changes to commit"
        return 0
    fi
    
    # Add all changes
    git add .
    log_info "Added all changes to staging"
    
    # Commit changes
    git commit -m "$commit_message"
    log_info "Committed changes: $commit_message"
    
    # Push to remote
    local current_branch=$(git branch --show-current)
    git push origin "$current_branch"
    log_success "Pushed changes to origin/$current_branch"
    
    return 0
}

# Deploy to Raspberry Pi
deploy_to_pi() {
    local branch="${1:-$DEFAULT_BRANCH}"
    
    log_deploy "Starting deployment to Raspberry Pi..."
    log_info "Branch: $branch"
    
    # Check Pi connectivity
    if ! ssh -o ConnectTimeout=5 "$PI_USER@$PI_HOST" "echo 'Connected'" >/dev/null 2>&1; then
        log_error "Cannot connect to Raspberry Pi at $PI_HOST"
        return 1
    fi
    
    # Create backup before deployment
    create_backup
    
    # Deploy to Pi
    ssh "$PI_USER@$PI_HOST" << EOF
        set -e
        cd "$REMOTE_DIR"
        
        # Stop the service
        sudo systemctl stop alpaca-bot.service || true
        
        # Fetch latest changes
        git fetch origin
        
        # Checkout and pull the specified branch
        git checkout "$branch"
        git pull origin "$branch"
        
        # Activate virtual environment and update dependencies
        source alpaca-venv/bin/activate
        
        # Update requirements if they changed
        if git diff HEAD~1 --name-only | grep -q requirements; then
            echo "Requirements changed, updating..."
            pip install -r requirements/pi.txt
        fi
        
        # Run any migration scripts if they exist
        if [ -f "scripts/migrate.py" ]; then
            python scripts/migrate.py
        fi
        
        # Start the service
        sudo systemctl start alpaca-bot.service
        
        # Check if service started successfully
        sleep 3
        if sudo systemctl is-active --quiet alpaca-bot.service; then
            echo "Service started successfully"
        else
            echo "Service failed to start"
            sudo systemctl status alpaca-bot.service
            exit 1
        fi
EOF
    
    if [[ $? -eq 0 ]]; then
        log_success "Deployment completed successfully"
        show_deployment_status
    else
        log_error "Deployment failed"
        return 1
    fi
}

# Quick deploy: push and deploy in one command
quick_deploy() {
    local commit_message="$1"
    local branch="${2:-$DEFAULT_BRANCH}"
    
    if [[ -z "$commit_message" ]]; then
        log_error "Commit message is required for quick deploy"
        return 1
    fi
    
    log_deploy "Starting quick deployment..."
    
    # Push to Git
    if push_to_git "$commit_message"; then
        # Deploy to Pi
        deploy_to_pi "$branch"
    else
        log_error "Failed to push to Git, aborting deployment"
        return 1
    fi
}

# Show status
show_status() {
    log_info "Git Status:"
    echo "Current branch: $(git branch --show-current)"
    echo "Last commit: $(git log -1 --oneline)"
    echo "Remote status: $(git status -uno --porcelain | wc -l) files changed"
    echo
    
    log_info "Raspberry Pi Status:"
    if ssh -o ConnectTimeout=5 "$PI_USER@$PI_HOST" "echo 'Connected'" >/dev/null 2>&1; then
        ssh "$PI_USER@$PI_HOST" << 'EOF'
            cd /home/jarvis/alpaca-bot
            echo "Pi branch: $(git branch --show-current)"
            echo "Pi commit: $(git log -1 --oneline)"
            echo "Service status: $(sudo systemctl is-active alpaca-bot.service)"
            echo "Uptime: $(uptime -p)"
EOF
    else
        log_error "Cannot connect to Raspberry Pi"
    fi
}

# Show deployment status
show_deployment_status() {
    log_info "Deployment Status:"
    ssh "$PI_USER@$PI_HOST" << 'EOF'
        cd /home/jarvis/alpaca-bot
        echo "Deployed commit: $(git log -1 --oneline)"
        echo "Service status: $(sudo systemctl is-active alpaca-bot.service)"
        echo "Last deployment: $(stat -c %y .git/FETCH_HEAD 2>/dev/null || echo 'Unknown')"
EOF
}

# Create backup
create_backup() {
    log_info "Creating backup on Raspberry Pi..."
    
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    
    ssh "$PI_USER@$PI_HOST" << EOF
        cd "$REMOTE_DIR"
        
        # Create backup directory if it doesn't exist
        mkdir -p "$BACKUP_DIR"
        
        # Create backup
        tar -czf "$BACKUP_DIR/backup_\${timestamp}.tar.gz" \
            --exclude="$BACKUP_DIR" \
            --exclude="alpaca-venv" \
            --exclude=".git" \
            --exclude="__pycache__" \
            --exclude="*.pyc" \
            --exclude="logs/*.log" \
            .
        
        echo "Backup created: $BACKUP_DIR/backup_\${timestamp}.tar.gz"
        
        # Keep only last 5 backups
        cd "$BACKUP_DIR"
        ls -t backup_*.tar.gz | tail -n +6 | xargs -r rm
EOF
    
    log_success "Backup created successfully"
}

# Rollback deployment
rollback_deployment() {
    local commit_hash="$1"
    
    if [[ -z "$commit_hash" ]]; then
        log_error "Commit hash is required for rollback"
        return 1
    fi
    
    log_warning "Rolling back to commit: $commit_hash"
    
    # Create backup before rollback
    create_backup
    
    ssh "$PI_USER@$PI_HOST" << EOF
        set -e
        cd "$REMOTE_DIR"
        
        # Stop service
        sudo systemctl stop alpaca-bot.service
        
        # Rollback to specified commit
        git checkout "$commit_hash"
        
        # Update dependencies if needed
        source alpaca-venv/bin/activate
        pip install -r requirements/pi.txt
        
        # Start service
        sudo systemctl start alpaca-bot.service
EOF
    
    log_success "Rollback completed"
    show_deployment_status
}

# Show application logs
show_logs() {
    log_info "Showing Raspberry Pi application logs..."
    
    ssh "$PI_USER@$PI_HOST" << 'EOF'
        # Show systemd logs
        echo "=== Systemd Service Logs ==="
        sudo journalctl -u alpaca-bot.service -n 50 --no-pager
        
        echo
        echo "=== Application Logs ==="
        if [ -f "/home/jarvis/alpaca-bot/logs/alpaca_bot.log" ]; then
            tail -50 "/home/jarvis/alpaca-bot/logs/alpaca_bot.log"
        else
            echo "No application log file found"
        fi
EOF
}

# Restart application
restart_application() {
    log_info "Restarting application on Raspberry Pi..."
    
    ssh "$PI_USER@$PI_HOST" << 'EOF'
        sudo systemctl restart alpaca-bot.service
        sleep 3
        sudo systemctl status alpaca-bot.service
EOF
    
    log_success "Application restarted"
}

# Check system health
check_health() {
    log_info "Checking Raspberry Pi system health..."
    
    ssh "$PI_USER@$PI_HOST" << 'EOF'
        echo "=== System Information ==="
        uptime
        echo
        
        echo "=== Memory Usage ==="
        free -h
        echo
        
        echo "=== Disk Usage ==="
        df -h /
        echo
        
        echo "=== CPU Temperature ==="
        if command -v vcgencmd >/dev/null 2>&1; then
            vcgencmd measure_temp
        else
            echo "vcgencmd not available"
        fi
        echo
        
        echo "=== Service Status ==="
        sudo systemctl status alpaca-bot.service --no-pager
EOF
}

# Setup Git hooks
setup_git_hooks() {
    log_info "Setting up Git hooks for automated deployment..."
    
    # Create post-commit hook
    cat > .git/hooks/post-commit << 'EOF'
#!/bin/bash
# Auto-deploy to Pi after commit (optional)
# Uncomment the line below to enable auto-deployment
# ./git_deploy.sh deploy
EOF
    
    chmod +x .git/hooks/post-commit
    
    log_success "Git hooks setup completed"
    log_info "Edit .git/hooks/post-commit to enable auto-deployment"
}

# Main function
main() {
    local command="$1"
    shift
    
    case "$command" in
        "push")
            push_to_git "$1"
            ;;
        "deploy")
            deploy_to_pi "$1"
            ;;
        "quick")
            quick_deploy "$1" "$2"
            ;;
        "status")
            show_status
            ;;
        "rollback")
            rollback_deployment "$1"
            ;;
        "backup")
            create_backup
            ;;
        "logs")
            show_logs
            ;;
        "restart")
            restart_application
            ;;
        "health")
            check_health
            ;;
        "setup-hooks")
            setup_git_hooks
            ;;
        "help"|"--help"|"-h"|"")
            show_usage
            ;;
        *)
            log_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"