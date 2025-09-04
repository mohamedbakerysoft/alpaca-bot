"""Performance display component for the Alpaca trading bot.

This module provides:
- Trading performance metrics
- P&L visualization
- Win/loss statistics
- Portfolio performance tracking
"""

import logging
import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from ..utils.logging_utils import get_logger
from ..models.trade import Trade, Position


class PerformanceDisplay:
    """Performance display component."""
    
    def __init__(self, parent: tk.Widget):
        """Initialize the performance display.
        
        Args:
            parent: Parent widget.
        """
        self.logger = get_logger(__name__)
        
        # Create main frame
        self.frame = ttk.LabelFrame(parent, text="Performance Metrics", padding=10)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Performance data
        self.trades: List[Trade] = []
        self.positions: List[Position] = []
        
        # Create UI components
        self._create_metrics_display()
        self._create_chart_display()
        
    def _create_metrics_display(self) -> None:
        """Create performance metrics display."""
        # Metrics frame
        metrics_frame = ttk.LabelFrame(self.frame, text="Key Metrics", padding=5)
        metrics_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create metrics labels
        self.total_pnl_label = ttk.Label(metrics_frame, text="Total P&L: $0.00")
        self.total_pnl_label.grid(row=0, column=0, sticky=tk.W, padx=5)
        
        self.win_rate_label = ttk.Label(metrics_frame, text="Win Rate: 0%")
        self.win_rate_label.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        self.total_trades_label = ttk.Label(metrics_frame, text="Total Trades: 0")
        self.total_trades_label.grid(row=1, column=0, sticky=tk.W, padx=5)
        
        self.avg_trade_label = ttk.Label(metrics_frame, text="Avg Trade: $0.00")
        self.avg_trade_label.grid(row=1, column=1, sticky=tk.W, padx=5)
        
        self.max_drawdown_label = ttk.Label(metrics_frame, text="Max Drawdown: $0.00")
        self.max_drawdown_label.grid(row=2, column=0, sticky=tk.W, padx=5)
        
        self.sharpe_ratio_label = ttk.Label(metrics_frame, text="Sharpe Ratio: 0.00")
        self.sharpe_ratio_label.grid(row=2, column=1, sticky=tk.W, padx=5)
        
    def _create_chart_display(self) -> None:
        """Create performance chart display."""
        if not MATPLOTLIB_AVAILABLE:
            chart_label = ttk.Label(self.frame, text="Matplotlib not available for charts")
            chart_label.pack(pady=10)
            return
            
        # Chart frame
        chart_frame = ttk.LabelFrame(self.frame, text="P&L Chart", padding=5)
        chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create matplotlib figure
        self.fig = Figure(figsize=(10, 6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, chart_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Initialize empty chart
        self._update_chart()
        
    def update_trades(self, trades: List[Trade]) -> None:
        """Update performance with new trades.
        
        Args:
            trades: List of trades to analyze.
        """
        self.trades = trades
        self._update_metrics()
        self._update_chart()
        
    def update_positions(self, positions: List[Position]) -> None:
        """Update performance with current positions.
        
        Args:
            positions: List of current positions.
        """
        self.positions = positions
        self._update_metrics()
        
    def _update_metrics(self) -> None:
        """Update performance metrics display."""
        try:
            if not self.trades:
                return
                
            # Calculate metrics
            total_pnl = sum(trade.realized_pnl or 0 for trade in self.trades)
            total_trades = len(self.trades)
            winning_trades = len([t for t in self.trades if (t.realized_pnl or 0) > 0])
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            avg_trade = total_pnl / total_trades if total_trades > 0 else 0
            
            # Calculate drawdown
            cumulative_pnl = []
            running_total = 0
            for trade in self.trades:
                running_total += trade.realized_pnl or 0
                cumulative_pnl.append(running_total)
                
            max_drawdown = 0
            if cumulative_pnl:
                peak = cumulative_pnl[0]
                for pnl in cumulative_pnl:
                    if pnl > peak:
                        peak = pnl
                    drawdown = peak - pnl
                    if drawdown > max_drawdown:
                        max_drawdown = drawdown
            
            # Update labels
            self.total_pnl_label.config(text=f"Total P&L: ${total_pnl:.2f}")
            self.win_rate_label.config(text=f"Win Rate: {win_rate:.1f}%")
            self.total_trades_label.config(text=f"Total Trades: {total_trades}")
            self.avg_trade_label.config(text=f"Avg Trade: ${avg_trade:.2f}")
            self.max_drawdown_label.config(text=f"Max Drawdown: ${max_drawdown:.2f}")
            
            # Simple Sharpe ratio approximation
            if len(self.trades) > 1:
                returns = [trade.realized_pnl or 0 for trade in self.trades]
                avg_return = sum(returns) / len(returns)
                std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
                sharpe = avg_return / std_return if std_return > 0 else 0
                self.sharpe_ratio_label.config(text=f"Sharpe Ratio: {sharpe:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error updating performance metrics: {e}")
            
    def _update_chart(self) -> None:
        """Update performance chart."""
        if not MATPLOTLIB_AVAILABLE:
            return
            
        try:
            self.ax.clear()
            
            if not self.trades:
                self.ax.text(0.5, 0.5, 'No trades yet', 
                           horizontalalignment='center', 
                           verticalalignment='center',
                           transform=self.ax.transAxes)
                self.canvas.draw()
                return
                
            # Calculate cumulative P&L
            dates = []
            cumulative_pnl = []
            running_total = 0
            
            for trade in sorted(self.trades, key=lambda t: t.timestamp):
                dates.append(trade.timestamp)
                running_total += trade.realized_pnl or 0
                cumulative_pnl.append(running_total)
                
            # Plot cumulative P&L
            self.ax.plot(dates, cumulative_pnl, 'b-', linewidth=2, label='Cumulative P&L')
            self.ax.axhline(y=0, color='r', linestyle='--', alpha=0.7)
            
            self.ax.set_title('Cumulative P&L Over Time')
            self.ax.set_xlabel('Time')
            self.ax.set_ylabel('P&L ($)')
            self.ax.grid(True, alpha=0.3)
            self.ax.legend()
            
            # Format x-axis
            if dates:
                self.fig.autofmt_xdate()
                
            self.canvas.draw()
            
        except Exception as e:
            self.logger.error(f"Error updating performance chart: {e}")
            
    def clear_data(self) -> None:
        """Clear all performance data."""
        self.trades = []
        self.positions = []
        self._update_metrics()
        self._update_chart()