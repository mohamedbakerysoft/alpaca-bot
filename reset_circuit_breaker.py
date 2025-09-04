#!/usr/bin/env python3
"""
Script to reset circuit breakers for the Alpaca Trading Bot.

This script can be used to manually reset circuit breakers when they are stuck
open due to previous errors, allowing the application to resume normal operation.
"""

import sys
import os
import logging
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from alpaca_bot.utils.error_handler import ErrorHandler

def main():
    """Reset circuit breakers for the trading bot."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize error handler
        error_handler = ErrorHandler(logger)
        
        # Get current error summary
        logger.info("Current error summary:")
        summary = error_handler.get_error_summary()
        for operation, details in summary.items():
            logger.info(f"  {operation}: {details}")
        
        # Reset specific operations that are commonly problematic
        operations_to_reset = [
            "get_quote_AAPL",
            "get_quote_MSFT", 
            "get_quote_GOOGL",
            "get_quote_TSLA",
            "get_latest_quote",
            "market_data",
            "get_bars",
            "get_account",
            "get_positions",
            "get_orders",
            "is_market_open",
            "get_tradable_assets"
        ]
        
        logger.info("Resetting circuit breakers for quote operations...")
        for operation in operations_to_reset:
            error_handler.reset_error_counts(operation)
            logger.info(f"Reset circuit breaker for: {operation}")
        
        # Also reset all error counts if requested
        if len(sys.argv) > 1 and sys.argv[1] == "--all":
            logger.info("Resetting all circuit breakers...")
            error_handler.reset_error_counts()
            logger.info("All circuit breakers have been reset")
        
        logger.info("Circuit breaker reset completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to reset circuit breakers: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()