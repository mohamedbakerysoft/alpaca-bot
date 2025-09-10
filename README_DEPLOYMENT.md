# Alpaca Bot - Raspberry Pi Deployment Guide

## Overview

This guide covers setting up the Alpaca Bot for development on macOS and deployment to a Raspberry Pi using a professional, lightweight setup with virtual environments.

## Prerequisites

### On macOS (Development Machine)
- Python 3.8+
- Git
- SSH access to Raspberry Pi
- Virtual environment (venv or conda)

### On Raspberry Pi
- Raspberry Pi OS (Bullseye or newer)
- SSH enabled
- Internet connection
- At least 1GB free space

## Initial Setup

### 1. SSH Key Setup (Already Completed)

Passwordless SSH should already be configured. Test with:
```bash
ssh jarvis@jarvis.local
```

### 2. First-Time Pi Installation

Copy the installation script to your Pi and run it:

```bash
# From your Mac
scp install_pi.sh jarvis@jarvis.local:~/
ssh jarvis@jarvis.local

# On the Pi
chmod +x install_pi.sh
./install_pi.sh
```

This will:
- Update the system
- Install required packages
- Clone the repository
- Set up Python virtual environment
- Install dependencies
- Configure systemd service
- Set up log rotation

## Development Workflow

### Local Development on Mac

1. **Make changes** to your code locally
2. **Test locally** in your development environment
3. **Commit and push** to Git:
   ```bash
   git add .
   git commit -m "Your commit message"
   git push origin main
   ```

### Deployment to Raspberry Pi

Use the Git deployment script for easy updates:

```bash
# Deploy latest changes
./git_deploy.sh deploy

# Quick deploy (skip dependency updates)
./git_deploy.sh quick

# Check status
./git_deploy.sh status

# View logs
./git_deploy.sh logs

# Restart service
./git_deploy.sh restart
```

## Available Scripts

### `install_pi.sh`
- **Purpose**: Initial setup on Raspberry Pi
- **Usage**: Run once on the Pi for first-time installation
- **Features**: System setup, dependency installation, service configuration

### `deploy_to_pi.sh`
- **Purpose**: Deploy code changes to Pi
- **Usage**: `./deploy_to_pi.sh` (from Mac)
- **Features**: Sync files, update dependencies, restart services

### `git_deploy.sh`
- **Purpose**: Git-based deployment workflow
- **Usage**: Various commands for deployment and management
- **Commands**:
  - `deploy`: Full deployment with dependency updates
  - `quick`: Quick deployment without dependency updates
  - `status`: Check service status
  - `logs`: View application logs
  - `restart`: Restart the service
  - `rollback`: Rollback to previous version
  - `backup`: Create backup
  - `health`: Health check

## Configuration Files

### `.env.pi`
Pi-specific environment configuration with optimized settings for:
- Trading mode (ultra_safe by default)
- Resource limits
- Logging levels
- Performance tuning

### `requirements/pi.txt`
Lightweight dependencies optimized for Raspberry Pi:
- ARM-compatible packages
- Reduced memory footprint
- Pi-specific hardware libraries (GPIO, etc.)

### `src/alpaca_bot/config/pi_config.py`
Pi-specific configuration module with:
- Hardware monitoring
- Thermal management
- GPIO configuration
- Performance optimization

## Service Management

The bot runs as a systemd service on the Pi:

```bash
# Check status
sudo systemctl status alpaca-bot

# Start service
sudo systemctl start alpaca-bot

# Stop service
sudo systemctl stop alpaca-bot

# Restart service
sudo systemctl restart alpaca-bot

# View logs
journalctl -u alpaca-bot -f
```

## Monitoring and Logs

### Log Files
- Application logs: `/home/jarvis/alpaca-bot/logs/`
- System logs: `journalctl -u alpaca-bot`
- Deployment logs: `/home/jarvis/alpaca-bot/deploy.log`

### Health Monitoring
```bash
# Check system resources
./git_deploy.sh health

# Monitor in real-time
htop

# Check temperature
vcgencmd measure_temp
```

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   chmod +x *.sh
   ```

2. **Service Won't Start**
   ```bash
   sudo systemctl status alpaca-bot
   journalctl -u alpaca-bot --no-pager
   ```

3. **Dependency Issues**
   ```bash
   # On Pi
   cd ~/alpaca-bot
   source venv/bin/activate
   pip install -r requirements/pi.txt
   ```

4. **SSH Connection Issues**
   ```bash
   ssh-keygen -R jarvis.local
   ssh jarvis@jarvis.local
   ```

### Performance Optimization

1. **Memory Usage**
   - Monitor with `free -h`
   - Adjust `MAX_MEMORY_MB` in `.env.pi`

2. **CPU Temperature**
   - Monitor with `vcgencmd measure_temp`
   - Ensure proper cooling
   - Adjust `THERMAL_THROTTLE_TEMP` in config

3. **Storage Space**
   - Monitor with `df -h`
   - Log rotation is configured automatically

## Security Considerations

- Environment files (`.env*`) are not committed to Git
- SSH keys are used for authentication
- Service runs with limited privileges
- Logs are rotated to prevent disk filling
- Firewall configuration recommended

## Backup and Recovery

### Create Backup
```bash
./git_deploy.sh backup
```

### Restore from Backup
```bash
./git_deploy.sh rollback
```

### Manual Backup
```bash
# On Pi
tar -czf ~/alpaca-bot-backup-$(date +%Y%m%d).tar.gz ~/alpaca-bot
```

## Development Tips

1. **Test locally first** before deploying
2. **Use feature branches** for experimental changes
3. **Monitor Pi resources** during development
4. **Keep commits small** for easier rollbacks
5. **Use the quick deploy** for minor changes
6. **Check logs regularly** for issues

## Support

For issues:
1. Check the logs first
2. Verify SSH connectivity
3. Ensure Pi has sufficient resources
4. Check service status
5. Review recent changes in Git history

---

**Note**: This setup uses virtual environments (venv) to keep the system clean and professional. All dependencies are isolated within the project environment.