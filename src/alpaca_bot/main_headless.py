"""Headless entry point for the Alpaca Trading Bot.

This module provides:
- Application initialization without GUI
- Trading loop execution
- Configuration loading
- Error handling and logging setup
"""

import sys
import logging
import threading
import time
import signal
from pathlib import Path

from .config.settings import Settings
from .utils.logging_utils import setup_logging
from .utils.error_handler import (
    ErrorHandler, TradingBotError, APIConnectionError,
    ConfigurationError, safe_execute
)
from .services.alpaca_client import AlpacaClient
from .strategies.scalping_strategy import ScalpingStrategy


class HeadlessTradingBot:
    """Headless trading bot that runs without GUI."""
    
    def __init__(self):
        """Initialize the headless trading bot."""
        self.logger = logging.getLogger(__name__)
        self.is_trading = False
        self.trading_thread = None
        self.alpaca_client = None
        self.strategy = None
        self.shutdown_event = threading.Event()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.shutdown_event.set()
        self.stop_trading()
    
    def setup_application(self) -> None:
        """Set up the application environment."""
        try:
            # Setup logging
            setup_logging()
            self.logger.info("Starting Alpaca Trading Bot (Headless Mode)")
            
            # Load configuration
            settings = Settings()
            
            # Validate required settings
            if not settings.alpaca_api_key or not settings.alpaca_secret_key:
                raise ValueError(
                    "Alpaca API credentials not found. "
                    "Please check your .env file or environment variables."
                )
            
            self.logger.info(f"Configuration loaded - Paper trading: {settings.paper_trading}")
            
            # Initialize Alpaca client
            self.alpaca_client = AlpacaClient()
            
            # Initialize trading strategy
            self.strategy = ScalpingStrategy(self.alpaca_client)
            
            self.logger.info("Application setup completed successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize application: {e}"
            self.logger.error(error_msg, exc_info=True)
            raise
    
    def start_trading(self) -> bool:
        """Start automated trading."""
        if self.is_trading:
            self.logger.warning("Trading is already running")
            return False
        
        try:
            # Validate connection
            if not self.alpaca_client or not self.alpaca_client.is_connected():
                self.logger.error("Alpaca client not connected")
                return False
            
            self.is_trading = True
            
            # Start trading thread
            self.trading_thread = threading.Thread(
                target=self._trading_loop,
                daemon=True
            )
            self.trading_thread.start()
            
            self.logger.info("Trading started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start trading: {e}", exc_info=True)
            self.is_trading = False
            return False
    
    def stop_trading(self) -> None:
        """Stop automated trading."""
        if not self.is_trading:
            return
        
        self.logger.info("Stopping trading...")
        self.is_trading = False
        
        # Wait for trading thread to finish
        if self.trading_thread and self.trading_thread.is_alive():
            self.trading_thread.join(timeout=10)
        
        self.logger.info("Trading stopped")
    
    def _trading_loop(self) -> None:
        """Main trading loop."""
        self.logger.info("Trading loop started")
        
        try:
            while self.is_trading and not self.shutdown_event.is_set():
                # Get selected symbols from settings
                settings = Settings()
                symbols = settings.selected_symbols
                
                if not symbols:
                    self.logger.warning("No symbols selected for trading")
                    time.sleep(30)
                    continue
                
                # Process each symbol
                for symbol in symbols:
                    if not self.is_trading or self.shutdown_event.is_set():
                        break
                    
                    try:
                        # Execute trading strategy for symbol
                        self.strategy.process_symbol(symbol)
                        
                    except Exception as e:
                        self.logger.error(f"Error processing symbol {symbol}: {e}", exc_info=True)
                
                # Sleep between iterations (5 seconds)
                if self.is_trading and not self.shutdown_event.is_set():
                    self.shutdown_event.wait(5)
                    
        except Exception as e:
            self.logger.error(f"Error in trading loop: {e}", exc_info=True)
        
        finally:
            self.logger.info("Trading loop ended")
    
    def run(self) -> None:
        """Run the headless trading bot."""
        try:
            # Setup application
            self.setup_application()
            
            # Start trading
            if self.start_trading():
                self.logger.info("Bot is running. Press Ctrl+C to stop.")
                
                # Keep the main thread alive
                while not self.shutdown_event.is_set():
                    self.shutdown_event.wait(1)
            else:
                self.logger.error("Failed to start trading")
                sys.exit(1)
                
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}", exc_info=True)
            sys.exit(1)
        finally:
            self.stop_trading()
            self.logger.info("Alpaca Trading Bot shutdown complete")


def main() -> None:
    """Main application entry point for headless mode."""
    bot = HeadlessTradingBot()
    bot.run()


if __name__ == "__main__":
    main()