"""Real-time data display component for the Alpaca trading bot.

This module provides:
- Real-time price charts
- Performance metrics display
- Technical indicators visualization
- Trade execution markers
"""

import logging
import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import threading
import time

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from ..utils.logging_utils import get_logger
from ..models.stock import StockData, StockBar, StockQuote
from ..models.trade import Trade, Position


class DataDisplay:
    """Real-time data display component."""
    
    def __init__(self, parent: tk.Widget):
        """Initialize the data display.
        
        Args:
            parent: Parent widget.
        """
        self.logger = get_logger(__name__)
        
        # Create main frame
        self.frame = ttk.LabelFrame(parent, text="Market Data", padding=10)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Data storage
        self.current_data: Dict[str, StockData] = {}
        self.price_history: Dict[str, List[StockBar]] = {}
        self.trades: List[Trade] = []
        self.positions: List[Position] = []
        
        # Display settings
        self.selected_symbol = tk.StringVar(value="AAPL")
        self.chart_timeframe = tk.StringVar(value="1Min")
        self.show_indicators = tk.BooleanVar(value=True)
        self.show_trades = tk.BooleanVar(value=True)
        
        # Update control
        self.auto_update = tk.BooleanVar(value=True)
        self.update_interval = 5  # seconds
        self._update_thread = None
        self._stop_update = threading.Event()
        
        self._create_widgets()
        
        if MATPLOTLIB_AVAILABLE:
            self._setup_chart()
        else:
            self._show_no_matplotlib_message()
    
    def _create_widgets(self) -> None:
        """Create the display widgets."""
        # Control panel
        control_frame = ttk.Frame(self.frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Symbol selection
        ttk.Label(control_frame, text="Symbol:").pack(side=tk.LEFT, padx=(0, 5))
        
        symbol_combo = ttk.Combobox(
            control_frame,
            textvariable=self.selected_symbol,
            values=["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN", "NVDA", "META"],
            width=8,
            state="readonly"
        )
        symbol_combo.pack(side=tk.LEFT, padx=(0, 10))
        symbol_combo.bind('<<ComboboxSelected>>', self._on_symbol_change)
        
        # Timeframe selection
        ttk.Label(control_frame, text="Timeframe:").pack(side=tk.LEFT, padx=(0, 5))
        
        timeframe_combo = ttk.Combobox(
            control_frame,
            textvariable=self.chart_timeframe,
            values=["1Min", "5Min", "15Min", "1Hour", "1Day"],
            width=8,
            state="readonly"
        )
        timeframe_combo.pack(side=tk.LEFT, padx=(0, 10))
        timeframe_combo.bind('<<ComboboxSelected>>', self._on_timeframe_change)
        
        # Display options
        ttk.Checkbutton(
            control_frame,
            text="Indicators",
            variable=self.show_indicators,
            command=self._on_display_option_change
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Checkbutton(
            control_frame,
            text="Trades",
            variable=self.show_trades,
            command=self._on_display_option_change
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        # Auto-update control
        ttk.Checkbutton(
            control_frame,
            text="Auto Update",
            variable=self.auto_update,
            command=self._on_auto_update_change
        ).pack(side=tk.LEFT, padx=(10, 5))
        
        # Manual refresh button
        ttk.Button(
            control_frame,
            text="Refresh",
            command=self._refresh_data
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        # Create notebook for different views
        self.notebook = ttk.Notebook(self.frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Chart tab
        self.chart_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.chart_frame, text="Price Chart")
        
        # Quote tab
        self.quote_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.quote_frame, text="Live Quote")
        self._create_quote_display()
        
        # Performance tab
        self.performance_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.performance_frame, text="Performance")
        self._create_performance_display()
    
    def _setup_chart(self) -> None:
        """Set up the matplotlib chart."""
        if not MATPLOTLIB_AVAILABLE:
            return
        
        # Create figure and axis
        self.fig = Figure(figsize=(12, 8), dpi=100)
        self.ax = self.fig.add_subplot(111)
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, self.chart_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Configure chart appearance
        self.ax.set_title(f"{self.selected_symbol.get()} - {self.chart_timeframe.get()}")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Price ($)")
        self.ax.grid(True, alpha=0.3)
        
        # Format x-axis for time
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        self.ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=30))
        
        plt.setp(self.ax.xaxis.get_majorticklabels(), rotation=45)
        
        self.fig.tight_layout()
    
    def _show_no_matplotlib_message(self) -> None:
        """Show message when matplotlib is not available."""
        message_frame = ttk.Frame(self.chart_frame)
        message_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(
            message_frame,
            text="📊 Chart Display Unavailable",
            font=('TkDefaultFont', 16, 'bold')
        ).pack(pady=(50, 10))
        
        ttk.Label(
            message_frame,
            text="Install matplotlib to enable chart display:",
            font=('TkDefaultFont', 12)
        ).pack(pady=5)
        
        ttk.Label(
            message_frame,
            text="pip install matplotlib",
            font=('TkDefaultFont', 10, 'bold'),
            foreground='blue'
        ).pack(pady=5)
        
        ttk.Label(
            message_frame,
            text="Real-time quotes and performance data are still available in other tabs.",
            font=('TkDefaultFont', 10)
        ).pack(pady=10)
    
    def _create_quote_display(self) -> None:
        """Create the live quote display."""
        # Current quote frame
        quote_info_frame = ttk.LabelFrame(self.quote_frame, text="Current Quote", padding=10)
        quote_info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create quote grid
        quote_grid = ttk.Frame(quote_info_frame)
        quote_grid.pack(fill=tk.X)
        
        # Price information
        ttk.Label(quote_grid, text="Last Price:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.last_price_label = ttk.Label(quote_grid, text="--", font=('TkDefaultFont', 12, 'bold'))
        self.last_price_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(quote_grid, text="Change:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.price_change_label = ttk.Label(quote_grid, text="--")
        self.price_change_label.grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Bid/Ask
        ttk.Label(quote_grid, text="Bid:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.bid_label = ttk.Label(quote_grid, text="--")
        self.bid_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(quote_grid, text="Ask:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        self.ask_label = ttk.Label(quote_grid, text="--")
        self.ask_label.grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Volume
        ttk.Label(quote_grid, text="Volume:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.volume_label = ttk.Label(quote_grid, text="--")
        self.volume_label.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Last update
        ttk.Label(quote_grid, text="Updated:").grid(row=2, column=2, sticky=tk.W, padx=5, pady=2)
        self.quote_update_label = ttk.Label(quote_grid, text="--")
        self.quote_update_label.grid(row=2, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Configure grid weights
        for i in range(4):
            quote_grid.columnconfigure(i, weight=1)
        
        # Technical indicators frame
        indicators_frame = ttk.LabelFrame(self.quote_frame, text="Technical Indicators", padding=10)
        indicators_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create indicators grid
        indicators_grid = ttk.Frame(indicators_frame)
        indicators_grid.pack(fill=tk.X)
        
        # RSI
        ttk.Label(indicators_grid, text="RSI (14):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.rsi_label = ttk.Label(indicators_grid, text="--")
        self.rsi_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        # MACD
        ttk.Label(indicators_grid, text="MACD:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.macd_label = ttk.Label(indicators_grid, text="--")
        self.macd_label.grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Moving averages
        ttk.Label(indicators_grid, text="SMA (20):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.sma20_label = ttk.Label(indicators_grid, text="--")
        self.sma20_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(indicators_grid, text="EMA (20):").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        self.ema20_label = ttk.Label(indicators_grid, text="--")
        self.ema20_label.grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Configure grid weights
        for i in range(4):
            indicators_grid.columnconfigure(i, weight=1)
    
    def _create_performance_display(self) -> None:
        """Create the performance metrics display."""
        # Position summary
        position_frame = ttk.LabelFrame(self.performance_frame, text="Current Positions", padding=10)
        position_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Position list
        position_list_frame = ttk.Frame(position_frame)
        position_list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create treeview for positions
        columns = ('Symbol', 'Quantity', 'Avg Price', 'Current Price', 'P&L', 'P&L %')
        self.position_tree = ttk.Treeview(position_list_frame, columns=columns, show='headings', height=6)
        
        # Configure columns
        for col in columns:
            self.position_tree.heading(col, text=col)
            self.position_tree.column(col, width=100, anchor=tk.CENTER)
        
        # Add scrollbar
        position_scrollbar = ttk.Scrollbar(position_list_frame, orient=tk.VERTICAL, command=self.position_tree.yview)
        self.position_tree.configure(yscrollcommand=position_scrollbar.set)
        
        self.position_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        position_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Recent trades
        trades_frame = ttk.LabelFrame(self.performance_frame, text="Recent Trades", padding=10)
        trades_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create treeview for trades
        trade_columns = ('Time', 'Symbol', 'Side', 'Quantity', 'Price', 'P&L')
        self.trades_tree = ttk.Treeview(trades_frame, columns=trade_columns, show='headings', height=8)
        
        # Configure columns
        for col in trade_columns:
            self.trades_tree.heading(col, text=col)
            self.trades_tree.column(col, width=100, anchor=tk.CENTER)
        
        # Add scrollbar
        trades_scrollbar = ttk.Scrollbar(trades_frame, orient=tk.VERTICAL, command=self.trades_tree.yview)
        self.trades_tree.configure(yscrollcommand=trades_scrollbar.set)
        
        self.trades_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        trades_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def update_quote_data(self, symbol: str, quote: StockQuote) -> None:
        """Update quote display with new data.
        
        Args:
            symbol: Stock symbol.
            quote: Quote data.
        """
        try:
            if symbol != self.selected_symbol.get():
                return
            
            # Update price labels
            self.last_price_label.config(text=f"${quote.price:.2f}")
            
            # Calculate and display price change
            if quote.prev_close and quote.prev_close > 0 and quote.price is not None:
                change = quote.price - quote.prev_close
                change_pct = (change / quote.prev_close) * 100
                
                change_text = f"{change:+.2f} ({change_pct:+.1f}%)"
                change_color = 'green' if change >= 0 else 'red'
                
                self.price_change_label.config(text=change_text, foreground=change_color)
            
            # Update bid/ask
            if quote.bid:
                self.bid_label.config(text=f"${quote.bid:.2f}")
            if quote.ask:
                self.ask_label.config(text=f"${quote.ask:.2f}")
            
            # Update volume
            if quote.volume:
                volume_text = f"{quote.volume:,}"
                self.volume_label.config(text=volume_text)
            
            # Update timestamp
            if quote.timestamp:
                time_text = quote.timestamp.strftime('%H:%M:%S')
                self.quote_update_label.config(text=time_text)
            
        except Exception as e:
            self.logger.error(f"Error updating quote display: {e}")
    
    def update_technical_indicators(self, symbol: str, stock_data: StockData) -> None:
        """Update technical indicators display.
        
        Args:
            symbol: Stock symbol.
            stock_data: Stock data with indicators.
        """
        try:
            if symbol != self.selected_symbol.get():
                return
            
            if not stock_data.indicators:
                return
            
            indicators = stock_data.indicators
            
            # Update RSI
            if indicators.rsi is not None:
                rsi_text = f"{indicators.rsi:.1f}"
                rsi_color = 'red' if indicators.rsi > 70 else 'green' if indicators.rsi < 30 else 'black'
                self.rsi_label.config(text=rsi_text, foreground=rsi_color)
            
            # Update MACD
            if indicators.macd is not None:
                macd_text = f"{indicators.macd:.3f}"
                self.macd_label.config(text=macd_text)
            
            # Update moving averages
            if indicators.sma_20 is not None:
                self.sma20_label.config(text=f"${indicators.sma_20:.2f}")
            
            if indicators.ema_20 is not None:
                self.ema20_label.config(text=f"${indicators.ema_20:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error updating technical indicators: {e}")
    
    def update_positions(self, positions: List[Position]) -> None:
        """Update positions display.
        
        Args:
            positions: List of current positions.
        """
        try:
            # Clear existing items
            for item in self.position_tree.get_children():
                self.position_tree.delete(item)
            
            # Add current positions
            for position in positions:
                # Calculate current P&L (would need current price)
                current_price = position.current_price or position.avg_price
                if current_price is not None and position.avg_price is not None and position.avg_price > 0:
                    pnl = (current_price - position.avg_price) * position.quantity
                    pnl_pct = (pnl / (position.avg_price * position.quantity)) * 100
                else:
                    pnl = 0.0
                    pnl_pct = 0.0
                
                # Format values
                values = (
                    position.symbol,
                    f"{position.quantity:,}",
                    f"${position.avg_price:.2f}",
                    f"${current_price:.2f}",
                    f"${pnl:+.2f}",
                    f"{pnl_pct:+.1f}%"
                )
                
                # Add to tree with color coding
                item = self.position_tree.insert('', tk.END, values=values)
                
                # Color code based on P&L
                if pnl > 0:
                    self.position_tree.set(item, 'P&L', f"${pnl:.2f}")
                    # Note: Treeview doesn't support easy color coding, would need custom styling
            
        except Exception as e:
            self.logger.error(f"Error updating positions display: {e}")
    
    def update_trades(self, trades: List[Trade]) -> None:
        """Update trades display.
        
        Args:
            trades: List of recent trades.
        """
        try:
            # Clear existing items
            for item in self.trades_tree.get_children():
                self.trades_tree.delete(item)
            
            # Add recent trades (last 20)
            recent_trades = sorted(trades, key=lambda t: t.timestamp, reverse=True)[:20]
            
            for trade in recent_trades:
                # Format values
                time_str = trade.timestamp.strftime('%H:%M:%S') if trade.timestamp else '--'
                pnl_str = f"${trade.pnl:.2f}" if trade.pnl is not None else '--'
                
                values = (
                    time_str,
                    trade.symbol,
                    trade.trade_type.value,
                    f"{trade.quantity:,}",
                    f"${trade.price:.2f}",
                    pnl_str
                )
                
                self.trades_tree.insert('', tk.END, values=values)
            
        except Exception as e:
            self.logger.error(f"Error updating trades display: {e}")
    
    def update_chart(self, symbol: str, bars: List[StockBar]) -> None:
        """Update price chart.
        
        Args:
            symbol: Stock symbol.
            bars: Price bar data.
        """
        if not MATPLOTLIB_AVAILABLE or symbol != self.selected_symbol.get():
            return
        
        try:
            # Clear previous plot
            self.ax.clear()
            
            if not bars:
                self.ax.text(0.5, 0.5, 'No data available', 
                           horizontalalignment='center', verticalalignment='center',
                           transform=self.ax.transAxes, fontsize=14)
                self.canvas.draw()
                return
            
            # Extract data
            times = [bar.timestamp for bar in bars]
            prices = [bar.close for bar in bars]
            volumes = [bar.volume for bar in bars]
            
            # Plot price line
            self.ax.plot(times, prices, linewidth=2, color='blue', label='Price')
            
            # Add volume bars (scaled)
            if volumes and max(volumes) > 0:
                ax2 = self.ax.twinx()
                ax2.bar(times, volumes, alpha=0.3, color='gray', width=0.0001)
                ax2.set_ylabel('Volume')
                ax2.tick_params(axis='y', labelcolor='gray')
            
            # Add technical indicators if enabled
            if self.show_indicators.get():
                self._add_chart_indicators(times, bars)
            
            # Add trade markers if enabled
            if self.show_trades.get():
                self._add_trade_markers()
            
            # Configure chart
            self.ax.set_title(f"{symbol} - {self.chart_timeframe.get()}")
            self.ax.set_xlabel("Time")
            self.ax.set_ylabel("Price ($)")
            self.ax.grid(True, alpha=0.3)
            self.ax.legend()
            
            # Format x-axis
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            if len(times) > 20:
                self.ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=max(1, len(times)//10)))
            
            plt.setp(self.ax.xaxis.get_majorticklabels(), rotation=45)
            
            self.fig.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            self.logger.error(f"Error updating chart: {e}")
    
    def _add_chart_indicators(self, times: List[datetime], bars: List[StockBar]) -> None:
        """Add technical indicators to chart.
        
        Args:
            times: Time data.
            bars: Price bar data.
        """
        try:
            # This would calculate and plot indicators
            # For now, just add placeholder moving averages
            if len(bars) >= 20:
                # Simple 20-period moving average
                ma_20 = []
                for i in range(len(bars)):
                    if i >= 19:
                        avg = sum(bar.close for bar in bars[i-19:i+1]) / 20
                        ma_20.append(avg)
                    else:
                        ma_20.append(None)
                
                # Plot moving average
                valid_times = [t for t, ma in zip(times, ma_20) if ma is not None]
                valid_ma = [ma for ma in ma_20 if ma is not None]
                
                if valid_times and valid_ma:
                    self.ax.plot(valid_times, valid_ma, linewidth=1, color='red', 
                               alpha=0.7, label='MA(20)')
            
        except Exception as e:
            self.logger.error(f"Error adding chart indicators: {e}")
    
    def _add_trade_markers(self) -> None:
        """Add trade execution markers to chart."""
        try:
            symbol = self.selected_symbol.get()
            
            # Filter trades for current symbol
            symbol_trades = [t for t in self.trades if t.symbol == symbol]
            
            for trade in symbol_trades:
                if trade.timestamp and trade.price:
                    color = 'green' if trade.trade_type.value == 'buy' else 'red'
                    marker = '^' if trade.trade_type.value == 'buy' else 'v'
                    
                    self.ax.scatter(trade.timestamp, trade.price, 
                                  color=color, marker=marker, s=100, alpha=0.8,
                                  label=f'{trade.trade_type.value.upper()}' if trade == symbol_trades[0] else "")
            
        except Exception as e:
            self.logger.error(f"Error adding trade markers: {e}")
    
    def _on_symbol_change(self, event=None) -> None:
        """Handle symbol selection change."""
        self._refresh_data()
    
    def _on_timeframe_change(self, event=None) -> None:
        """Handle timeframe selection change."""
        self._refresh_data()
    
    def _on_display_option_change(self) -> None:
        """Handle display option changes."""
        if MATPLOTLIB_AVAILABLE:
            # Redraw chart with new options
            symbol = self.selected_symbol.get()
            if symbol in self.price_history:
                self.update_chart(symbol, self.price_history[symbol])
    
    def _on_auto_update_change(self) -> None:
        """Handle auto-update toggle."""
        if self.auto_update.get():
            self._start_auto_update()
        else:
            self._stop_auto_update()
    
    def _start_auto_update(self) -> None:
        """Start automatic data updates."""
        if self._update_thread and self._update_thread.is_alive():
            return
        
        self._stop_update.clear()
        self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self._update_thread.start()
        
        self.logger.info("Started auto-update for data display")
    
    def _stop_auto_update(self) -> None:
        """Stop automatic data updates."""
        self._stop_update.set()
        
        if self._update_thread and self._update_thread.is_alive():
            self._update_thread.join(timeout=1.0)
        
        self.logger.info("Stopped auto-update for data display")
    
    def _update_loop(self) -> None:
        """Auto-update loop."""
        while not self._stop_update.is_set():
            try:
                self._refresh_data()
                time.sleep(self.update_interval)
            except Exception as e:
                self.logger.error(f"Error in update loop: {e}")
                time.sleep(self.update_interval)
    
    def _refresh_data(self) -> None:
        """Refresh displayed data."""
        try:
            # This would normally fetch fresh data from the API
            # For now, just update the display with existing data
            symbol = self.selected_symbol.get()
            
            if symbol in self.current_data:
                stock_data = self.current_data[symbol]
                
                # Update quote if available
                if stock_data.quote:
                    self.update_quote_data(symbol, stock_data.quote)
                
                # Update indicators if available
                self.update_technical_indicators(symbol, stock_data)
            
            # Update chart if data available
            if MATPLOTLIB_AVAILABLE and symbol in self.price_history:
                self.update_chart(symbol, self.price_history[symbol])
            
        except Exception as e:
            self.logger.error(f"Error refreshing data: {e}")
    
    def set_data(self, symbol: str, stock_data: StockData) -> None:
        """Set stock data for display.
        
        Args:
            symbol: Stock symbol.
            stock_data: Stock data to display.
        """
        self.current_data[symbol] = stock_data
        
        # Update price history if bars available
        if stock_data.bars:
            self.price_history[symbol] = stock_data.bars
        
        # Update display if this is the selected symbol
        if symbol == self.selected_symbol.get():
            if stock_data.quote:
                self.update_quote_data(symbol, stock_data.quote)
            
            self.update_technical_indicators(symbol, stock_data)
            
            if MATPLOTLIB_AVAILABLE and stock_data.bars:
                self.update_chart(symbol, stock_data.bars)
    
    def set_trades(self, trades: List[Trade]) -> None:
        """Set trades for display.
        
        Args:
            trades: List of trades.
        """
        self.trades = trades
        self.update_trades(trades)
    
    def set_positions(self, positions: List[Position]) -> None:
        """Set positions for display.
        
        Args:
            positions: List of positions.
        """
        self.positions = positions
        self.update_positions(positions)
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self._stop_auto_update()
        self.logger.info("Data display cleanup complete")