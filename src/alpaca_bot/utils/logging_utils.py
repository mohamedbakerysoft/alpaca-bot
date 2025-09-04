"""Logging utilities for the Alpaca trading bot.

This module provides centralized logging configuration and utilities
for consistent logging across the application.
"""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..config.settings import settings


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> None:
    """Set up logging configuration for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Path to log file. If None, uses default from settings.
        max_file_size: Maximum size of log file before rotation.
        backup_count: Number of backup files to keep.
    """
    # Get log level from settings if not provided
    if log_level is None:
        log_level = settings.LOG_LEVEL
    
    # Get log file path
    if log_file is None:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"alpaca_bot_{datetime.now().strftime('%Y%m%d')}.log"
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized - Level: {log_level}, File: {log_file}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__).
        
    Returns:
        logging.Logger: Configured logger instance.
    """
    return logging.getLogger(name)


class TradeLogger:
    """Specialized logger for trade-related events."""
    
    def __init__(self, log_file: Optional[str] = None):
        """Initialize trade logger.
        
        Args:
            log_file: Path to trade log file. If None, uses default.
        """
        self.logger = logging.getLogger('trades')
        
        if log_file is None:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / f"trades_{datetime.now().strftime('%Y%m%d')}.log"
        
        # Create file handler for trades
        handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=10,
            encoding='utf-8'
        )
        
        # Trade-specific formatter
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        # Add handler if not already present
        if not any(isinstance(h, logging.handlers.RotatingFileHandler) 
                  for h in self.logger.handlers):
            self.logger.addHandler(handler)
        
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False  # Don't propagate to root logger
    
    def log_trade_signal(self, symbol: str, signal_type: str, price: float, 
                        reason: str) -> None:
        """Log a trade signal.
        
        Args:
            symbol: Stock symbol.
            signal_type: Type of signal (BUY, SELL).
            price: Signal price.
            reason: Reason for the signal.
        """
        message = f"SIGNAL - {symbol} - {signal_type} at ${price:.2f} - {reason}"
        self.logger.info(message)
    
    def log_order_placed(self, symbol: str, side: str, quantity: float, 
                        order_type: str, price: Optional[float] = None,
                        order_id: Optional[str] = None) -> None:
        """Log an order placement.
        
        Args:
            symbol: Stock symbol.
            side: Order side (buy/sell).
            quantity: Order quantity.
            order_type: Order type (market/limit/etc).
            price: Order price (for limit orders).
            order_id: Order ID from broker.
        """
        price_str = f" at ${price:.2f}" if price else ""
        order_id_str = f" (ID: {order_id})" if order_id else ""
        
        message = (f"ORDER_PLACED - {symbol} - {side.upper()} {quantity} shares "
                  f"{order_type}{price_str}{order_id_str}")
        self.logger.info(message)
    
    def log_order_filled(self, symbol: str, side: str, quantity: float, 
                        fill_price: float, order_id: Optional[str] = None) -> None:
        """Log an order fill.
        
        Args:
            symbol: Stock symbol.
            side: Order side (buy/sell).
            quantity: Filled quantity.
            fill_price: Fill price.
            order_id: Order ID from broker.
        """
        order_id_str = f" (ID: {order_id})" if order_id else ""
        
        message = (f"ORDER_FILLED - {symbol} - {side.upper()} {quantity} shares "
                  f"at ${fill_price:.2f}{order_id_str}")
        self.logger.info(message)
    
    def log_order_cancelled(self, symbol: str, order_id: str, reason: str = "") -> None:
        """Log an order cancellation.
        
        Args:
            symbol: Stock symbol.
            order_id: Order ID from broker.
            reason: Reason for cancellation.
        """
        reason_str = f" - {reason}" if reason else ""
        message = f"ORDER_CANCELLED - {symbol} - ID: {order_id}{reason_str}"
        self.logger.info(message)
    
    def log_position_opened(self, symbol: str, quantity: float, avg_price: float) -> None:
        """Log a position opening.
        
        Args:
            symbol: Stock symbol.
            quantity: Position quantity.
            avg_price: Average entry price.
        """
        message = f"POSITION_OPENED - {symbol} - {quantity} shares at ${avg_price:.2f}"
        self.logger.info(message)
    
    def log_position_closed(self, symbol: str, quantity: float, avg_price: float,
                           exit_price: float, pnl: float) -> None:
        """Log a position closing.
        
        Args:
            symbol: Stock symbol.
            quantity: Position quantity.
            avg_price: Average entry price.
            exit_price: Exit price.
            pnl: Profit/loss.
        """
        pnl_str = f"${pnl:+.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
        message = (f"POSITION_CLOSED - {symbol} - {quantity} shares "
                  f"(Entry: ${avg_price:.2f}, Exit: ${exit_price:.2f}, P&L: {pnl_str})")
        self.logger.info(message)
    
    def log_strategy_event(self, symbol: str, event: str, details: str = "") -> None:
        """Log a strategy-related event.
        
        Args:
            symbol: Stock symbol.
            event: Event description.
            details: Additional details.
        """
        details_str = f" - {details}" if details else ""
        message = f"STRATEGY - {symbol} - {event}{details_str}"
        self.logger.info(message)
    
    def log_error(self, symbol: str, error_type: str, error_message: str) -> None:
        """Log a trading error.
        
        Args:
            symbol: Stock symbol.
            error_type: Type of error.
            error_message: Error message.
        """
        message = f"ERROR - {symbol} - {error_type}: {error_message}"
        self.logger.error(message)


class PerformanceLogger:
    """Logger for performance metrics and statistics."""
    
    def __init__(self, log_file: Optional[str] = None):
        """Initialize performance logger.
        
        Args:
            log_file: Path to performance log file. If None, uses default.
        """
        self.logger = logging.getLogger('performance')
        
        if log_file is None:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / f"performance_{datetime.now().strftime('%Y%m%d')}.log"
        
        # Create file handler for performance
        handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=5,
            encoding='utf-8'
        )
        
        # Performance-specific formatter
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        # Add handler if not already present
        if not any(isinstance(h, logging.handlers.RotatingFileHandler) 
                  for h in self.logger.handlers):
            self.logger.addHandler(handler)
        
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False  # Don't propagate to root logger
    
    def log_daily_summary(self, date: str, total_trades: int, winning_trades: int,
                         total_pnl: float, max_drawdown: float) -> None:
        """Log daily performance summary.
        
        Args:
            date: Trading date.
            total_trades: Total number of trades.
            winning_trades: Number of winning trades.
            total_pnl: Total profit/loss.
            max_drawdown: Maximum drawdown.
        """
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        message = (f"DAILY_SUMMARY - {date} - Trades: {total_trades}, "
                  f"Win Rate: {win_rate:.1f}%, P&L: ${total_pnl:+.2f}, "
                  f"Max Drawdown: ${max_drawdown:.2f}")
        self.logger.info(message)
    
    def log_session_metrics(self, session_duration: float, trades_per_hour: float,
                           avg_trade_duration: float, sharpe_ratio: float) -> None:
        """Log session performance metrics.
        
        Args:
            session_duration: Session duration in hours.
            trades_per_hour: Average trades per hour.
            avg_trade_duration: Average trade duration in minutes.
            sharpe_ratio: Sharpe ratio.
        """
        message = (f"SESSION_METRICS - Duration: {session_duration:.1f}h, "
                  f"Trades/Hour: {trades_per_hour:.1f}, "
                  f"Avg Trade Duration: {avg_trade_duration:.1f}min, "
                  f"Sharpe: {sharpe_ratio:.2f}")
        self.logger.info(message)


# Global logger instances
trade_logger = TradeLogger()
performance_logger = PerformanceLogger()