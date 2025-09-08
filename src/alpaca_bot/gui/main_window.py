"""Main GUI window for the Alpaca trading bot.

This module provides the main interface with:
- Start/Stop button to control automated trading
- Dropdown menu to manually select specific stocks
- Auto-selection option for optimal scalping stocks
- Real-time display of trading status and performance
"""

import logging
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime
from typing import Dict, List, Optional

from ..config.settings import settings
from ..services.alpaca_client import AlpacaClient
from ..strategies.scalping_strategy import ScalpingStrategy
from ..utils.logging_utils import get_logger, setup_logging
from ..utils.error_handler import (
    ErrorHandler, TradingBotError, APIConnectionError, 
    MarketDataError, OrderExecutionError, ConfigurationError,
    RateLimitError, safe_execute
)
from ..utils.market_utils import market_hours
from .stock_selector import StockSelectorFrame
from .trading_panel import TradingPanel
from .performance_display import PerformanceDisplay
from .config_panel import ConfigPanel


class MainWindow:
    """Main application window."""
    
    def __init__(self):
        """Initialize the main window."""
        self.logger = get_logger(__name__)
        self.error_handler = ErrorHandler(self.logger)
        
        # Initialize components
        self.alpaca_client: Optional[AlpacaClient] = None
        self.strategy: Optional[ScalpingStrategy] = None
        self.trading_thread: Optional[threading.Thread] = None
        self.is_trading = False
        self.selected_symbols: List[str] = []
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("Alpaca Trading Bot")
        self.root.geometry(f"{settings.window_width}x{settings.window_height}")
        self.root.minsize(800, 600)
        
        # Configure style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Create GUI components
        self._create_menu()
        self._create_main_frame()
        self._create_status_bar()
        
        # Initialize API client
        self._initialize_api_client()
        
        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        self.logger.info("Main window initialized")
    
    def _create_menu(self) -> None:
        """Create the application menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Settings", command=self._show_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_closing)
        
        # Trading menu
        trading_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Trading", menu=trading_menu)
        trading_menu.add_command(label="Start Trading", command=self._start_trading)
        trading_menu.add_command(label="Stop Trading", command=self._stop_trading)
        trading_menu.add_separator()
        trading_menu.add_command(label="View Positions", command=self._show_positions)
        trading_menu.add_command(label="View Orders", command=self._show_orders)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Trading Log", command=self._show_trading_log)
        view_menu.add_command(label="Performance", command=self._show_performance)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
    
    def _create_main_frame(self) -> None:
        """Create the main application frame."""
        # Create main container with vertical paned window for better layout
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Top section with horizontal paned window
        top_paned = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        top_paned.pack(fill=tk.BOTH, expand=True)
        
        # Left panel for controls
        left_frame = ttk.Frame(top_paned)
        top_paned.add(left_frame, weight=1)
        
        # Right panel for displays
        right_frame = ttk.Frame(top_paned)
        top_paned.add(right_frame, weight=2)
        
        # Create left panel components
        self._create_control_panel(left_frame)
        
        # Create right panel components
        self._create_display_panel(right_frame)
        
        # Bottom section for trading panel (more prominent)
        bottom_frame = ttk.Frame(main_container)
        bottom_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Enhanced trading panel
        self.trading_panel = TradingPanel(bottom_frame)
        self.trading_panel.frame.configure(text="🔥 Trading Panel - Quick Access")
    
    def _create_control_panel(self, parent: ttk.Frame) -> None:
        """Create the control panel.
        
        Args:
            parent: Parent frame.
        """
        # Trading control section
        control_frame = ttk.LabelFrame(parent, text="Trading Control", padding=10)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Start/Stop button
        self.start_stop_btn = ttk.Button(
            control_frame,
            text="Start Trading",
            command=self._toggle_trading,
            style="Accent.TButton"
        )
        self.start_stop_btn.pack(fill=tk.X, pady=(0, 10))
        
        # Trading status
        self.status_var = tk.StringVar(value="Stopped")
        status_label = ttk.Label(control_frame, text="Status:")
        status_label.pack(anchor=tk.W)
        
        self.status_display = ttk.Label(
            control_frame,
            textvariable=self.status_var,
            font=('TkDefaultFont', 10, 'bold')
        )
        self.status_display.pack(anchor=tk.W, pady=(0, 10))
        
        # Account info
        account_frame = ttk.LabelFrame(parent, text="Account Info", padding=10)
        account_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Account info with explanations
        account_info_frame = ttk.Frame(account_frame)
        account_info_frame.pack(fill=tk.X)
        
        self.account_info = ttk.Label(account_info_frame, text="Not connected")
        self.account_info.pack(side=tk.LEFT, anchor=tk.W)
        
        # Help button for account info explanation
        help_button = ttk.Button(
            account_info_frame,
            text="?",
            width=3,
            command=self._show_account_info_help
        )
        help_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Stock selection
        self.stock_selector = StockSelectorFrame(parent, self._on_symbols_changed)
    
    def _create_display_panel(self, parent: ttk.Frame) -> None:
        """Create the display panel.
        
        Args:
            parent: Parent frame.
        """
        # Create notebook for tabbed display
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Performance tab
        perf_frame = ttk.Frame(notebook)
        notebook.add(perf_frame, text="Performance")
        self.performance_display = PerformanceDisplay(perf_frame)
        
        # Log tab
        log_frame = ttk.Frame(notebook)
        notebook.add(log_frame, text="Trading Log")
        self._create_log_display(log_frame)
        
        # Positions tab
        positions_frame = ttk.Frame(notebook)
        notebook.add(positions_frame, text="Positions")
        self._create_positions_display(positions_frame)
        
        # Orders tab
        orders_frame = ttk.Frame(notebook)
        notebook.add(orders_frame, text="Orders")
        self._create_orders_display(orders_frame)
        
        # Configuration panel
        from ..config.settings import settings
        self.config_panel = ConfigPanel(notebook, settings, self._on_config_changed)
    
    def _create_log_display(self, parent: ttk.Frame) -> None:
        """Create the log display.
        
        Args:
            parent: Parent frame.
        """
        # Log text area
        self.log_text = scrolledtext.ScrolledText(
            parent,
            wrap=tk.WORD,
            height=20,
            font=('Consolas', 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Log controls
        log_controls = ttk.Frame(parent)
        log_controls.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(
            log_controls,
            text="Clear Log",
            command=self._clear_log
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            log_controls,
            text="Refresh",
            command=self._refresh_log
        ).pack(side=tk.LEFT)
    
    def _create_positions_display(self, parent: ttk.Frame) -> None:
        """Create the positions display.
        
        Args:
            parent: Parent frame.
        """
        # Positions treeview
        columns = ('Symbol', 'Quantity', 'Entry Price', 'Current Price', 'P&L', 'P&L %')
        self.positions_tree = ttk.Treeview(parent, columns=columns, show='headings')
        
        for col in columns:
            self.positions_tree.heading(col, text=col)
            self.positions_tree.column(col, width=100, anchor=tk.CENTER)
        
        # Scrollbar for positions
        pos_scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.positions_tree.yview)
        self.positions_tree.configure(yscrollcommand=pos_scrollbar.set)
        
        self.positions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        pos_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
    
    def _create_orders_display(self, parent: ttk.Frame) -> None:
        """Create the orders display.
        
        Args:
            parent: Parent frame.
        """
        # Orders treeview with enhanced columns
        columns = ('Order ID', 'Symbol', 'Side', 'Quantity', 'Type', 'Status', 'Price', 'Filled', 'Time')
        self.orders_tree = ttk.Treeview(parent, columns=columns, show='headings')
        
        # Configure column widths and headings
        column_widths = {
            'Order ID': 80,
            'Symbol': 70,
            'Side': 50,
            'Quantity': 70,
            'Type': 70,
            'Status': 80,
            'Price': 80,
            'Filled': 80,
            'Time': 80
        }
        
        for col in columns:
            self.orders_tree.heading(col, text=col)
            self.orders_tree.column(col, width=column_widths.get(col, 100), anchor=tk.CENTER)
        
        # Scrollbar for orders
        orders_scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.orders_tree.yview)
        self.orders_tree.configure(yscrollcommand=orders_scrollbar.set)
        
        self.orders_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        orders_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Configure status-based row colors
        self.orders_tree.tag_configure('filled', background='#d4edda')
        self.orders_tree.tag_configure('pending', background='#fff3cd')
        self.orders_tree.tag_configure('cancelled', background='#f8d7da')
        self.orders_tree.tag_configure('rejected', background='#f8d7da')
    
    def _create_status_bar(self) -> None:
        """Create the status bar."""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Connection status
        self.connection_status = ttk.Label(
            self.status_bar,
            text="Disconnected",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.connection_status.pack(side=tk.LEFT, padx=5, pady=2)
        
        # Market status
        self.market_status = ttk.Label(
            self.status_bar,
            text="Market: Unknown",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.market_status.pack(side=tk.LEFT, padx=5, pady=2)
        
        # Time display
        self.time_display = ttk.Label(
            self.status_bar,
            text="",
            relief=tk.SUNKEN,
            anchor=tk.E
        )
        self.time_display.pack(side=tk.RIGHT, padx=5, pady=2)
        
        # Update time display
        self._update_time_display()
        
        # Start order status updates
        self._start_order_updates()
    
    def _initialize_api_client(self) -> None:
        """Initialize the Alpaca API client."""
        def _init_client():
            self.alpaca_client = AlpacaClient()
            
            # Test connection
            account = self.alpaca_client.get_account()
            if account:
                self.connection_status.config(text="Connected")
                self._update_account_info(account)
                
                # Market status will be updated by _update_market_status method
                # which is called periodically by _update_time_display
                
                # Initialize strategy with account and order update callbacks
                self.strategy = ScalpingStrategy(
                    self.alpaca_client, 
                    account_update_callback=self._trigger_account_update,
                    order_update_callback=self._trigger_order_update
                )
                
                self.logger.info("API client initialized successfully")
                return True
            else:
                self.connection_status.config(text="Connection Failed")
                messagebox.showerror(
                    "Connection Error",
                    "Failed to connect to Alpaca API. Please check your credentials."
                )
                return False
        
        success = safe_execute(
            _init_client,
            default_return=False,
            log_errors=True
        )
        
        if not success:
            self.connection_status.config(text="Connection Error")
    
    def _handle_connection_error(self, error: Exception) -> None:
        """Handle API connection errors with user-friendly messages.
        
        Args:
            error: The exception that occurred.
        """
        if isinstance(error, ConfigurationError):
            messagebox.showerror(
                "Configuration Error",
                "Invalid API credentials. Please check your API key and secret."
            )
        elif isinstance(error, APIConnectionError):
            messagebox.showerror(
                "Connection Error",
                "Failed to connect to Alpaca API. Please check your internet connection."
            )
        elif isinstance(error, RateLimitError):
            messagebox.showwarning(
                "Rate Limit",
                "API rate limit exceeded. Please wait before retrying."
            )
        else:
            messagebox.showerror(
                "Initialization Error",
                f"Failed to initialize API client: {error}"
            )
     
    def _update_account_info(self, account) -> None:
        """Update account information display.
        
        Args:
            account: Account object from Alpaca API.
        """
        try:
            buying_power = float(account.buying_power)
            portfolio_value = float(account.portfolio_value)
            
            info_text = (
                f"Buying Power: ${buying_power:,.2f}\n"
                f"Portfolio Value: ${portfolio_value:,.2f}"
            )
            
            self.account_info.config(text=info_text)
            
        except Exception as e:
            self.logger.error(f"Error updating account info: {e}")
            self.account_info.config(text="Error loading account info")
    
    def _trigger_account_update(self) -> None:
        """Trigger immediate account update from strategy callback."""
        def _update_account():
            if self.alpaca_client:
                account = self.alpaca_client.get_account()
                if account:
                    self._update_account_info(account)
        
        # Schedule update on main thread
        self.root.after(0, _update_account)
    
    def _trigger_order_update(self) -> None:
        """Trigger immediate order display update from strategy callback."""
        def _update_orders():
            self._update_orders_display()
        
        # Schedule update on main thread
        self.root.after(0, _update_orders)
    
    def _toggle_trading(self) -> None:
        """Toggle trading on/off."""
        if self.is_trading:
            self._stop_trading()
        else:
            self._start_trading()
    
    def _start_trading(self) -> None:
        """Start automated trading."""
        def _start_trading_internal() -> None:
            """Internal function to start trading."""
            if not self.alpaca_client or not self.strategy:
                messagebox.showerror(
                    "Error",
                    "API client not initialized. Please check your connection."
                )
                return
            
            if not self.selected_symbols:
                messagebox.showwarning(
                    "Warning",
                    "No symbols selected. Please select stocks to trade."
                )
                return
            
            # Check market hours
            is_open, market_status = market_hours.get_market_status()
            if not is_open:
                time_until_open = market_hours.get_time_until_open()
                message = f"Market is currently closed.\n\n{market_status}"
                if time_until_open:
                    message += f"\nTime until market opens: {time_until_open}"
                
                messagebox.showwarning(
                    "Market Closed",
                    message
                )
                return
            
            # Confirm start trading
            if not messagebox.askyesno(
                "Confirm",
                f"Start trading with {len(self.selected_symbols)} symbols?\n"
                f"Symbols: {', '.join(self.selected_symbols)}\n\n"
                f"Market Status: {market_status}"
            ):
                return
            
            self.is_trading = True
            self.status_var.set("Running")
            self.start_stop_btn.config(text="Stop Trading", style="Danger.TButton")
            
            # Start trading thread
            self.trading_thread = threading.Thread(
                target=self._trading_loop,
                daemon=True
            )
            self.trading_thread.start()
            
            self.logger.info("Trading started")
            self._log_message("Trading started")
        
        def _handle_start_error(error: Exception) -> None:
            """Handle trading start errors."""
            self.logger.error(f"Error starting trading: {error}")
            messagebox.showerror("Error", f"Failed to start trading: {error}")
        
        safe_execute(
            _start_trading_internal,
            default_return=None,
            log_errors=True
        )
    
    def _stop_trading(self) -> None:
        """Stop automated trading."""
        def _stop_trading_internal():
            self.is_trading = False
            self.status_var.set("Stopping...")
            
            # Wait for trading thread to finish
            if self.trading_thread and self.trading_thread.is_alive():
                self.trading_thread.join(timeout=5)
            
            self.status_var.set("Stopped")
            self.start_stop_btn.config(text="Start Trading", style="Accent.TButton")
            
            self.logger.info("Trading stopped")
            self._log_message("Trading stopped")
            return True
        
        safe_execute(
            _stop_trading_internal,
            default_return=None,
            log_errors=True
        )
    
    def _trading_loop(self) -> None:
        """Main trading loop."""
        def _run_trading_loop() -> None:
            """Internal function to run the trading loop."""
            while self.is_trading:
                # Update strategy positions
                if self.strategy:
                    safe_execute(
                        self.strategy.update_positions,
                        default_return=None,
                        log_errors=True
                    )
                
                # Analyze each selected symbol
                for symbol in self.selected_symbols:
                    if not self.is_trading:
                        break
                    
                    def _process_symbol():
                        # Analyze symbol
                        stock_data = self.strategy.analyze_symbol(symbol)
                        if not stock_data:
                            return
                        
                        # Generate signals
                        signals = self.strategy.generate_signals(stock_data)
                        
                        # Execute trades based on signals
                        for signal_type, reason in signals:
                            if not self.is_trading:
                                break
                            
                            trade = self.strategy.execute_trade(symbol, signal_type, reason)
                            if trade:
                                self._log_message(
                                    f"{signal_type} signal executed for {symbol}: {reason}"
                                )
                        
                        # Update displays
                        self.root.after(0, self._update_displays)
                    
                    safe_execute(
                        _process_symbol,
                        default_return=None,
                        log_errors=True
                    )
                
                # Sleep between iterations
                if self.is_trading:
                    threading.Event().wait(5)  # 5-second interval
        
        def _handle_loop_error(error: Exception) -> None:
            """Handle trading loop errors."""
            self.logger.error(f"Error in trading loop: {error}")
            self.root.after(0, lambda: self._handle_critical_trading_error(error))
        
        def _cleanup() -> None:
            """Cleanup after trading loop."""
            self.root.after(0, lambda: self.status_var.set("Stopped"))
        
        try:
            safe_execute(
                _run_trading_loop,
                default_return=None,
                log_errors=True
            )
        finally:
            _cleanup()
    
    def _handle_trading_error(self, symbol: str, error: Exception) -> None:
        """Handle trading errors for specific symbols.
        
        Args:
            symbol: Stock symbol that caused the error.
            error: The exception that occurred.
        """
        if isinstance(error, MarketDataError):
            self._log_message(f"Market data unavailable for {symbol}")
        elif isinstance(error, OrderExecutionError):
            self._log_message(f"Order execution failed for {symbol}: {error}")
            messagebox.showwarning(
                "Order Failed",
                f"Failed to execute order for {symbol}. Check your account status."
            )
        elif isinstance(error, RateLimitError):
            self._log_message("Rate limit exceeded, pausing trading")
            self.is_trading = False
            messagebox.showwarning(
                "Rate Limit",
                "API rate limit exceeded. Trading has been paused."
            )
        else:
            self._log_message(f"Error processing {symbol}: {error}")
    
    def _handle_critical_trading_error(self, error: Exception) -> None:
        """Handle critical trading loop errors.
        
        Args:
            error: The exception that occurred.
        """
        if isinstance(error, APIConnectionError):
            messagebox.showerror(
                "Connection Lost",
                "Lost connection to Alpaca API. Trading has been stopped."
            )
        elif isinstance(error, ConfigurationError):
            messagebox.showerror(
                "Configuration Error",
                "Trading configuration is invalid. Please check your settings."
            )
        else:
            messagebox.showerror(
                "Trading Error",
                f"Critical trading error: {error}"
            )

    def _update_displays(self) -> None:
        """Update all display components."""
        def _update_positions():
            self._update_positions_display()
        
        def _update_orders():
            self._update_orders_display()
        
        def _update_account():
            if hasattr(self, 'alpaca_client') and self.alpaca_client:
                try:
                    account = self.alpaca_client.get_account()
                    if account:
                        self._update_account_info(account)
                except Exception as e:
                    self.logger.error(f"Error updating account info: {e}")
        
        def _update_performance():
            if hasattr(self, 'performance_display'):
                # Get current trades from strategy if available
                trades = []
                if hasattr(self, 'strategy') and self.strategy:
                    trades = getattr(self.strategy, 'completed_trades', [])
                self.performance_display.update_trades(trades)
        
        # Update each display component safely
        safe_execute(
            _update_positions,
            default_return=None,
            log_errors=True
        )
        
        safe_execute(
            _update_orders,
            default_return=None,
            log_errors=True
        )
        
        safe_execute(
            _update_account,
            default_return=None,
            log_errors=True
        )
        
        safe_execute(
            _update_performance,
            default_return=None,
            log_errors=True
        )
    
    def _update_positions_display(self) -> None:
        """Update the positions display with actual Alpaca positions."""
        try:
            # Clear existing items
            for item in self.positions_tree.get_children():
                self.positions_tree.delete(item)
            
            # Get actual positions from Alpaca
            try:
                alpaca_positions = self.alpaca_client.get_positions()
                
                for position in alpaca_positions:
                    try:
                        symbol = position.symbol
                        quantity = float(position.qty) if position.qty is not None else 0.0
                        avg_price = float(position.avg_entry_price) if position.avg_entry_price is not None else 0.0
                        
                        # Calculate current price safely
                        if position.market_value is not None and quantity != 0:
                            current_price = float(position.market_value) / quantity
                        else:
                            current_price = avg_price
                            
                        unrealized_pnl = float(position.unrealized_pl) if position.unrealized_pl is not None else 0.0
                        unrealized_pnl_pct = float(position.unrealized_plpc) * 100 if position.unrealized_plpc is not None else 0.0
                        
                        # Insert into treeview
                        self.positions_tree.insert('', 'end', values=(
                            symbol,
                            f"{float(quantity):.6f}".rstrip('0').rstrip('.'),
                            f"${avg_price:.2f}",
                            f"${current_price:.2f}",
                            f"${unrealized_pnl:+.2f}",
                            f"{unrealized_pnl_pct:+.2f}%"
                        ))
                        
                    except Exception as e:
                        self.logger.error(f"Error processing position for {position.symbol}: {e}")
                        
            except Exception as e:
                self.logger.error(f"Error fetching Alpaca positions: {e}")
                # Fallback to strategy positions if Alpaca positions fail
                if self.strategy:
                    for symbol, trade in self.strategy.active_positions.items():
                        try:
                            # Get current quote
                            quote = self.alpaca_client.get_latest_quote(symbol)
                            current_price = quote.bid if quote and hasattr(quote, 'bid') and quote.bid is not None else (trade.entry_price if trade.entry_price is not None else 0.0)
                            
                            # Ensure current_price is never None
                            if current_price is None:
                                current_price = trade.entry_price if trade.entry_price is not None else 0.0
                            
                            # Calculate P&L with proper None checks
                            if (current_price is not None and trade.entry_price is not None and 
                                trade.quantity is not None and trade.entry_price != 0):
                                pnl = (current_price - trade.entry_price) * trade.quantity
                                pnl_pct = (current_price - trade.entry_price) / trade.entry_price * 100
                            else:
                                pnl = 0.0
                                pnl_pct = 0.0
                                current_price = trade.entry_price if trade.entry_price is not None else 0.0
                            
                            # Insert into treeview with safe formatting
                            entry_price_str = f"${trade.entry_price:.2f}" if trade.entry_price is not None else "$0.00"
                            current_price_str = f"${current_price:.2f}" if current_price is not None else "$0.00"
                            quantity_str = f"{trade.quantity:.6f}".rstrip('0').rstrip('.') if trade.quantity is not None else "0"
                            
                            self.positions_tree.insert('', 'end', values=(
                                symbol,
                                quantity_str,
                                entry_price_str,
                                current_price_str,
                                f"${pnl:+.2f}",
                                f"{pnl_pct:+.2f}%"
                            ))
                            
                        except Exception as e:
                            self.logger.error(f"Error updating fallback position for {symbol}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error updating positions display: {e}")
    
    def _update_orders_display(self) -> None:
        """Update the orders display with enhanced information."""
        try:
            # Clear existing items
            for item in self.orders_tree.get_children():
                self.orders_tree.delete(item)
            
            if not self.alpaca_client:
                return
            
            # Get recent orders
            orders = self.alpaca_client.get_orders(status='all', limit=50)
            if not orders:
                return
            
            for order in orders:
                try:
                    # Format time
                    order_time = order.created_at.strftime('%H:%M:%S')
                    
                    # Format price
                    price_str = f"${float(order.limit_price):.2f}" if order.limit_price else "Market"
                    
                    # Format filled quantity and percentage
                    filled_qty = float(order.filled_qty) if order.filled_qty else 0
                    total_qty = float(order.qty) if order.qty else 0
                    filled_pct = (filled_qty / total_qty * 100) if total_qty > 0 else 0
                    filled_str = f"{filled_qty:.0f} ({filled_pct:.0f}%)" if total_qty > 0 else "N/A"
                    
                    # Determine status tag for color coding
                    status = order.status.lower()
                    if status in ['filled', 'partially_filled']:
                        tag = 'filled'
                    elif status in ['new', 'accepted', 'pending_new']:
                        tag = 'pending'
                    elif status in ['canceled', 'cancelled']:
                        tag = 'cancelled'
                    elif status in ['rejected', 'expired']:
                        tag = 'rejected'
                    else:
                        tag = ''
                    
                    # Handle quantity display for both regular and notional orders
                    if total_qty > 0:
                        qty_str = f"{total_qty:.0f}"
                    elif hasattr(order, 'notional') and order.notional:
                        qty_str = f"${float(order.notional):.2f}"
                    else:
                        qty_str = "Notional"
                    item = self.orders_tree.insert('', 'end', values=(
                        order.id[:8] + '...',  # Truncated order ID
                        order.symbol,
                        order.side.upper(),
                        qty_str,
                        order.order_type.upper(),
                        order.status.upper().replace('_', ' '),
                        price_str,
                        filled_str,
                        order_time
                    ), tags=(tag,) if tag else ())
                    
                except Exception as e:
                    self.logger.error(f"Error processing order {order.id}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error updating orders display: {e}")
    
    def _update_time_display(self) -> None:
        """Update the time display and market status."""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.time_display.config(text=current_time)
        
        # Update market status
        self._update_market_status()
        
        # Schedule next update
        self.root.after(1000, self._update_time_display)
    
    def _update_market_status(self) -> None:
        """Update the market status display."""
        try:
            is_open, status_message = market_hours.get_market_status()
            status_text = f"Market: {status_message}"
            
            if not is_open:
                time_until_open = market_hours.get_time_until_open()
                if time_until_open:
                    status_text += f" (Opens in {time_until_open})"
            
            self.market_status.config(text=status_text)
            
        except Exception as e:
            self.logger.error(f"Error updating market status: {e}")
            self.market_status.config(text="Market: Unknown")
    
    def _start_order_updates(self) -> None:
        """Start periodic order status updates."""
        self._update_orders_display()
        # Schedule next update every 5 seconds
        self.root.after(5000, self._start_order_updates)
    
    def _on_symbols_changed(self, symbols: List[str]) -> None:
        """Handle symbol selection changes.
        
        Args:
            symbols: List of selected symbols.
        """
        self.selected_symbols = symbols
        self.logger.info(f"Selected symbols updated: {symbols}")
    
    def _on_config_changed(self, config: Dict) -> None:
        """Handle configuration changes.
        
        Args:
            config: Updated configuration.
        """
        def _update_config():
            # Update strategy parameters if strategy exists
            if self.strategy:
                for key, value in config.items():
                    if key == 'trading_mode':
                        # Handle trading mode specially - convert string to enum
                        from src.alpaca_bot.strategies.scalping_strategy import TradingMode
                        try:
                            trading_mode_enum = TradingMode(value)
                            self.strategy.set_trading_mode(trading_mode_enum)
                        except ValueError:
                            self.logger.warning(f"Invalid trading mode '{value}', defaulting to conservative")
                            self.strategy.set_trading_mode(TradingMode.CONSERVATIVE)
                    elif hasattr(self.strategy, key):
                        setattr(self.strategy, key, value)
                        
            self.logger.info("Configuration updated")
            return True
        
        safe_execute(
            _update_config,
            default_return=None,
            log_errors=True
        )
    
    def _log_message(self, message: str) -> None:
        """Add a message to the log display.
        
        Args:
            message: Message to log.
        """
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
    
    def _clear_log(self) -> None:
        """Clear the log display."""
        self.log_text.delete(1.0, tk.END)
    
    def _refresh_log(self) -> None:
        """Refresh the log display."""
        # This could be enhanced to read from log files
        pass
    
    def _show_settings(self) -> None:
        """Show settings dialog."""
        messagebox.showinfo("Settings", "Settings dialog not implemented yet.")
    
    def _show_positions(self) -> None:
        """Show positions dialog."""
        messagebox.showinfo("Positions", "Positions dialog not implemented yet.")
    
    def _show_orders(self) -> None:
        """Show orders dialog."""
        messagebox.showinfo("Orders", "Orders dialog not implemented yet.")
    
    def _show_trading_log(self) -> None:
        """Show trading log dialog."""
        messagebox.showinfo("Trading Log", "Trading log dialog not implemented yet.")
    
    def _show_performance(self) -> None:
        """Show performance dialog."""
        messagebox.showinfo("Performance", "Performance dialog not implemented yet.")
    
    def _show_account_info_help(self) -> None:
        """Show account info help dialog."""
        help_text = (
            "Account Information Explanation:\n\n"
            "• Buying Power: The amount of money available to purchase securities. "
            "This includes cash plus the maximum amount you can borrow on margin.\n\n"
            "• Portfolio Value: The total current market value of all your holdings, "
            "including stocks, cash, and other assets in your account.\n\n"
            "Note: Buying Power can be higher than Portfolio Value if you have "
            "margin trading enabled, as it includes potential borrowed funds."
        )
        messagebox.showinfo("Account Info Help", help_text)
    
    def _show_about(self) -> None:
        """Show about dialog."""
        messagebox.showinfo(
            "About",
            "Alpaca Trading Bot\n\n"
            "Automated scalping strategy for stock trading\n"
            "using the Alpaca API.\n\n"
            "Version 1.0"
        )
    
    def _on_closing(self) -> None:
        """Handle window closing event."""
        def _shutdown_application():
            if self.is_trading:
                if messagebox.askyesno(
                    "Confirm Exit",
                    "Trading is currently active. Stop trading and exit?"
                ):
                    self._stop_trading()
                else:
                    return False
            
            self.logger.info("Application closing")
            self.root.destroy()
            return True
        
        safe_execute(
            _shutdown_application,
            default_return=None,
            log_errors=True
        )
    
    def run(self) -> None:
        """Run the application."""
        def _run_mainloop():
            self.logger.info("Starting application")
            self.root.mainloop()
            return True
        
        safe_execute(
            _run_mainloop,
            default_return=None,
            log_errors=True
        )


def main() -> None:
    """Main entry point."""
    # Setup logging
    setup_logging()
    
    # Create and run application
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()