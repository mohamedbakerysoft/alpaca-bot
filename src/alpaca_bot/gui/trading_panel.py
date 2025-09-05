"""Trading panel component for the Alpaca trading bot.

This module provides:
- Trading status display
- Position management controls
- Order management interface
- Risk management settings
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..utils.logging_utils import get_logger
from ..models.trade import Trade, Position, TradeType, OrderType, TradeStatus
from ..utils.error_handler import ErrorHandler, safe_execute


class TradingPanel:
    """Trading panel component."""
    
    def __init__(self, parent: tk.Widget):
        """Initialize the trading panel.
        
        Args:
            parent: Parent widget.
        """
        self.logger = get_logger(__name__)
        self.error_handler = ErrorHandler()
        
        # Create main frame with enhanced styling
        self.frame = ttk.LabelFrame(parent, text="Trading Panel", padding=8)
        self.frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Configure frame style for better visibility
        style = ttk.Style()
        style.configure('TradingPanel.TLabelframe', relief='raised', borderwidth=2)
        style.configure('TradingPanel.TLabelframe.Label', font=('TkDefaultFont', 10, 'bold'))
        self.frame.configure(style='TradingPanel.TLabelframe')
        
        # Trading statistics
        self.stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'win_rate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0
        }
        
        self._create_widgets()
    
    def _create_widgets(self) -> None:
        """Create the panel widgets."""
        # Create a more compact layout with key info at the top
        
        # Quick stats section (always visible)
        quick_stats_frame = ttk.Frame(self.frame)
        quick_stats_frame.pack(fill=tk.X, pady=(0, 5))
        
        self._create_quick_stats_section(quick_stats_frame)
        
        # Create notebook for detailed sections
        notebook = ttk.Notebook(self.frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Statistics tab
        stats_frame = ttk.Frame(notebook)
        notebook.add(stats_frame, text="📊 Stats")
        self._create_statistics_section(stats_frame)
        
        # Risk Management tab
        risk_frame = ttk.Frame(notebook)
        notebook.add(risk_frame, text="⚠️ Risk")
        self._create_risk_management_section(risk_frame)
        
        # Manual Trading tab
        manual_frame = ttk.Frame(notebook)
        notebook.add(manual_frame, text="🎯 Manual")
        self._create_manual_trading_section(manual_frame)
        
        # Quick Actions tab
        actions_frame = ttk.Frame(notebook)
        notebook.add(actions_frame, text="⚡ Actions")
        self._create_quick_actions_section(actions_frame)
    
    def _create_quick_stats_section(self, parent: ttk.Frame) -> None:
        """Create quick stats section that's always visible.
        
        Args:
            parent: Parent frame.
        """
        # Create a horizontal layout for key metrics
        stats_container = ttk.Frame(parent)
        stats_container.pack(fill=tk.X)
        
        # PnL display (most important)
        pnl_frame = ttk.Frame(stats_container)
        pnl_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(pnl_frame, text="P&L:", font=('TkDefaultFont', 9)).pack(side=tk.LEFT)
        self.quick_pnl_label = ttk.Label(
            pnl_frame, 
            text="$0.00", 
            font=('TkDefaultFont', 10, 'bold'),
            foreground='black'
        )
        self.quick_pnl_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Trades count
        trades_frame = ttk.Frame(stats_container)
        trades_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(trades_frame, text="Trades:", font=('TkDefaultFont', 9)).pack(side=tk.LEFT)
        self.quick_trades_label = ttk.Label(
            trades_frame, 
            text="0", 
            font=('TkDefaultFont', 10, 'bold')
        )
        self.quick_trades_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Win rate
        winrate_frame = ttk.Frame(stats_container)
        winrate_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(winrate_frame, text="Win Rate:", font=('TkDefaultFont', 9)).pack(side=tk.LEFT)
        self.quick_winrate_label = ttk.Label(
            winrate_frame, 
            text="0%", 
            font=('TkDefaultFont', 10, 'bold')
        )
        self.quick_winrate_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Status indicator
        status_frame = ttk.Frame(stats_container)
        status_frame.pack(side=tk.RIGHT)
        
        self.status_indicator = ttk.Label(
            status_frame,
            text="● READY",
            font=('TkDefaultFont', 9, 'bold'),
            foreground='orange'
        )
        self.status_indicator.pack(side=tk.RIGHT)
    
    def _create_quick_actions_section(self, parent: ttk.Frame) -> None:
        """Create quick actions section.
        
        Args:
            parent: Parent frame.
        """
        # Emergency controls
        emergency_frame = ttk.LabelFrame(parent, text="Emergency Controls", padding=10)
        emergency_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Close all positions button
        close_all_btn = ttk.Button(
            emergency_frame,
            text="🚨 Close All Positions",
            command=self._close_all_positions,
            style="Accent.TButton"
        )
        close_all_btn.pack(fill=tk.X, pady=(0, 5))
        
        # Cancel all orders button
        cancel_all_btn = ttk.Button(
            emergency_frame,
            text="❌ Cancel All Orders",
            command=self._cancel_all_orders
        )
        cancel_all_btn.pack(fill=tk.X, pady=(0, 5))
        
        # Pause trading button
        self.pause_btn = ttk.Button(
            emergency_frame,
            text="⏸️ Pause Trading",
            command=self._toggle_pause
        )
        self.pause_btn.pack(fill=tk.X)
        
        # Quick trade section
        quick_trade_frame = ttk.LabelFrame(parent, text="Quick Trade", padding=10)
        quick_trade_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Symbol entry
        symbol_frame = ttk.Frame(quick_trade_frame)
        symbol_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(symbol_frame, text="Symbol:").pack(side=tk.LEFT)
        self.quick_symbol_var = tk.StringVar()
        symbol_entry = ttk.Entry(
            symbol_frame,
            textvariable=self.quick_symbol_var,
            width=10
        )
        symbol_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # Quantity entry
        ttk.Label(symbol_frame, text="Qty:").pack(side=tk.LEFT, padx=(10, 0))
        self.quick_qty_var = tk.StringVar(value="100")
        qty_entry = ttk.Entry(
            symbol_frame,
            textvariable=self.quick_qty_var,
            width=8
        )
        qty_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # Buy/Sell buttons
        buttons_frame = ttk.Frame(quick_trade_frame)
        buttons_frame.pack(fill=tk.X)
        
        buy_btn = ttk.Button(
            buttons_frame,
            text="📈 Quick Buy",
            command=self._quick_buy,
            style="Accent.TButton"
        )
        buy_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        
        sell_btn = ttk.Button(
            buttons_frame,
            text="📉 Quick Sell",
            command=self._quick_sell
        )
        sell_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))
    
    def _create_statistics_section(self, parent: ttk.Frame) -> None:
        """Create the statistics section.
        
        Args:
            parent: Parent frame.
        """
        # Today's performance
        today_frame = ttk.LabelFrame(parent, text="Today's Performance", padding=10)
        today_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create statistics display
        stats_grid = ttk.Frame(today_frame)
        stats_grid.pack(fill=tk.X)
        
        # Row 1: Trades and Win Rate
        ttk.Label(stats_grid, text="Total Trades:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.total_trades_label = ttk.Label(stats_grid, text="0", font=('TkDefaultFont', 10, 'bold'))
        self.total_trades_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(stats_grid, text="Win Rate:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.win_rate_label = ttk.Label(stats_grid, text="0.0%", font=('TkDefaultFont', 10, 'bold'))
        self.win_rate_label.grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Row 2: Winning and Losing Trades
        ttk.Label(stats_grid, text="Winning:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.winning_trades_label = ttk.Label(stats_grid, text="0", foreground='green')
        self.winning_trades_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(stats_grid, text="Losing:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        self.losing_trades_label = ttk.Label(stats_grid, text="0", foreground='red')
        self.losing_trades_label.grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Row 3: P&L
        ttk.Label(stats_grid, text="Total P&L:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.total_pnl_label = ttk.Label(stats_grid, text="$0.00", font=('TkDefaultFont', 10, 'bold'))
        self.total_pnl_label.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Row 4: Average Win/Loss
        ttk.Label(stats_grid, text="Avg Win:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.avg_win_label = ttk.Label(stats_grid, text="$0.00", foreground='green')
        self.avg_win_label.grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(stats_grid, text="Avg Loss:").grid(row=3, column=2, sticky=tk.W, padx=5, pady=2)
        self.avg_loss_label = ttk.Label(stats_grid, text="$0.00", foreground='red')
        self.avg_loss_label.grid(row=3, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Configure grid weights
        for i in range(4):
            stats_grid.columnconfigure(i, weight=1)
        
        # Reset button
        reset_frame = ttk.Frame(today_frame)
        reset_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(
            reset_frame,
            text="Reset Statistics",
            command=self._reset_statistics
        ).pack(side=tk.LEFT)
        
        # Last update time
        self.last_update_label = ttk.Label(
            reset_frame,
            text="Last updated: Never",
            font=('TkDefaultFont', 8)
        )
        self.last_update_label.pack(side=tk.RIGHT)
    
    def _create_risk_management_section(self, parent: ttk.Frame) -> None:
        """Create the risk management section.
        
        Args:
            parent: Parent frame.
        """
        # Position sizing
        sizing_frame = ttk.LabelFrame(parent, text="Position Sizing", padding=10)
        sizing_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Max position size
        max_pos_frame = ttk.Frame(sizing_frame)
        max_pos_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(max_pos_frame, text="Max Position Size ($):").pack(side=tk.LEFT)
        
        self.max_position_var = tk.DoubleVar(value=1000.0)
        max_pos_spinbox = ttk.Spinbox(
            max_pos_frame,
            from_=100.0,
            to=50000.0,
            increment=100.0,
            width=10,
            textvariable=self.max_position_var
        )
        max_pos_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        
        # Risk per trade
        risk_frame = ttk.Frame(sizing_frame)
        risk_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(risk_frame, text="Risk per Trade (%):").pack(side=tk.LEFT)
        
        self.risk_per_trade_var = tk.DoubleVar(value=1.0)
        risk_spinbox = ttk.Spinbox(
            risk_frame,
            from_=0.1,
            to=10.0,
            increment=0.1,
            width=10,
            textvariable=self.risk_per_trade_var
        )
        risk_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        
        # Stop loss and take profit
        stops_frame = ttk.LabelFrame(parent, text="Stop Loss & Take Profit", padding=10)
        stops_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Stop loss percentage
        sl_frame = ttk.Frame(stops_frame)
        sl_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(sl_frame, text="Stop Loss (%):").pack(side=tk.LEFT)
        
        self.stop_loss_var = tk.DoubleVar(value=2.0)
        sl_spinbox = ttk.Spinbox(
            sl_frame,
            from_=0.5,
            to=10.0,
            increment=0.1,
            width=10,
            textvariable=self.stop_loss_var
        )
        sl_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        
        # Take profit percentage
        tp_frame = ttk.Frame(stops_frame)
        tp_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(tp_frame, text="Take Profit (%):").pack(side=tk.LEFT)
        
        self.take_profit_var = tk.DoubleVar(value=3.0)
        tp_spinbox = ttk.Spinbox(
            tp_frame,
            from_=0.5,
            to=20.0,
            increment=0.1,
            width=10,
            textvariable=self.take_profit_var
        )
        tp_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        
        # Daily limits
        limits_frame = ttk.LabelFrame(parent, text="Daily Limits", padding=10)
        limits_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Max daily loss
        max_loss_frame = ttk.Frame(limits_frame)
        max_loss_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(max_loss_frame, text="Max Daily Loss ($):").pack(side=tk.LEFT)
        
        self.max_daily_loss_var = tk.DoubleVar(value=500.0)
        max_loss_spinbox = ttk.Spinbox(
            max_loss_frame,
            from_=50.0,
            to=5000.0,
            increment=50.0,
            width=10,
            textvariable=self.max_daily_loss_var
        )
        max_loss_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        
        # Max daily trades
        max_trades_frame = ttk.Frame(limits_frame)
        max_trades_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(max_trades_frame, text="Max Daily Trades:").pack(side=tk.LEFT)
        
        self.max_daily_trades_var = tk.IntVar(value=20)
        max_trades_spinbox = ttk.Spinbox(
            max_trades_frame,
            from_=1,
            to=100,
            increment=1,
            width=10,
            textvariable=self.max_daily_trades_var
        )
        max_trades_spinbox.pack(side=tk.LEFT, padx=(5, 0))
    
    def _create_manual_trading_section(self, parent: ttk.Frame) -> None:
        """Create the manual trading section.
        
        Args:
            parent: Parent frame.
        """
        # Quick trade frame
        trade_frame = ttk.LabelFrame(parent, text="Quick Trade", padding=10)
        trade_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Symbol input
        symbol_frame = ttk.Frame(trade_frame)
        symbol_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(symbol_frame, text="Symbol:").pack(side=tk.LEFT)
        
        self.manual_symbol_var = tk.StringVar()
        symbol_entry = ttk.Entry(
            symbol_frame,
            textvariable=self.manual_symbol_var,
            width=10
        )
        symbol_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # Quantity input
        qty_frame = ttk.Frame(trade_frame)
        qty_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(qty_frame, text="Quantity:").pack(side=tk.LEFT)
        
        self.manual_quantity_var = tk.IntVar(value=100)
        qty_spinbox = ttk.Spinbox(
            qty_frame,
            from_=1,
            to=10000,
            increment=1,
            width=10,
            textvariable=self.manual_quantity_var
        )
        qty_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        
        # Order type
        order_frame = ttk.Frame(trade_frame)
        order_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(order_frame, text="Order Type:").pack(side=tk.LEFT)
        
        self.order_type_var = tk.StringVar(value="market")
        order_combo = ttk.Combobox(
            order_frame,
            textvariable=self.order_type_var,
            values=["market", "limit", "stop", "stop_limit"],
            state="readonly",
            width=12
        )
        order_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # Price input (for limit orders)
        price_frame = ttk.Frame(trade_frame)
        price_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(price_frame, text="Price ($):").pack(side=tk.LEFT)
        
        self.manual_price_var = tk.DoubleVar(value=0.0)
        price_spinbox = ttk.Spinbox(
            price_frame,
            from_=0.01,
            to=10000.0,
            increment=0.01,
            width=10,
            textvariable=self.manual_price_var
        )
        price_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        
        # Trade buttons
        button_frame = ttk.Frame(trade_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        buy_btn = ttk.Button(
            button_frame,
            text="Buy",
            command=lambda: self._manual_trade("buy")
        )
        buy_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        sell_btn = ttk.Button(
            button_frame,
            text="Sell",
            command=lambda: self._manual_trade("sell")
        )
        sell_btn.pack(side=tk.LEFT, padx=5)
        
        # Emergency controls
        emergency_frame = ttk.LabelFrame(parent, text="Emergency Controls", padding=10)
        emergency_frame.pack(fill=tk.X, padx=5, pady=5)
        
        emergency_button_frame = ttk.Frame(emergency_frame)
        emergency_button_frame.pack(fill=tk.X)
        
        close_all_btn = ttk.Button(
            emergency_button_frame,
            text="Close All Positions",
            command=self._close_all_positions
        )
        close_all_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        cancel_all_btn = ttk.Button(
            emergency_button_frame,
            text="Cancel All Orders",
            command=self._cancel_all_orders
        )
        cancel_all_btn.pack(side=tk.LEFT, padx=5)
        
        # Warning label
        warning_label = ttk.Label(
            emergency_frame,
            text="⚠️ Use emergency controls with caution!",
            foreground='red',
            font=('TkDefaultFont', 8)
        )
        warning_label.pack(pady=(5, 0))
    
    def update_statistics(self, trades: List[Trade]) -> None:
        """Update trading statistics.
        
        Args:
            trades: List of completed trades.
        """
        try:
            # Reset statistics
            self.stats = {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'total_pnl': 0.0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0
            }
            
            # Calculate statistics from trades
            winning_pnls = []
            losing_pnls = []
            
            for trade in trades:
                if trade.status == TradeStatus.CLOSED and trade.pnl is not None:
                    self.stats['total_trades'] += 1
                    self.stats['total_pnl'] += trade.pnl
                    
                    if trade.pnl > 0:
                        self.stats['winning_trades'] += 1
                        winning_pnls.append(trade.pnl)
                    else:
                        self.stats['losing_trades'] += 1
                        losing_pnls.append(trade.pnl)
            
            # Calculate derived statistics
            if self.stats['total_trades'] > 0:
                self.stats['win_rate'] = (self.stats['winning_trades'] / self.stats['total_trades']) * 100
            
            if winning_pnls:
                self.stats['avg_win'] = sum(winning_pnls) / len(winning_pnls)
            
            if losing_pnls:
                self.stats['avg_loss'] = sum(losing_pnls) / len(losing_pnls)
            
            # Update display
            self._update_statistics_display()
            
        except Exception as e:
            self.logger.error(f"Error updating statistics: {e}")
    
    def _update_statistics_display(self) -> None:
        """Update the statistics display."""
        def _update_display() -> None:
            """Internal function to update the display."""
            # Update labels
            self.total_trades_label.config(text=str(self.stats['total_trades']))
            self.winning_trades_label.config(text=str(self.stats['winning_trades']))
            self.losing_trades_label.config(text=str(self.stats['losing_trades']))
            
            # Format and color P&L
            pnl_text = f"${self.stats['total_pnl']:+.2f}"
            pnl_color = 'green' if self.stats['total_pnl'] >= 0 else 'red'
            self.total_pnl_label.config(text=pnl_text, foreground=pnl_color)
            
            # Win rate
            self.win_rate_label.config(text=f"{self.stats['win_rate']:.1f}%")
            
            # Average win/loss
            self.avg_win_label.config(text=f"${self.stats['avg_win']:+.2f}")
            self.avg_loss_label.config(text=f"${self.stats['avg_loss']:+.2f}")
            
            # Update timestamp
            current_time = datetime.now().strftime('%H:%M:%S')
            self.last_update_label.config(text=f"Last updated: {current_time}")
        
        def _handle_display_error(error: Exception) -> None:
            """Handle display update errors."""
            self.logger.error(f"Error updating statistics display: {error}")
        
        safe_execute(
            _update_display,
            default_return=None,
            log_errors=True
        )
    
    def _reset_statistics(self) -> None:
        """Reset trading statistics."""
        if messagebox.askyesno("Confirm Reset", "Reset all trading statistics?"):
            self.stats = {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'total_pnl': 0.0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0
            }
            
            self._update_statistics_display()
            self.logger.info("Trading statistics reset")
    
    def _manual_trade(self, side: str) -> None:
        """Execute a manual trade.
        
        Args:
            side: Trade side ('buy' or 'sell').
        """
        try:
            symbol = self.manual_symbol_var.get().strip().upper()
            quantity = self.manual_quantity_var.get()
            order_type = self.order_type_var.get()
            price = self.manual_price_var.get() if order_type != "market" else None
            
            if not symbol:
                messagebox.showerror("Error", "Please enter a symbol")
                return
            
            if quantity <= 0:
                messagebox.showerror("Error", "Quantity must be greater than 0")
                return
            
            if order_type != "market" and (not price or price <= 0):
                messagebox.showerror("Error", "Please enter a valid price for limit orders")
                return
            
            # Confirm trade
            price_text = f" at ${price:.2f}" if price else " at market price"
            if not messagebox.askyesno(
                "Confirm Trade",
                f"{side.upper()} {quantity} shares of {symbol}{price_text}?"
            ):
                return
            
            # This would normally execute the trade through the strategy
            # For now, just show a message
            messagebox.showinfo(
                "Trade Submitted",
                f"Manual {side} order submitted for {symbol}"
            )
            
            self.logger.info(f"Manual {side} order submitted: {symbol} x{quantity}")
            
        except Exception as e:
            self.logger.error(f"Error executing manual trade: {e}")
            messagebox.showerror("Trade Error", f"Error executing trade: {e}")
    
    def _close_all_positions(self) -> None:
        """Close all open positions."""
        if messagebox.askyesno(
            "Confirm Close All",
            "Close ALL open positions? This action cannot be undone."
        ):
            # This would normally close all positions through the strategy
            messagebox.showinfo(
                "Positions Closed",
                "All positions have been closed"
            )
            
            self.logger.warning("Emergency: All positions closed")
    
    def _cancel_all_orders(self) -> None:
        """Cancel all pending orders."""
        if messagebox.askyesno(
            "Confirm Cancel All",
            "Cancel ALL pending orders?"
        ):
            # This would normally cancel all orders through the strategy
            messagebox.showinfo(
                "Orders Cancelled",
                "All pending orders have been cancelled"
            )
            
            self.logger.warning("Emergency: All orders cancelled")
    
    def get_risk_parameters(self) -> Dict[str, Any]:
        """Get current risk management parameters.
        
        Returns:
            Dictionary of risk parameters.
        """
        return {
            'max_position_size': self.max_position_var.get(),
            'risk_per_trade': self.risk_per_trade_var.get(),
            'stop_loss_pct': self.stop_loss_var.get(),
            'take_profit_pct': self.take_profit_var.get(),
            'max_daily_loss': self.max_daily_loss_var.get(),
            'max_daily_trades': self.max_daily_trades_var.get()
        }
    
    def set_risk_parameters(self, params: Dict[str, Any]) -> None:
        """Set risk management parameters.
        
        Args:
            params: Dictionary of risk parameters.
        """
        try:
            if 'max_position_size' in params:
                self.max_position_var.set(params['max_position_size'])
            
            if 'risk_per_trade' in params:
                self.risk_per_trade_var.set(params['risk_per_trade'])
            
            if 'stop_loss_pct' in params:
                self.stop_loss_var.set(params['stop_loss_pct'])
            
            if 'take_profit_pct' in params:
                self.take_profit_var.set(params['take_profit_pct'])
            
            if 'max_daily_loss' in params:
                self.max_daily_loss_var.set(params['max_daily_loss'])
            
            if 'max_daily_trades' in params:
                self.max_daily_trades_var.set(params['max_daily_trades'])
            
            self.logger.info("Risk parameters updated")
            
        except Exception as e:
            self.logger.error(f"Error setting risk parameters: {e}")
    
    def _close_all_positions(self) -> None:
        """Close all open positions."""
        try:
            # This would integrate with the trading strategy
            # For now, just show a confirmation dialog
            import tkinter.messagebox as msgbox
            result = msgbox.askyesno(
                "Confirm Close All",
                "Are you sure you want to close ALL positions?\n\nThis action cannot be undone.",
                icon="warning"
            )
            if result:
                # TODO: Implement actual position closing logic
                self.status_indicator.config(text="● CLOSING ALL", foreground="red")
                self.logger.info("Closing all positions...")
        except Exception as e:
            self.logger.error(f"Error closing positions: {e}")
    
    def _cancel_all_orders(self) -> None:
        """Cancel all pending orders."""
        try:
            import tkinter.messagebox as msgbox
            result = msgbox.askyesno(
                "Confirm Cancel All",
                "Are you sure you want to cancel ALL pending orders?",
                icon="warning"
            )
            if result:
                # TODO: Implement actual order cancellation logic
                self.status_indicator.config(text="● CANCELING", foreground="red")
                self.logger.info("Canceling all orders...")
        except Exception as e:
            self.logger.error(f"Error canceling orders: {e}")
    
    def _toggle_pause(self) -> None:
        """Toggle trading pause state."""
        try:
            current_text = self.pause_btn.cget("text")
            if "Pause" in current_text:
                self.pause_btn.config(text="▶️ Resume Trading")
                self.status_indicator.config(text="● PAUSED", foreground="orange")
                self.logger.info("Trading paused")
            else:
                self.pause_btn.config(text="⏸️ Pause Trading")
                self.status_indicator.config(text="● ACTIVE", foreground="green")
                self.logger.info("Trading resumed")
        except Exception as e:
            self.logger.error(f"Error toggling pause: {e}")
    
    def _quick_buy(self) -> None:
        """Execute a quick buy order."""
        try:
            symbol = self.quick_symbol_var.get().upper().strip()
            qty_str = self.quick_qty_var.get().strip()
            
            if not symbol:
                import tkinter.messagebox as msgbox
                msgbox.showerror("Error", "Please enter a symbol")
                return
            
            try:
                qty = int(qty_str)
                if qty <= 0:
                    raise ValueError("Quantity must be positive")
            except ValueError:
                import tkinter.messagebox as msgbox
                msgbox.showerror("Error", "Please enter a valid quantity")
                return
            
            # TODO: Implement actual buy logic
            self.logger.info(f"Quick buy: {qty} shares of {symbol}")
            self.status_indicator.config(text="● BUYING", foreground="blue")
            
        except Exception as e:
            self.logger.error(f"Error executing quick buy: {e}")
    
    def _quick_sell(self) -> None:
        """Execute a quick sell order."""
        try:
            symbol = self.quick_symbol_var.get().upper().strip()
            qty_str = self.quick_qty_var.get().strip()
            
            if not symbol:
                import tkinter.messagebox as msgbox
                msgbox.showerror("Error", "Please enter a symbol")
                return
            
            try:
                qty = int(qty_str)
                if qty <= 0:
                    raise ValueError("Quantity must be positive")
            except ValueError:
                import tkinter.messagebox as msgbox
                msgbox.showerror("Error", "Please enter a valid quantity")
                return
            
            # TODO: Implement actual sell logic
            self.logger.info(f"Quick sell: {qty} shares of {symbol}")
            self.status_indicator.config(text="● SELLING", foreground="red")
            
        except Exception as e:
            self.logger.error(f"Error executing quick sell: {e}")
    
    def update_quick_stats(self, pnl: float = 0.0, trades: int = 0, win_rate: float = 0.0) -> None:
        """Update the quick stats display.
        
        Args:
            pnl: Current profit/loss.
            trades: Total number of trades.
            win_rate: Win rate percentage.
        """
        try:
            # Update P&L with color coding
            pnl_text = f"${pnl:,.2f}"
            pnl_color = "green" if pnl > 0 else "red" if pnl < 0 else "black"
            self.quick_pnl_label.config(text=pnl_text, foreground=pnl_color)
            
            # Update trades count
            self.quick_trades_label.config(text=str(trades))
            
            # Update win rate with color coding
            win_rate_text = f"{win_rate:.1f}%"
            win_rate_color = "green" if win_rate >= 60 else "orange" if win_rate >= 40 else "red"
            self.quick_winrate_label.config(text=win_rate_text, foreground=win_rate_color)
            
        except Exception as e:
            self.logger.error(f"Error updating quick stats: {e}")