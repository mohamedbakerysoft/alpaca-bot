"""Raspberry Pi specific configuration and hardware management."""

import os
import logging
import psutil
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

try:
    import RPi.GPIO as GPIO
    import gpiozero
    PI_HARDWARE_AVAILABLE = True
except ImportError:
    PI_HARDWARE_AVAILABLE = False
    logging.warning("Pi hardware libraries not available. Running in simulation mode.")


@dataclass
class PiHardwareConfig:
    """Raspberry Pi hardware configuration."""
    status_led_pin: int = 18
    error_led_pin: int = 19
    trading_led_pin: int = 20
    monitor_cpu_temp: bool = True
    max_cpu_temp: float = 70.0
    enable_gpio: bool = True
    low_power_mode: bool = False


class PiSystemMonitor:
    """System monitoring for Raspberry Pi."""
    
    def __init__(self, config: PiHardwareConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._setup_gpio()
        
    def _setup_gpio(self) -> None:
        """Setup GPIO pins for status LEDs."""
        if not PI_HARDWARE_AVAILABLE or not self.config.enable_gpio:
            self.logger.info("GPIO setup skipped - hardware not available or disabled")
            return
            
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Setup LED pins
            GPIO.setup(self.config.status_led_pin, GPIO.OUT)
            GPIO.setup(self.config.error_led_pin, GPIO.OUT)
            GPIO.setup(self.config.trading_led_pin, GPIO.OUT)
            
            # Initialize LEDs (all off)
            self.set_status_led(False)
            self.set_error_led(False)
            self.set_trading_led(False)
            
            self.logger.info("GPIO setup completed successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to setup GPIO: {e}")
            
    def set_status_led(self, state: bool) -> None:
        """Control status LED."""
        if PI_HARDWARE_AVAILABLE and self.config.enable_gpio:
            try:
                GPIO.output(self.config.status_led_pin, GPIO.HIGH if state else GPIO.LOW)
            except Exception as e:
                self.logger.error(f"Failed to control status LED: {e}")
                
    def set_error_led(self, state: bool) -> None:
        """Control error LED."""
        if PI_HARDWARE_AVAILABLE and self.config.enable_gpio:
            try:
                GPIO.output(self.config.error_led_pin, GPIO.HIGH if state else GPIO.LOW)
            except Exception as e:
                self.logger.error(f"Failed to control error LED: {e}")
                
    def set_trading_led(self, state: bool) -> None:
        """Control trading LED."""
        if PI_HARDWARE_AVAILABLE and self.config.enable_gpio:
            try:
                GPIO.output(self.config.trading_led_pin, GPIO.HIGH if state else GPIO.LOW)
            except Exception as e:
                self.logger.error(f"Failed to control trading LED: {e}")
                
    def get_cpu_temperature(self) -> Optional[float]:
        """Get CPU temperature in Celsius."""
        try:
            # Try multiple methods to get CPU temperature
            temp_paths = [
                '/sys/class/thermal/thermal_zone0/temp',
                '/sys/devices/virtual/thermal/thermal_zone0/temp'
            ]
            
            for path in temp_paths:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        temp = float(f.read().strip()) / 1000.0
                        return temp
                        
            # Alternative method using vcgencmd
            import subprocess
            result = subprocess.run(['vcgencmd', 'measure_temp'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                temp_str = result.stdout.strip()
                temp = float(temp_str.split('=')[1].split("'")[0])
                return temp
                
        except Exception as e:
            self.logger.error(f"Failed to get CPU temperature: {e}")
            
        return None
        
    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        stats = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'cpu_temperature': self.get_cpu_temperature(),
            'uptime': self._get_uptime(),
            'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else None,
        }
        
        # Add network stats
        try:
            net_io = psutil.net_io_counters()
            stats['network'] = {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv
            }
        except Exception as e:
            self.logger.error(f"Failed to get network stats: {e}")
            
        return stats
        
    def _get_uptime(self) -> float:
        """Get system uptime in seconds."""
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
                return uptime_seconds
        except Exception:
            return 0.0
            
    def check_thermal_throttling(self) -> bool:
        """Check if the Pi is being thermally throttled."""
        if not self.config.monitor_cpu_temp:
            return False
            
        temp = self.get_cpu_temperature()
        if temp and temp > self.config.max_cpu_temp:
            self.logger.warning(f"CPU temperature high: {temp}°C")
            self.set_error_led(True)
            return True
            
        return False
        
    def optimize_for_pi(self) -> None:
        """Apply Pi-specific optimizations."""
        try:
            # Set CPU governor to performance when trading
            if os.path.exists('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor'):
                with open('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor', 'w') as f:
                    f.write('performance')
                    
            # Disable swap if low memory
            memory = psutil.virtual_memory()
            if memory.total < 1024 * 1024 * 1024:  # Less than 1GB
                os.system('sudo swapoff -a')
                self.logger.info("Swap disabled for low memory system")
                
        except Exception as e:
            self.logger.error(f"Failed to apply Pi optimizations: {e}")
            
    def cleanup(self) -> None:
        """Cleanup GPIO resources."""
        if PI_HARDWARE_AVAILABLE and self.config.enable_gpio:
            try:
                GPIO.cleanup()
                self.logger.info("GPIO cleanup completed")
            except Exception as e:
                self.logger.error(f"Failed to cleanup GPIO: {e}")


class PiConfigManager:
    """Configuration manager for Raspberry Pi deployment."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path.cwd() / '.env'
        self.logger = logging.getLogger(__name__)
        self.hardware_config = self._load_hardware_config()
        self.monitor = PiSystemMonitor(self.hardware_config)
        
    def _load_hardware_config(self) -> PiHardwareConfig:
        """Load hardware configuration from environment."""
        return PiHardwareConfig(
            status_led_pin=int(os.getenv('STATUS_LED_PIN', 18)),
            error_led_pin=int(os.getenv('ERROR_LED_PIN', 19)),
            trading_led_pin=int(os.getenv('TRADING_LED_PIN', 20)),
            monitor_cpu_temp=os.getenv('MONITOR_CPU_TEMP', 'true').lower() == 'true',
            max_cpu_temp=float(os.getenv('MAX_CPU_TEMP', 70.0)),
            enable_gpio=os.getenv('ENABLE_GPIO', 'true').lower() == 'true',
            low_power_mode=os.getenv('LOW_POWER_MODE', 'false').lower() == 'true'
        )
        
    def is_raspberry_pi(self) -> bool:
        """Check if running on Raspberry Pi."""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                return 'Raspberry Pi' in cpuinfo or 'BCM' in cpuinfo
        except Exception:
            return False
            
    def get_pi_model(self) -> Optional[str]:
        """Get Raspberry Pi model information."""
        try:
            with open('/proc/device-tree/model', 'r') as f:
                return f.read().strip('\x00')
        except Exception:
            return None
            
    def setup_logging_for_pi(self) -> None:
        """Setup Pi-optimized logging configuration."""
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        log_file = os.getenv('LOG_FILE', 'logs/alpaca_bot.log')
        
        # Create logs directory
        log_dir = Path(log_file).parent
        log_dir.mkdir(exist_ok=True)
        
        # Configure logging with rotation for limited storage
        from logging.handlers import RotatingFileHandler
        
        handler = RotatingFileHandler(
            log_file,
            maxBytes=int(os.getenv('LOG_MAX_SIZE', 10485760)),  # 10MB
            backupCount=int(os.getenv('LOG_BACKUP_COUNT', 5))
        )
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, log_level.upper()))
        logger.addHandler(handler)
        
    def create_health_check_endpoint(self) -> Dict[str, Any]:
        """Create health check data for monitoring."""
        stats = self.monitor.get_system_stats()
        
        health_data = {
            'status': 'healthy',
            'timestamp': psutil.boot_time(),
            'pi_model': self.get_pi_model(),
            'system_stats': stats,
            'thermal_throttling': self.monitor.check_thermal_throttling(),
            'hardware_available': PI_HARDWARE_AVAILABLE
        }
        
        # Determine overall health status
        if stats['cpu_percent'] > 90 or stats['memory_percent'] > 90:
            health_data['status'] = 'warning'
            
        if stats['cpu_temperature'] and stats['cpu_temperature'] > self.hardware_config.max_cpu_temp:
            health_data['status'] = 'critical'
            
        return health_data
        
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.monitor.cleanup()


# Global instance for easy access
pi_config = None

def get_pi_config() -> PiConfigManager:
    """Get global Pi configuration instance."""
    global pi_config
    if pi_config is None:
        pi_config = PiConfigManager()
    return pi_config


def initialize_pi_environment() -> None:
    """Initialize Raspberry Pi environment and optimizations."""
    config = get_pi_config()
    
    if config.is_raspberry_pi():
        logging.info(f"Running on Raspberry Pi: {config.get_pi_model()}")
        config.setup_logging_for_pi()
        config.monitor.optimize_for_pi()
        config.monitor.set_status_led(True)  # Indicate system is running
    else:
        logging.info("Not running on Raspberry Pi - Pi-specific features disabled")