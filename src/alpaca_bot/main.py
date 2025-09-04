"""Main entry point for the Alpaca Trading Bot.

This module provides:
- Application initialization
- GUI startup
- Configuration loading
- Error handling and logging setup
"""

import sys
import logging
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

from .config.settings import Settings
from .utils.logging_utils import setup_logging
from .utils.error_handler import (
    ErrorHandler, TradingBotError, APIConnectionError,
    ConfigurationError, safe_execute
)
from .gui.main_window import MainWindow


def setup_application() -> None:
    """Set up the application environment."""
    try:
        # Setup logging
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("Starting Alpaca Trading Bot")
        
        # Load configuration
        settings = Settings()
        
        # Validate required settings
        if not settings.alpaca_api_key or not settings.alpaca_secret_key:
            raise ValueError(
                "Alpaca API credentials not found. "
                "Please check your .env file or environment variables."
            )
        
        logger.info(f"Configuration loaded - Paper trading: {settings.paper_trading}")
        
    except Exception as e:
        error_msg = f"Failed to initialize application: {e}"
        logging.error(error_msg)
        
        # Show error dialog if possible
        try:
            root = tk.Tk()
            root.withdraw()  # Hide the root window
            messagebox.showerror("Initialization Error", error_msg)
            root.destroy()
        except:
            pass
        
        sys.exit(1)


def main() -> None:
    """Main application entry point."""
    logger = logging.getLogger(__name__)
    error_handler = ErrorHandler(logger)
    
    def _run_application():
        """Run the main application."""
        # Setup application
        setup_application()
        
        # Create and run GUI
        app = MainWindow()
        
        # Configure window close behavior
        def on_closing():
            """Handle application closing."""
            try:
                # Stop trading if running
                if hasattr(app, 'is_trading') and app.is_trading:
                    app.stop_trading()
                
                # Close the application
                app.root.quit()
                app.root.destroy()
                
            except Exception as e:
                logging.error(f"Error during application shutdown: {e}")
                root.destroy()
        
        app.root.protocol("WM_DELETE_WINDOW", on_closing)
        
        # Start the GUI event loop
        logging.info("Starting GUI")
        app.root.mainloop()
        return True
    
    def _handle_startup_error(error: Exception):
        """Handle application startup errors."""
        if isinstance(error, ConfigurationError):
            error_msg = "Configuration error. Please check your settings and API credentials."
        elif isinstance(error, APIConnectionError):
            error_msg = "Failed to connect to Alpaca API. Please check your internet connection."
        else:
            error_msg = f"Unexpected error: {error}"
        
        logger.error(error_msg, exc_info=True)
        
        # Show error dialog if possible
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Application Error", error_msg)
            root.destroy()
        except:
            pass
        
        sys.exit(1)
    
    try:
        # Handle keyboard interrupt gracefully
        success = safe_execute(
            _run_application,
            default_return=False,
            log_errors=True
        )
        
        if not success:
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    
    finally:
        logger.info("Alpaca Trading Bot shutdown complete")


if __name__ == "__main__":
    main()