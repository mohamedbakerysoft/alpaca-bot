"""Comprehensive error handling utilities for the Alpaca Trading Bot.

This module provides centralized error handling for API failures, network issues,
market connectivity problems, and other common errors that can occur during trading.
"""

import logging
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type, Union

import requests
from alpaca_trade_api.rest import APIError
from requests.exceptions import (
    ConnectionError,
    HTTPError,
    RequestException,
    Timeout
)


class TradingBotError(Exception):
    """Base exception for trading bot errors."""
    pass


class APIConnectionError(TradingBotError):
    """Raised when API connection fails."""
    pass


class MarketDataError(TradingBotError):
    """Raised when market data retrieval fails."""
    pass


class OrderExecutionError(TradingBotError):
    """Raised when order execution fails."""
    pass


class ConfigurationError(TradingBotError):
    """Raised when configuration is invalid."""
    pass


class RateLimitError(TradingBotError):
    """Raised when API rate limit is exceeded."""
    pass


class ErrorHandler:
    """Centralized error handling and recovery manager."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the error handler.
        
        Args:
            logger: Logger instance to use for error reporting.
        """
        self.logger = logger or logging.getLogger(__name__)
        self.error_counts: Dict[str, int] = {}
        self.last_error_times: Dict[str, datetime] = {}
        self.circuit_breakers: Dict[str, bool] = {}
        
        # Configuration
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
        self.circuit_breaker_threshold = 5
        self.circuit_breaker_timeout = 300  # 5 minutes
        self.rate_limit_delay = 60  # 1 minute
    
    def handle_api_error(self, error: Exception, operation: str) -> None:
        """Handle API-related errors with appropriate logging and recovery.
        
        Args:
            error: The exception that occurred.
            operation: Description of the operation that failed.
        """
        error_key = f"api_{operation}"
        
        if isinstance(error, APIError):
            if error.status_code == 429:  # Rate limit
                self._handle_rate_limit(error_key)
                raise RateLimitError(f"Rate limit exceeded for {operation}: {error}")
            elif error.status_code >= 500:  # Server error
                self._increment_error_count(error_key)
                raise APIConnectionError(f"Server error during {operation}: {error}")
            elif error.status_code == 401:  # Unauthorized
                raise ConfigurationError(f"Invalid API credentials for {operation}: {error}")
            elif error.status_code == 403:  # Forbidden
                raise ConfigurationError(f"Insufficient permissions for {operation}: {error}")
            else:
                self._increment_error_count(error_key)
                raise TradingBotError(f"API error during {operation}: {error}")
        
        elif isinstance(error, (ConnectionError, Timeout)):
            self._increment_error_count(error_key)
            raise APIConnectionError(f"Network error during {operation}: {error}")
        
        elif isinstance(error, HTTPError):
            self._increment_error_count(error_key)
            raise APIConnectionError(f"HTTP error during {operation}: {error}")
        
        else:
            self._increment_error_count(error_key)
            raise TradingBotError(f"Unexpected error during {operation}: {error}")
    
    def handle_market_data_error(self, error: Exception, symbol: str) -> None:
        """Handle market data retrieval errors.
        
        Args:
            error: The exception that occurred.
            symbol: Stock symbol for which data retrieval failed.
        """
        error_key = f"market_data_{symbol}"
        self._increment_error_count(error_key)
        
        self.logger.error(f"Market data error for {symbol}: {error}")
        raise MarketDataError(f"Failed to retrieve market data for {symbol}: {error}")
    
    def handle_order_error(self, error: Exception, order_details: Dict[str, Any]) -> None:
        """Handle order execution errors.
        
        Args:
            error: The exception that occurred.
            order_details: Details of the order that failed.
        """
        symbol = order_details.get('symbol', 'unknown')
        side = order_details.get('side', 'unknown')
        qty = order_details.get('qty', 'unknown')
        
        error_key = f"order_{symbol}"
        self._increment_error_count(error_key)
        
        self.logger.error(
            f"Order execution error: {side} {qty} {symbol} - {error}"
        )
        raise OrderExecutionError(
            f"Failed to execute {side} order for {qty} {symbol}: {error}"
        )
    
    def is_circuit_breaker_open(self, operation: str) -> bool:
        """Check if circuit breaker is open for an operation.
        
        Args:
            operation: Operation to check.
            
        Returns:
            bool: True if circuit breaker is open, False otherwise.
        """
        if operation not in self.circuit_breakers:
            return False
        
        if not self.circuit_breakers[operation]:
            return False
        
        # Check if timeout has passed
        last_error_time = self.last_error_times.get(operation)
        if last_error_time:
            time_since_error = datetime.now() - last_error_time
            if time_since_error.total_seconds() > self.circuit_breaker_timeout:
                self.circuit_breakers[operation] = False
                self.error_counts[operation] = 0
                self.logger.info(f"Circuit breaker reset for {operation}")
                return False
        
        return True
    
    def _increment_error_count(self, error_key: str) -> None:
        """Increment error count and check circuit breaker threshold.
        
        Args:
            error_key: Key identifying the type of error.
        """
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        self.last_error_times[error_key] = datetime.now()
        
        if self.error_counts[error_key] >= self.circuit_breaker_threshold:
            self.circuit_breakers[error_key] = True
            self.logger.warning(
                f"Circuit breaker opened for {error_key} after "
                f"{self.error_counts[error_key]} errors"
            )
    
    def _handle_rate_limit(self, error_key: str) -> None:
        """Handle rate limit errors with appropriate delays.
        
        Args:
            error_key: Key identifying the rate-limited operation.
        """
        self.logger.warning(f"Rate limit hit for {error_key}, waiting {self.rate_limit_delay}s")
        time.sleep(self.rate_limit_delay)
    
    def reset_error_counts(self, operation: Optional[str] = None) -> None:
        """Reset error counts for an operation or all operations.
        
        Args:
            operation: Specific operation to reset, or None for all.
        """
        if operation:
            self.error_counts.pop(operation, None)
            self.last_error_times.pop(operation, None)
            self.circuit_breakers.pop(operation, None)
            self.logger.info(f"Error counts reset for {operation}")
        else:
            self.error_counts.clear()
            self.last_error_times.clear()
            self.circuit_breakers.clear()
            self.logger.info("All error counts reset")
    
    def get_error_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get summary of current error states.
        
        Returns:
            Dict containing error counts, circuit breaker states, and last error times.
        """
        summary = {}
        
        for operation in set(list(self.error_counts.keys()) + 
                           list(self.circuit_breakers.keys())):
            summary[operation] = {
                'error_count': self.error_counts.get(operation, 0),
                'circuit_breaker_open': self.circuit_breakers.get(operation, False),
                'last_error_time': self.last_error_times.get(operation)
            }
        
        return summary


def retry_on_error(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (APIError, ConnectionError, Timeout)
) -> Callable:
    """Decorator for retrying functions on specific errors.
    
    Args:
        max_retries: Maximum number of retry attempts.
        delay: Initial delay between retries in seconds.
        backoff_factor: Factor to multiply delay by after each retry.
        exceptions: Tuple of exception types to retry on.
        
    Returns:
        Decorated function with retry logic.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = logging.getLogger(func.__module__)
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries} retries: {e}"
                        )
                        raise
                    
                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                        f"Retrying in {current_delay}s..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
                except Exception as e:
                    # Don't retry on unexpected exceptions
                    logger.error(f"Function {func.__name__} failed with unexpected error: {e}")
                    raise
            
            return None  # Should never reach here
        
        return wrapper
    return decorator


def circuit_breaker(
    failure_threshold: int = 5,
    timeout: int = 300,
    expected_exception: Type[Exception] = Exception
) -> Callable:
    """Decorator implementing circuit breaker pattern.
    
    Args:
        failure_threshold: Number of failures before opening circuit.
        timeout: Time in seconds before attempting to close circuit.
        expected_exception: Exception type that triggers circuit breaker.
        
    Returns:
        Decorated function with circuit breaker logic.
    """
    def decorator(func: Callable) -> Callable:
        failure_count = 0
        last_failure_time = None
        circuit_open = False
        
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            nonlocal failure_count, last_failure_time, circuit_open
            
            logger = logging.getLogger(func.__module__)
            
            # Check if circuit should be closed
            if circuit_open and last_failure_time:
                if time.time() - last_failure_time > timeout:
                    circuit_open = False
                    failure_count = 0
                    logger.info(f"Circuit breaker closed for {func.__name__}")
            
            # If circuit is open, fail fast
            if circuit_open:
                raise TradingBotError(
                    f"Circuit breaker is open for {func.__name__}. "
                    f"Try again after {timeout} seconds."
                )
            
            try:
                result = func(*args, **kwargs)
                # Reset failure count on success
                failure_count = 0
                return result
            
            except expected_exception as e:
                failure_count += 1
                last_failure_time = time.time()
                
                if failure_count >= failure_threshold:
                    circuit_open = True
                    logger.error(
                        f"Circuit breaker opened for {func.__name__} after "
                        f"{failure_count} failures"
                    )
                
                raise
        
        return wrapper
    return decorator


def safe_execute(
    func: Callable,
    *args,
    default_return: Any = None,
    log_errors: bool = True,
    **kwargs
) -> Any:
    """Safely execute a function with error handling.
    
    Args:
        func: Function to execute.
        *args: Positional arguments for the function.
        default_return: Value to return if function fails.
        log_errors: Whether to log errors.
        **kwargs: Keyword arguments for the function.
        
    Returns:
        Function result or default_return if function fails.
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            logger = logging.getLogger(func.__module__)
            logger.error(f"Error executing {func.__name__}: {e}")
        return default_return


# Global error handler instance
error_handler = ErrorHandler()