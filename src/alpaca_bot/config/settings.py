"""Configuration management for Alpaca Trading Bot.

This module handles secure configuration management using environment variables
and .env files for API keys and application settings.
"""

import os
from pathlib import Path
from typing import Optional, Tuple, Dict

from decouple import config


class Settings:
    """Application settings with secure configuration management."""

    def __init__(self) -> None:
        """Initialize settings from environment variables."""
        # Alpaca API Configuration
        self.alpaca_api_key: str = config(
            "ALPACA_API_KEY",
            default="",
            cast=str
        )
        self.alpaca_secret_key: str = config(
            "ALPACA_SECRET_KEY",
            default="",
            cast=str
        )
        self.alpaca_base_url: str = config(
            "ALPACA_BASE_URL",
            default="https://paper-api.alpaca.markets",
            cast=str
        )
        
        # Trading Configuration
        self.paper_trading: bool = config(
            "PAPER_TRADING",
            default=True,
            cast=bool
        )
        self.enable_fractional_shares: bool = config(
            "ENABLE_FRACTIONAL_SHARES",
            default=True,
            cast=bool
        )
        self.min_order_value: float = config(
            "MIN_ORDER_VALUE",
            default=1.0,
            cast=float
        )
        
        # Dynamic parameter adjustment
        self.enable_dynamic_parameters: bool = config(
            "ENABLE_DYNAMIC_PARAMETERS",
            default=True,
            cast=bool
        )
        self.parameter_refresh_frequency: int = config(
            "PARAMETER_REFRESH_FREQUENCY",
            default=10,
            cast=int
        )
        
        # Strategy Parameters - Improved for better risk management
        self.default_position_size: float = config(
            "DEFAULT_POSITION_SIZE",
            default=500.0,  # Reduced from 1000 to limit risk per trade
            cast=float
        )
        self.support_threshold: float = config(
            "SUPPORT_THRESHOLD",
            default=0.015,  # Tightened from 0.02 for better entry precision
            cast=float
        )
        self.resistance_threshold: float = config(
            "RESISTANCE_THRESHOLD",
            default=0.01,  # Tightened from 0.015 for better exit precision
            cast=float
        )
        self.stop_loss_percentage: float = config(
            "STOP_LOSS_PERCENTAGE",
            default=0.025,  # Increased from 0.01 (1%) to 0.025 (2.5%) for better protection
            cast=float
        )
        
        # Additional risk management parameters
        self.take_profit_percentage: float = config(
            "TAKE_PROFIT_PERCENTAGE",
            default=0.05,  # 5% take profit for better risk/reward ratio (2:1)
            cast=float
        )
        self.max_daily_loss_percentage: float = config(
            "MAX_DAILY_LOSS_PERCENTAGE",
            default=0.05,  # 5% maximum daily loss
            cast=float
        )
        self.max_daily_trades: int = config(
            "MAX_DAILY_TRADES",
            default=10,  # Limit daily trades to prevent overtrading
            cast=int
        )
        self.max_position_percentage: float = config(
            "MAX_POSITION_PERCENTAGE",
            default=0.02,  # Maximum 2% of portfolio per position (reduced from 5%)
            cast=float
        )
        
        # Fixed Trade Amount Feature
        self.fixed_trade_amount_enabled: bool = config(
            "FIXED_TRADE_AMOUNT_ENABLED",
            default=False,
            cast=bool
        )
        self.fixed_trade_amount: float = config(
            "FIXED_TRADE_AMOUNT",
            default=100.0,
            cast=float
        )
        self.min_trade_amount: float = config(
            "MIN_TRADE_AMOUNT",
            default=1.0,
            cast=float
        )
        self.max_trade_amount: float = config(
            "MAX_TRADE_AMOUNT",
            default=10000.0,
            cast=float
        )
        
        # Trading Mode
        self.trading_mode: str = config(
            "TRADING_MODE",
            default="conservative",
            cast=str
        )
        
        # Weekend Trading
        self.weekend_trading_enabled: bool = config(
            "WEEKEND_TRADING_ENABLED",
            default=False,
            cast=bool
        )
        
        # Portfolio Management
        self.custom_portfolio_value_enabled: bool = config(
            "CUSTOM_PORTFOLIO_VALUE_ENABLED",
            default=False,
            cast=bool
        )
        self.custom_portfolio_value: float = config(
            "CUSTOM_PORTFOLIO_VALUE",
            default=10000.0,
            cast=float
        )
        self.min_portfolio_value: float = config(
            "MIN_PORTFOLIO_VALUE",
            default=1.0,
            cast=float
        )
        self.max_portfolio_value: float = config(
            "MAX_PORTFOLIO_VALUE",
            default=1000000.0,
            cast=float
        )
        
        # Application Configuration
        self.log_level: str = config(
            "LOG_LEVEL",
            default="INFO",
            cast=str
        )
        self.log_file_path: str = config(
            "LOG_FILE_PATH",
            default="logs/alpaca_bot.log",
            cast=str
        )
        self.data_refresh_interval: int = config(
            "DATA_REFRESH_INTERVAL",
            default=5,
            cast=int
        )
        
        # GUI Configuration
        self.window_width: int = config(
            "WINDOW_WIDTH",
            default=1200,
            cast=int
        )
        self.window_height: int = config(
            "WINDOW_HEIGHT",
            default=800,
            cast=int
        )
        
        # Validate critical settings
        self._validate_settings()
    
    def _validate_settings(self) -> None:
        """Validate critical configuration settings.
        
        Raises:
            ValueError: If required settings are missing or invalid.
        """
        if not self.alpaca_api_key:
            raise ValueError(
                "ALPACA_API_KEY is required. Please set it in your environment "
                "variables or .env file."
            )
        
        if not self.alpaca_secret_key:
            raise ValueError(
                "ALPACA_SECRET_KEY is required. Please set it in your environment "
                "variables or .env file."
            )
        
        if self.support_threshold <= 0 or self.support_threshold >= 1:
            raise ValueError(
                "SUPPORT_THRESHOLD must be between 0 and 1 (exclusive)."
            )
        
        if self.resistance_threshold <= 0 or self.resistance_threshold >= 1:
            raise ValueError(
                "RESISTANCE_THRESHOLD must be between 0 and 1 (exclusive)."
            )
        
        if self.stop_loss_percentage <= 0 or self.stop_loss_percentage >= 1:
            raise ValueError(
                "STOP_LOSS_PERCENTAGE must be between 0 and 1 (exclusive)."
            )
    
    def is_paper_trading(self) -> bool:
        """Check if paper trading is enabled.
        
        Returns:
            bool: True if paper trading is enabled, False otherwise.
        """
        return self.paper_trading
    
    def get_alpaca_credentials(self) -> Tuple[str, str, str]:
        """Get Alpaca API credentials.
        
        Returns:
            Tuple[str, str, str]: API key, secret key, and base URL.
        """
        return self.alpaca_api_key, self.alpaca_secret_key, self.alpaca_base_url
    
    def get_strategy_params(self) -> Dict[str, float]:
        """Get trading strategy parameters.
        
        Returns:
            Dict[str, float]: Dictionary containing strategy parameters.
        """
        return {
            "support_threshold": self.support_threshold,
            "resistance_threshold": self.resistance_threshold,
            "stop_loss_percentage": self.stop_loss_percentage,
            "default_position_size": self.default_position_size,
        }
    
    def update_strategy_params(self, **kwargs) -> None:
        """Update strategy parameters.
        
        Args:
            **kwargs: Strategy parameters to update.
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        # Re-validate after updates
        self._validate_settings()
    
    def save_to_env_file(self, env_file_path: str = None) -> bool:
        """Save current settings to .env file.
        
        Args:
            env_file_path (str, optional): Path to .env file. Defaults to project root/.env
            
        Returns:
            bool: True if saved successfully, False otherwise.
        """
        try:
            if env_file_path is None:
                env_file_path = get_project_root() / ".env"
            else:
                env_file_path = Path(env_file_path)
            
            # Read existing .env file if it exists
            existing_vars = {}
            if env_file_path.exists():
                with open(env_file_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            existing_vars[key.strip()] = value.strip()
            
            # Update with current settings
            settings_to_save = {
                # Alpaca API Settings
                'ALPACA_API_KEY': self.alpaca_api_key,
                'ALPACA_SECRET_KEY': self.alpaca_secret_key,
                'ALPACA_BASE_URL': self.alpaca_base_url,
                'PAPER_TRADING': str(self.paper_trading).lower(),
                
                # Trading Configuration
                'TRADING_MODE': self.trading_mode,
                'WEEKEND_TRADING_ENABLED': str(self.weekend_trading_enabled).lower(),
                'SUPPORT_THRESHOLD': str(self.support_threshold),
                'RESISTANCE_THRESHOLD': str(self.resistance_threshold),
                'STOP_LOSS_PERCENTAGE': str(self.stop_loss_percentage),
                'DEFAULT_POSITION_SIZE': str(self.default_position_size),
                
                # Fixed Trade Amount Feature
                'FIXED_TRADE_AMOUNT_ENABLED': str(self.fixed_trade_amount_enabled).lower(),
                'FIXED_TRADE_AMOUNT': str(self.fixed_trade_amount),
                
                # Custom Portfolio Value Feature
                'CUSTOM_PORTFOLIO_VALUE_ENABLED': str(self.custom_portfolio_value_enabled).lower(),
                'CUSTOM_PORTFOLIO_VALUE': str(self.custom_portfolio_value),
                
                # Application Settings
                'LOG_LEVEL': self.log_level,
                'LOG_FILE_PATH': self.log_file_path,
                'DATA_REFRESH_INTERVAL': str(self.data_refresh_interval),
                
                # GUI Settings
                'WINDOW_WIDTH': str(self.window_width),
                'WINDOW_HEIGHT': str(self.window_height),
            }
            
            # Merge with existing variables (preserve non-settings variables)
            existing_vars.update(settings_to_save)
            
            # Write to .env file
            with open(env_file_path, 'w') as f:
                f.write("# Alpaca Trading Bot Configuration\n")
                f.write("# Generated automatically - modify with caution\n\n")
                
                # Group settings by category
                f.write("# Alpaca API Settings\n")
                for key in ['ALPACA_API_KEY', 'ALPACA_SECRET_KEY', 'ALPACA_BASE_URL', 'PAPER_TRADING']:
                    if key in existing_vars:
                        f.write(f"{key}={existing_vars[key]}\n")
                
                f.write("\n# Trading Configuration\n")
                for key in ['TRADING_MODE', 'WEEKEND_TRADING_ENABLED', 'SUPPORT_THRESHOLD', 'RESISTANCE_THRESHOLD', 'STOP_LOSS_PERCENTAGE', 'DEFAULT_POSITION_SIZE']:
                    if key in existing_vars:
                        f.write(f"{key}={existing_vars[key]}\n")
                
                f.write("\n# Position Sizing Features\n")
                for key in ['FIXED_TRADE_AMOUNT_ENABLED', 'FIXED_TRADE_AMOUNT', 'CUSTOM_PORTFOLIO_VALUE_ENABLED', 'CUSTOM_PORTFOLIO_VALUE']:
                    if key in existing_vars:
                        f.write(f"{key}={existing_vars[key]}\n")
                
                f.write("\n# Application Settings\n")
                for key in ['LOG_LEVEL', 'LOG_FILE_PATH', 'DATA_REFRESH_INTERVAL']:
                    if key in existing_vars:
                        f.write(f"{key}={existing_vars[key]}\n")
                
                f.write("\n# GUI Settings\n")
                for key in ['WINDOW_WIDTH', 'WINDOW_HEIGHT']:
                    if key in existing_vars:
                        f.write(f"{key}={existing_vars[key]}\n")
                
                # Write any other existing variables
                other_vars = {k: v for k, v in existing_vars.items() 
                             if k not in settings_to_save}
                if other_vars:
                    f.write("\n# Other Settings\n")
                    for key, value in other_vars.items():
                        f.write(f"{key}={value}\n")
            
            return True
            
        except Exception as e:
            print(f"Error saving settings to .env file: {e}")
            return False


def get_project_root() -> Path:
    """Get the project root directory.
    
    Returns:
        Path: Path to the project root directory.
    """
    return Path(__file__).parent.parent.parent.parent


def ensure_directories() -> None:
    """Ensure required directories exist."""
    project_root = get_project_root()
    
    # Create logs directory if it doesn't exist
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Create data directory if it doesn't exist
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)


# Global settings instance
settings = Settings()