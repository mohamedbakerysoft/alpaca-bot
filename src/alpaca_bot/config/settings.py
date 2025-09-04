"""Configuration management for Alpaca Trading Bot.

This module handles secure configuration management using environment variables
and .env files for API keys and application settings.
"""

import os
from pathlib import Path
from typing import Optional

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
        
        # Strategy Parameters
        self.default_position_size: float = config(
            "DEFAULT_POSITION_SIZE",
            default=1000.0,
            cast=float
        )
        self.support_threshold: float = config(
            "SUPPORT_THRESHOLD",
            default=0.02,
            cast=float
        )
        self.resistance_threshold: float = config(
            "RESISTANCE_THRESHOLD",
            default=0.015,
            cast=float
        )
        self.stop_loss_percentage: float = config(
            "STOP_LOSS_PERCENTAGE",
            default=0.01,
            cast=float
        )
        
        # Trading Mode
        self.aggressive_mode: bool = config(
            "AGGRESSIVE_MODE",
            default=False,
            cast=bool
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
    
    def get_alpaca_credentials(self) -> tuple[str, str, str]:
        """Get Alpaca API credentials.
        
        Returns:
            tuple[str, str, str]: API key, secret key, and base URL.
        """
        return self.alpaca_api_key, self.alpaca_secret_key, self.alpaca_base_url
    
    def get_strategy_params(self) -> dict[str, float]:
        """Get trading strategy parameters.
        
        Returns:
            dict[str, float]: Dictionary containing strategy parameters.
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