"""Configuration panel for the Alpaca trading bot.

This module provides:
- Strategy parameter configuration
- Risk management settings
- API configuration
- Trading preferences
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, Any, Callable, Optional
import json
import os
from pathlib import Path

from ..utils.logging_utils import get_logger
from ..config.settings import Settings


class ConfigPanel:
    """Configuration panel for trading bot settings."""
    
    def __init__(self, parent: tk.Widget, settings: Settings, on_settings_change: Optional[Callable] = None):
        """Initialize the configuration panel.
        
        Args:
            parent: Parent widget (can be a notebook or regular frame).
            settings: Settings instance.
            on_settings_change: Callback for when settings change.
        """
        self.logger = get_logger(__name__)
        self.settings = settings
        self.on_settings_change = on_settings_change
        
        # Check if parent is a notebook
        self.is_notebook_parent = isinstance(parent, ttk.Notebook)
        
        if self.is_notebook_parent:
            # Parent is a notebook, we'll add tabs directly to it
            self.notebook = parent
        else:
            # Create main frame for standalone use
            self.frame = ttk.LabelFrame(parent, text="Configuration", padding=10)
            self.frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create custom styles for visual indicators
        self.style = ttk.Style()
        self.style.configure('Active.TEntry', fieldbackground='#e8f5e8', bordercolor='#4CAF50')
        
        # Configuration variables
        self.config_vars = {}
        self._create_config_vars()
        
        # Create widgets
        self._create_widgets()
        
        # Load current settings
        self._load_settings()
    
    def _create_config_vars(self) -> None:
        """Create tkinter variables for configuration."""
        # Strategy parameters
        self.config_vars.update({
            # Support/Resistance
            'support_resistance_lookback': tk.IntVar(value=20),
            'support_resistance_min_touches': tk.IntVar(value=2),
            'support_resistance_tolerance': tk.DoubleVar(value=0.01),
            
            # RSI parameters
            'rsi_period': tk.IntVar(value=14),
            'rsi_oversold': tk.DoubleVar(value=30.0),
            'rsi_overbought': tk.DoubleVar(value=70.0),
            
            # Bollinger Bands
            'bb_period': tk.IntVar(value=20),
            'bb_std_dev': tk.DoubleVar(value=2.0),
            
            # MACD parameters
            'macd_fast': tk.IntVar(value=12),
            'macd_slow': tk.IntVar(value=26),
            'macd_signal': tk.IntVar(value=9),
            
            # Position sizing
            'position_size_method': tk.StringVar(value='fixed_amount'),
            'fixed_position_amount': tk.DoubleVar(value=1000.0),
            'position_size_percent': tk.DoubleVar(value=2.0),
            'max_position_size': tk.DoubleVar(value=10000.0),
            
            # Fixed Trade Amount Feature
            'fixed_trade_amount_enabled': tk.BooleanVar(value=False),
            'fixed_trade_amount': tk.DoubleVar(value=100.0),
            
            # Custom Portfolio Value Feature
            'custom_portfolio_value_enabled': tk.BooleanVar(value=False),
            'custom_portfolio_value': tk.DoubleVar(value=10000.0),
            
            # Risk management
            'stop_loss_percent': tk.DoubleVar(value=2.0),
            'take_profit_percent': tk.DoubleVar(value=3.0),
            'max_daily_loss': tk.DoubleVar(value=500.0),
            'max_daily_trades': tk.IntVar(value=20),
            'max_positions': tk.IntVar(value=5),
            
            # Trading hours
            'trading_start_hour': tk.IntVar(value=9),
            'trading_start_minute': tk.IntVar(value=30),
            'trading_end_hour': tk.IntVar(value=15),
            'trading_end_minute': tk.IntVar(value=30),
            
            # Data settings
            'data_update_interval': tk.IntVar(value=5),
            'chart_timeframe': tk.StringVar(value='1Min'),
            'max_bars_history': tk.IntVar(value=1000),
            
            # Auto-selection criteria
            'auto_select_enabled': tk.BooleanVar(value=False),
            'auto_select_max_symbols': tk.IntVar(value=10),
            'auto_select_min_volume': tk.IntVar(value=1000000),
            'auto_select_min_price': tk.DoubleVar(value=10.0),
            'auto_select_max_price': tk.DoubleVar(value=500.0),
            'auto_select_min_volatility': tk.DoubleVar(value=0.02),
            
            # Logging
            'log_level': tk.StringVar(value='INFO'),
            'log_to_file': tk.BooleanVar(value=True),
            'max_log_files': tk.IntVar(value=10),
            
            # Trading mode
            'trading_mode': tk.StringVar(value='conservative'),
        })
    
    def _create_widgets(self) -> None:
        """Create the configuration widgets."""
        if not self.is_notebook_parent:
            # Create notebook for different configuration sections
            self.notebook = ttk.Notebook(self.frame)
            self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Strategy tab
        self._create_strategy_tab()
        
        # Risk Management tab
        self._create_risk_tab()
        
        # Trading Hours tab
        self._create_trading_hours_tab()
        
        # Auto-Selection tab
        self._create_auto_selection_tab()
        
        # Data & Display tab
        self._create_data_tab()
        
        # Logging tab
        self._create_logging_tab()
        
        # Control buttons (only for standalone mode)
        if not self.is_notebook_parent:
            self._create_control_buttons()
    
    def _create_strategy_tab(self) -> None:
        """Create strategy parameters tab."""
        strategy_frame = ttk.Frame(self.notebook)
        self.notebook.add(strategy_frame, text="Strategy")
        
        # Create scrollable frame
        canvas = tk.Canvas(strategy_frame)
        scrollbar = ttk.Scrollbar(strategy_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Support/Resistance section
        sr_frame = ttk.LabelFrame(scrollable_frame, text="Support/Resistance Detection", padding=10)
        sr_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self._create_labeled_spinbox(sr_frame, "Lookback Period:", 'support_resistance_lookback', 5, 100, row=0)
        self._create_labeled_spinbox(sr_frame, "Min Touches:", 'support_resistance_min_touches', 1, 10, row=1)
        self._create_labeled_entry(sr_frame, "Tolerance (%):", 'support_resistance_tolerance', row=2)
        
        # RSI section
        rsi_frame = ttk.LabelFrame(scrollable_frame, text="RSI Parameters", padding=10)
        rsi_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self._create_labeled_spinbox(rsi_frame, "RSI Period:", 'rsi_period', 5, 50, row=0)
        self._create_labeled_entry(rsi_frame, "Oversold Level:", 'rsi_oversold', row=1)
        self._create_labeled_entry(rsi_frame, "Overbought Level:", 'rsi_overbought', row=2)
        
        # Bollinger Bands section
        bb_frame = ttk.LabelFrame(scrollable_frame, text="Bollinger Bands", padding=10)
        bb_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self._create_labeled_spinbox(bb_frame, "Period:", 'bb_period', 5, 50, row=0)
        self._create_labeled_entry(bb_frame, "Standard Deviations:", 'bb_std_dev', row=1)
        
        # MACD section
        macd_frame = ttk.LabelFrame(scrollable_frame, text="MACD Parameters", padding=10)
        macd_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self._create_labeled_spinbox(macd_frame, "Fast Period:", 'macd_fast', 5, 50, row=0)
        self._create_labeled_spinbox(macd_frame, "Slow Period:", 'macd_slow', 10, 100, row=1)
        self._create_labeled_spinbox(macd_frame, "Signal Period:", 'macd_signal', 5, 20, row=2)
        
        # Trading mode section
        mode_frame = ttk.LabelFrame(scrollable_frame, text="Trading Mode", padding=10)
        mode_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(mode_frame, text="Trading Mode:").pack(anchor=tk.W, pady=2)
        mode_combo = ttk.Combobox(
            mode_frame,
            textvariable=self.config_vars['trading_mode'],
            values=['ultra_safe', 'conservative', 'aggressive'],
            state='readonly',
            width=20
        )
        mode_combo.pack(anchor=tk.W, pady=2)
        
        # Mode descriptions
        descriptions = {
            'ultra_safe': 'Ultra-Safe: Minimal risk, very conservative parameters',
            'conservative': 'Conservative: Balanced risk and reward (default)',
            'aggressive': 'Aggressive: Higher risk, more frequent trades'
        }
        
        desc_label = ttk.Label(mode_frame, text=descriptions['conservative'], foreground='gray')
        desc_label.pack(anchor=tk.W, pady=2)
        
        def update_description(event=None):
            selected = self.config_vars['trading_mode'].get()
            desc_label.config(text=descriptions.get(selected, ''))
        
        mode_combo.bind('<<ComboboxSelected>>', update_description)
        self.config_vars['trading_mode'].trace('w', lambda *args: update_description())
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _create_risk_tab(self) -> None:
        """Create risk management tab."""
        risk_frame = ttk.Frame(self.notebook)
        self.notebook.add(risk_frame, text="Risk Management")
        
        # Position sizing section
        position_frame = ttk.LabelFrame(risk_frame, text="Position Sizing", padding=10)
        position_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Fixed Trade Amount Feature
        self.fixed_amount_frame = ttk.LabelFrame(position_frame, text="Fixed Trade Amount", padding=5)
        self.fixed_amount_frame.grid(row=0, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=5)
        
        # Enable/Disable checkbox
        fixed_amount_check = ttk.Checkbutton(
            self.fixed_amount_frame,
            text="Enable Fixed Trade Amount",
            variable=self.config_vars['fixed_trade_amount_enabled']
        )
        fixed_amount_check.grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        
        # Fixed amount input
        ttk.Label(self.fixed_amount_frame, text="Fixed Amount ($):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.fixed_amount_entry = ttk.Entry(
            self.fixed_amount_frame,
            textvariable=self.config_vars['fixed_trade_amount'],
            width=15
        )
        self.fixed_amount_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Add validation to the fixed amount entry
        self.config_vars['fixed_trade_amount'].trace('w', self._validate_fixed_trade_amount)
        
        # Status indicator
        self.fixed_amount_status = ttk.Label(
            self.fixed_amount_frame,
            text="Inactive",
            foreground="gray"
        )
        self.fixed_amount_status.grid(row=1, column=2, sticky=tk.W, padx=10, pady=2)
        
        # Separator
        ttk.Separator(position_frame, orient='horizontal').grid(row=1, column=0, columnspan=3, sticky=tk.EW, pady=10)
        
        # Position sizing method
        ttk.Label(position_frame, text="Method:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.position_method_combo = ttk.Combobox(
            position_frame,
            textvariable=self.config_vars['position_size_method'],
            values=['fixed_amount', 'percent_of_portfolio', 'volatility_based'],
            state="readonly",
            width=20
        )
        self.position_method_combo.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        self._create_labeled_entry(position_frame, "Fixed Amount ($):", 'fixed_position_amount', row=3)
        self._create_labeled_entry(position_frame, "Portfolio Percent (%):", 'position_size_percent', row=4)
        self._create_labeled_entry(position_frame, "Max Position Size ($):", 'max_position_size', row=5)
        
        # Update status indicator when checkbox changes
        self.config_vars['fixed_trade_amount_enabled'].trace('w', lambda *args: self._update_fixed_amount_status())
        self._update_fixed_amount_status()  # Initial update
        
        # Custom Portfolio Value Feature
        self.portfolio_value_frame = ttk.LabelFrame(position_frame, text="Custom Portfolio Value", padding=5)
        self.portfolio_value_frame.grid(row=6, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=5)
        
        # Enable/Disable checkbox
        portfolio_value_check = ttk.Checkbutton(
            self.portfolio_value_frame,
            text="Enable Custom Portfolio Value",
            variable=self.config_vars['custom_portfolio_value_enabled']
        )
        portfolio_value_check.grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        
        # Custom portfolio value input
        ttk.Label(self.portfolio_value_frame, text="Portfolio Value ($):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.portfolio_value_entry = ttk.Entry(
            self.portfolio_value_frame,
            textvariable=self.config_vars['custom_portfolio_value'],
            width=15
        )
        self.portfolio_value_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Add validation to the portfolio value entry
        self.config_vars['custom_portfolio_value'].trace('w', self._validate_custom_portfolio_value)
        
        # Status indicator
        self.portfolio_value_status = ttk.Label(
            self.portfolio_value_frame,
            text="Using Real Portfolio Value",
            foreground="gray"
        )
        self.portfolio_value_status.grid(row=1, column=2, sticky=tk.W, padx=10, pady=2)
        
        # Update status indicator when checkbox changes
        self.config_vars['custom_portfolio_value_enabled'].trace('w', lambda *args: self._update_portfolio_value_status())
        self._update_portfolio_value_status()  # Initial update
        
        # Risk limits section
        limits_frame = ttk.LabelFrame(risk_frame, text="Risk Limits", padding=10)
        limits_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self._create_labeled_entry(limits_frame, "Stop Loss (%):", 'stop_loss_percent', row=0)
        self._create_labeled_entry(limits_frame, "Take Profit (%):", 'take_profit_percent', row=1)
        self._create_labeled_entry(limits_frame, "Max Daily Loss ($):", 'max_daily_loss', row=2)
        self._create_labeled_spinbox(limits_frame, "Max Daily Trades:", 'max_daily_trades', 1, 100, row=3)
        self._create_labeled_spinbox(limits_frame, "Max Positions:", 'max_positions', 1, 20, row=4)
        
        # Trading mode section
        mode_frame = ttk.LabelFrame(risk_frame, text="Trading Mode", padding=10)
        mode_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(mode_frame, text="Trading Mode:").pack(anchor=tk.W, pady=2)
        mode_combo_risk = ttk.Combobox(
            mode_frame,
            textvariable=self.config_vars['trading_mode'],
            values=['ultra_safe', 'conservative', 'aggressive'],
            state='readonly',
            width=20
        )
        mode_combo_risk.pack(anchor=tk.W, pady=2)
        
        # Mode descriptions for risk tab
        risk_descriptions = {
            'ultra_safe': 'Ultra-Safe: Minimal risk, very conservative parameters',
            'conservative': 'Conservative: Balanced risk and reward (default)',
            'aggressive': 'Aggressive: Higher risk, more frequent trades'
        }
        
        risk_desc_label = ttk.Label(mode_frame, text=risk_descriptions['conservative'], foreground='gray')
        risk_desc_label.pack(anchor=tk.W, pady=2)
        
        def update_risk_description(event=None):
            selected = self.config_vars['trading_mode'].get()
            risk_desc_label.config(text=risk_descriptions.get(selected, ''))
        
        mode_combo_risk.bind('<<ComboboxSelected>>', update_risk_description)
        self.config_vars['trading_mode'].trace('w', lambda *args: update_risk_description())
    
    def _create_trading_hours_tab(self) -> None:
        """Create trading hours tab."""
        hours_frame = ttk.Frame(self.notebook)
        self.notebook.add(hours_frame, text="Trading Hours")
        
        # Trading hours section
        time_frame = ttk.LabelFrame(hours_frame, text="Active Trading Hours (EST)", padding=10)
        time_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Start time
        start_frame = ttk.Frame(time_frame)
        start_frame.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Label(start_frame, text="Start Time:").pack(side=tk.LEFT, padx=(0, 5))
        
        start_hour_spin = ttk.Spinbox(
            start_frame,
            from_=0, to=23,
            textvariable=self.config_vars['trading_start_hour'],
            width=5
        )
        start_hour_spin.pack(side=tk.LEFT, padx=(0, 2))
        
        ttk.Label(start_frame, text=":").pack(side=tk.LEFT)
        
        start_min_spin = ttk.Spinbox(
            start_frame,
            from_=0, to=59,
            textvariable=self.config_vars['trading_start_minute'],
            width=5
        )
        start_min_spin.pack(side=tk.LEFT, padx=(2, 0))
        
        # End time
        end_frame = ttk.Frame(time_frame)
        end_frame.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Label(end_frame, text="End Time:").pack(side=tk.LEFT, padx=(0, 5))
        
        end_hour_spin = ttk.Spinbox(
            end_frame,
            from_=0, to=23,
            textvariable=self.config_vars['trading_end_hour'],
            width=5
        )
        end_hour_spin.pack(side=tk.LEFT, padx=(0, 2))
        
        ttk.Label(end_frame, text=":").pack(side=tk.LEFT)
        
        end_min_spin = ttk.Spinbox(
            end_frame,
            from_=0, to=59,
            textvariable=self.config_vars['trading_end_minute'],
            width=5
        )
        end_min_spin.pack(side=tk.LEFT, padx=(2, 0))
        
        # Preset buttons
        preset_frame = ttk.LabelFrame(hours_frame, text="Presets", padding=10)
        preset_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(
            preset_frame,
            text="Market Hours (9:30-16:00)",
            command=lambda: self._set_trading_hours(9, 30, 16, 0)
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            preset_frame,
            text="Extended Hours (4:00-20:00)",
            command=lambda: self._set_trading_hours(4, 0, 20, 0)
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            preset_frame,
            text="Opening Hour (9:30-10:30)",
            command=lambda: self._set_trading_hours(9, 30, 10, 30)
        ).pack(side=tk.LEFT, padx=5)
    
    def _create_auto_selection_tab(self) -> None:
        """Create auto-selection tab."""
        auto_frame = ttk.Frame(self.notebook)
        self.notebook.add(auto_frame, text="Auto-Selection")
        
        # Enable auto-selection
        ttk.Checkbutton(
            auto_frame,
            text="Enable Auto-Selection",
            variable=self.config_vars['auto_select_enabled']
        ).pack(anchor=tk.W, padx=5, pady=5)
        
        # Selection criteria
        criteria_frame = ttk.LabelFrame(auto_frame, text="Selection Criteria", padding=10)
        criteria_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self._create_labeled_spinbox(criteria_frame, "Max Symbols:", 'auto_select_max_symbols', 1, 50, row=0)
        self._create_labeled_entry(criteria_frame, "Min Volume:", 'auto_select_min_volume', row=1)
        self._create_labeled_entry(criteria_frame, "Min Price ($):", 'auto_select_min_price', row=2)
        self._create_labeled_entry(criteria_frame, "Max Price ($):", 'auto_select_max_price', row=3)
        self._create_labeled_entry(criteria_frame, "Min Volatility:", 'auto_select_min_volatility', row=4)
    
    def _create_data_tab(self) -> None:
        """Create data and display tab."""
        data_frame = ttk.Frame(self.notebook)
        self.notebook.add(data_frame, text="Data & Display")
        
        # Data settings
        data_settings_frame = ttk.LabelFrame(data_frame, text="Data Settings", padding=10)
        data_settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self._create_labeled_spinbox(data_settings_frame, "Update Interval (sec):", 'data_update_interval', 1, 60, row=0)
        
        # Chart timeframe
        ttk.Label(data_settings_frame, text="Chart Timeframe:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        timeframe_combo = ttk.Combobox(
            data_settings_frame,
            textvariable=self.config_vars['chart_timeframe'],
            values=['1Min', '5Min', '15Min', '1Hour', '1Day'],
            state="readonly",
            width=20
        )
        timeframe_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        self._create_labeled_spinbox(data_settings_frame, "Max Bars History:", 'max_bars_history', 100, 10000, row=2)
    
    def _create_logging_tab(self) -> None:
        """Create logging configuration tab."""
        log_frame = ttk.Frame(self.notebook)
        self.notebook.add(log_frame, text="Logging")
        
        # Logging settings
        log_settings_frame = ttk.LabelFrame(log_frame, text="Logging Settings", padding=10)
        log_settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Log level
        ttk.Label(log_settings_frame, text="Log Level:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        level_combo = ttk.Combobox(
            log_settings_frame,
            textvariable=self.config_vars['log_level'],
            values=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            state="readonly",
            width=20
        )
        level_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Log to file
        ttk.Checkbutton(
            log_settings_frame,
            text="Log to File",
            variable=self.config_vars['log_to_file']
        ).grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        
        self._create_labeled_spinbox(log_settings_frame, "Max Log Files:", 'max_log_files', 1, 50, row=2)
    
    def _create_control_buttons(self) -> None:
        """Create control buttons."""
        button_frame = ttk.Frame(self.frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Save button
        ttk.Button(
            button_frame,
            text="Save Settings",
            command=self._save_settings
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        # Load button
        ttk.Button(
            button_frame,
            text="Load Settings",
            command=self._load_settings_from_file
        ).pack(side=tk.LEFT, padx=5)
        
        # Reset button
        ttk.Button(
            button_frame,
            text="Reset to Defaults",
            command=self._reset_to_defaults
        ).pack(side=tk.LEFT, padx=5)
        
        # Export button
        ttk.Button(
            button_frame,
            text="Export Config",
            command=self._export_config
        ).pack(side=tk.LEFT, padx=5)
        
        # Import button
        ttk.Button(
            button_frame,
            text="Import Config",
            command=self._import_config
        ).pack(side=tk.LEFT, padx=5)
    
    def _create_labeled_entry(self, parent: tk.Widget, label: str, var_name: str, row: int) -> None:
        """Create a labeled entry widget.
        
        Args:
            parent: Parent widget.
            label: Label text.
            var_name: Variable name.
            row: Grid row.
        """
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        
        entry = ttk.Entry(
            parent,
            textvariable=self.config_vars[var_name],
            width=20
        )
        entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
    
    def _create_labeled_spinbox(self, parent: tk.Widget, label: str, var_name: str, 
                               from_: int, to: int, row: int) -> None:
        """Create a labeled spinbox widget.
        
        Args:
            parent: Parent widget.
            label: Label text.
            var_name: Variable name.
            from_: Minimum value.
            to: Maximum value.
            row: Grid row.
        """
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        
        spinbox = ttk.Spinbox(
            parent,
            from_=from_, to=to,
            textvariable=self.config_vars[var_name],
            width=20
        )
        spinbox.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
    
    def _set_trading_hours(self, start_hour: int, start_min: int, end_hour: int, end_min: int) -> None:
        """Set trading hours preset.
        
        Args:
            start_hour: Start hour.
            start_min: Start minute.
            end_hour: End hour.
            end_min: End minute.
        """
        self.config_vars['trading_start_hour'].set(start_hour)
        self.config_vars['trading_start_minute'].set(start_min)
        self.config_vars['trading_end_hour'].set(end_hour)
        self.config_vars['trading_end_minute'].set(end_min)
    
    def _validate_fixed_trade_amount(self, *args) -> bool:
        """Validate the fixed trade amount.
        
        Returns:
            True if valid, False otherwise.
        """
        try:
            amount = self.config_vars['fixed_trade_amount'].get()
            min_amount = getattr(self.settings, 'min_trade_amount', 1.0)
            max_amount = getattr(self.settings, 'max_trade_amount', 10000.0)
            
            # Only validate on save, not during typing
            # Allow any value >= $1.0 without showing error alerts
            if amount >= min_amount and amount <= max_amount:
                return True
            
            return True  # Allow typing without interruption
            
        except (ValueError, tk.TclError):
            # Don't show error during typing, only return False
            return False
    
    def _validate_custom_portfolio_value(self, *args) -> bool:
        """Validate the custom portfolio value.
        
        Returns:
            True if valid, False otherwise.
        """
        try:
            value = self.config_vars['custom_portfolio_value'].get()
            min_value = getattr(self.settings, 'min_portfolio_value', 1.0)
            max_value = getattr(self.settings, 'max_portfolio_value', 1000000.0)
            
            # Only validate on save, not during typing
            # Allow any value >= $1.0 without showing error alerts
            if value >= min_value and value <= max_value:
                return True
            
            return True  # Allow typing without interruption
            
        except (ValueError, tk.TclError):
            # Don't show error during typing, only return False
            return False
    
    def _update_fixed_amount_status(self) -> None:
        """Update visual indicators when fixed amount feature is toggled."""
        is_enabled = self.config_vars['fixed_trade_amount_enabled'].get()
        
        if is_enabled:
            # Update frame title to show active state
            if hasattr(self, 'fixed_amount_frame'):
                self.fixed_amount_frame.config(text="Fixed Trade Amount - ACTIVE")
            
            # Update status indicator to show active state
            self.fixed_amount_status.config(
                text="ACTIVE",
                foreground="green",
                font=('TkDefaultFont', 9, 'bold')
            )
            
            # Highlight the entry field
            if hasattr(self, 'fixed_amount_entry'):
                self.fixed_amount_entry.config(style='Active.TEntry')
            
            # Disable position sizing method combobox when fixed amount is active
            if hasattr(self, 'position_method_combo'):
                self.position_method_combo.config(state='disabled')
            
            # Show current fixed amount in status
            try:
                amount = self.config_vars['fixed_trade_amount'].get()
                if amount > 0:
                    self.fixed_amount_status.config(text=f"ACTIVE (${amount:.2f})")
            except (ValueError, tk.TclError):
                pass
                
            self.logger.info("Fixed trade amount feature activated")
        else:
            # Update frame title to show inactive state
            if hasattr(self, 'fixed_amount_frame'):
                self.fixed_amount_frame.config(text="Fixed Trade Amount")
            
            # Update status indicator to show inactive state
            self.fixed_amount_status.config(
                text="Inactive",
                foreground="gray",
                font=('TkDefaultFont', 9, 'normal')
            )
            
            # Reset entry field styling
            if hasattr(self, 'fixed_amount_entry'):
                self.fixed_amount_entry.config(style='TEntry')
            
            # Re-enable position sizing method combobox
            if hasattr(self, 'position_method_combo'):
                self.position_method_combo.config(state='readonly')
                
            self.logger.info("Fixed trade amount feature deactivated")
        
        # Notify of settings change without saving
        if self.on_settings_change:
            config_dict = self._get_current_config()
            self.on_settings_change(config_dict)
    
    def _update_portfolio_value_status(self) -> None:
        """Update visual indicators when custom portfolio value feature is toggled."""
        is_enabled = self.config_vars['custom_portfolio_value_enabled'].get()
        
        if is_enabled:
            # Update frame title to show active state
            if hasattr(self, 'portfolio_value_frame'):
                self.portfolio_value_frame.config(text="Custom Portfolio Value - ACTIVE")
            
            # Update status indicator to show active state
            self.portfolio_value_status.config(
                text="ACTIVE",
                foreground="green",
                font=('TkDefaultFont', 9, 'bold')
            )
            
            # Highlight the entry field
            if hasattr(self, 'portfolio_value_entry'):
                self.portfolio_value_entry.config(style='Active.TEntry')
            
            # Show current portfolio value in status
            try:
                value = self.config_vars['custom_portfolio_value'].get()
                if value > 0:
                    self.portfolio_value_status.config(text=f"ACTIVE (${value:,.2f})")
            except (ValueError, tk.TclError):
                pass
                
            self.logger.info("Custom portfolio value feature activated")
        else:
            # Update frame title to show inactive state
            if hasattr(self, 'portfolio_value_frame'):
                self.portfolio_value_frame.config(text="Custom Portfolio Value")
            
            # Update status indicator to show inactive state
            self.portfolio_value_status.config(
                text="Using Real Portfolio Value",
                foreground="gray",
                font=('TkDefaultFont', 9, 'normal')
            )
            
            # Reset entry field styling
            if hasattr(self, 'portfolio_value_entry'):
                self.portfolio_value_entry.config(style='TEntry')
                
            self.logger.info("Custom portfolio value feature deactivated")
        
        # Notify of settings change without saving
        if self.on_settings_change:
            config_dict = self._get_current_config()
            self.on_settings_change(config_dict)
     
    def _load_settings(self) -> None:
        """Load settings from the settings instance."""
        try:
            # Map settings to config variables
            settings_mapping = {
                # Strategy parameters
                'support_resistance_lookback': 'SUPPORT_RESISTANCE_LOOKBACK',
                'support_resistance_min_touches': 'SUPPORT_RESISTANCE_MIN_TOUCHES',
                'support_resistance_tolerance': 'SUPPORT_RESISTANCE_TOLERANCE',
                'rsi_period': 'RSI_PERIOD',
                'rsi_oversold': 'RSI_OVERSOLD',
                'rsi_overbought': 'RSI_OVERBOUGHT',
                'bb_period': 'BB_PERIOD',
                'bb_std_dev': 'BB_STD_DEV',
                'macd_fast': 'MACD_FAST',
                'macd_slow': 'MACD_SLOW',
                'macd_signal': 'MACD_SIGNAL',
                
                # Position sizing
                'position_size_method': 'POSITION_SIZE_METHOD',
                'fixed_position_amount': 'FIXED_POSITION_AMOUNT',
                'position_size_percent': 'POSITION_SIZE_PERCENT',
                'max_position_size': 'MAX_POSITION_SIZE',
                
                # Fixed Trade Amount Feature
                'fixed_trade_amount_enabled': 'fixed_trade_amount_enabled',
                'fixed_trade_amount': 'fixed_trade_amount',
                
                # Custom Portfolio Value Feature
                'custom_portfolio_value_enabled': 'custom_portfolio_value_enabled',
                'custom_portfolio_value': 'custom_portfolio_value',
                
                # Risk management
                'stop_loss_percent': 'STOP_LOSS_PERCENT',
                'take_profit_percent': 'TAKE_PROFIT_PERCENT',
                'max_daily_loss': 'MAX_DAILY_LOSS',
                'max_daily_trades': 'MAX_DAILY_TRADES',
                'max_positions': 'MAX_POSITIONS',
                
                # Trading hours
                'trading_start_hour': 'TRADING_START_HOUR',
                'trading_start_minute': 'TRADING_START_MINUTE',
                'trading_end_hour': 'TRADING_END_HOUR',
                'trading_end_minute': 'TRADING_END_MINUTE',
                
                # Data settings
                'data_update_interval': 'DATA_UPDATE_INTERVAL',
                'chart_timeframe': 'CHART_TIMEFRAME',
                'max_bars_history': 'MAX_BARS_HISTORY',
                
                # Auto-selection
                'auto_select_enabled': 'AUTO_SELECT_ENABLED',
                'auto_select_max_symbols': 'AUTO_SELECT_MAX_SYMBOLS',
                'auto_select_min_volume': 'AUTO_SELECT_MIN_VOLUME',
                'auto_select_min_price': 'AUTO_SELECT_MIN_PRICE',
                'auto_select_max_price': 'AUTO_SELECT_MAX_PRICE',
                'auto_select_min_volatility': 'AUTO_SELECT_MIN_VOLATILITY',
                
                # Logging
                'log_level': 'LOG_LEVEL',
                'log_to_file': 'LOG_TO_FILE',
                'max_log_files': 'MAX_LOG_FILES',
                
                # Trading mode
                'trading_mode': 'trading_mode',
            }
            
            # Load values from settings
            for var_name, setting_name in settings_mapping.items():
                if hasattr(self.settings, setting_name):
                    value = getattr(self.settings, setting_name)
                    if var_name in self.config_vars:
                        self.config_vars[var_name].set(value)
            
            self.logger.info("Settings loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}")
            messagebox.showerror("Error", f"Failed to load settings: {e}")
    
    def _save_settings(self) -> None:
        """Save current configuration to settings."""
        try:
            # Update settings from config variables
            settings_mapping = {
                # Strategy parameters
                'SUPPORT_RESISTANCE_LOOKBACK': 'support_resistance_lookback',
                'SUPPORT_RESISTANCE_MIN_TOUCHES': 'support_resistance_min_touches',
                'SUPPORT_RESISTANCE_TOLERANCE': 'support_resistance_tolerance',
                'RSI_PERIOD': 'rsi_period',
                'RSI_OVERSOLD': 'rsi_oversold',
                'RSI_OVERBOUGHT': 'rsi_overbought',
                'BB_PERIOD': 'bb_period',
                'BB_STD_DEV': 'bb_std_dev',
                'MACD_FAST': 'macd_fast',
                'MACD_SLOW': 'macd_slow',
                'MACD_SIGNAL': 'macd_signal',
                
                # Position sizing
                'POSITION_SIZE_METHOD': 'position_size_method',
                'FIXED_POSITION_AMOUNT': 'fixed_position_amount',
                'POSITION_SIZE_PERCENT': 'position_size_percent',
                'MAX_POSITION_SIZE': 'max_position_size',
                
                # Fixed Trade Amount Feature
                'fixed_trade_amount_enabled': 'fixed_trade_amount_enabled',
                'fixed_trade_amount': 'fixed_trade_amount',
                
                # Risk management
                'STOP_LOSS_PERCENT': 'stop_loss_percent',
                'TAKE_PROFIT_PERCENT': 'take_profit_percent',
                'MAX_DAILY_LOSS': 'max_daily_loss',
                'MAX_DAILY_TRADES': 'max_daily_trades',
                'MAX_POSITIONS': 'max_positions',
                
                # Trading hours
                'TRADING_START_HOUR': 'trading_start_hour',
                'TRADING_START_MINUTE': 'trading_start_minute',
                'TRADING_END_HOUR': 'trading_end_hour',
                'TRADING_END_MINUTE': 'trading_end_minute',
                
                # Data settings
                'DATA_UPDATE_INTERVAL': 'data_update_interval',
                'CHART_TIMEFRAME': 'chart_timeframe',
                'MAX_BARS_HISTORY': 'max_bars_history',
                
                # Auto-selection
                'AUTO_SELECT_ENABLED': 'auto_select_enabled',
                'AUTO_SELECT_MAX_SYMBOLS': 'auto_select_max_symbols',
                'AUTO_SELECT_MIN_VOLUME': 'auto_select_min_volume',
                'AUTO_SELECT_MIN_PRICE': 'auto_select_min_price',
                'AUTO_SELECT_MAX_PRICE': 'auto_select_max_price',
                'AUTO_SELECT_MIN_VOLATILITY': 'auto_select_min_volatility',
                
                # Logging
                'LOG_LEVEL': 'log_level',
                'LOG_TO_FILE': 'log_to_file',
                'MAX_LOG_FILES': 'max_log_files',
                
                # Trading mode
                'trading_mode': 'trading_mode',
            }
            
            # Update settings
            for setting_name, var_name in settings_mapping.items():
                if var_name in self.config_vars:
                    value = self.config_vars[var_name].get()
                    setattr(self.settings, setting_name, value)
            
            # Notify of settings change
            if self.on_settings_change:
                config_dict = self._get_current_config()
                self.on_settings_change(config_dict)
            
            # Save settings to .env file for persistence
            if self.settings.save_to_env_file():
                messagebox.showinfo("Success", "Settings saved successfully and persisted to .env file!")
                self.logger.info("Settings saved successfully and persisted to .env file")
            else:
                messagebox.showwarning("Partial Success", "Settings saved to memory but failed to persist to .env file.")
                self.logger.warning("Settings saved to memory but failed to persist to .env file")
            
        except Exception as e:
            self.logger.error(f"Error saving settings: {e}")
            messagebox.showerror("Error", f"Failed to save settings: {e}")
    
    def _load_settings_from_file(self) -> None:
        """Load settings from file."""
        try:
            # This would reload from .env or config file
            self.settings.reload()
            self._load_settings()
            messagebox.showinfo("Success", "Settings reloaded from file!")
            
        except Exception as e:
            self.logger.error(f"Error reloading settings: {e}")
            messagebox.showerror("Error", f"Failed to reload settings: {e}")
    
    def _get_current_config(self) -> Dict:
        """Get current configuration as a dictionary.
        
        Returns:
            Dictionary containing current configuration values.
        """
        config = {}
        try:
            # Get all current values from config variables
            for var_name, var in self.config_vars.items():
                config[var_name] = var.get()
            
            self.logger.debug(f"Current config retrieved: {len(config)} settings")
            return config
            
        except Exception as e:
            self.logger.error(f"Error getting current config: {e}")
            return {}
    
    def _reset_to_defaults(self) -> None:
        """Reset all settings to defaults."""
        try:
            result = messagebox.askyesno(
                "Confirm Reset",
                "Are you sure you want to reset all settings to defaults? This cannot be undone."
            )
            
            if result:
                # Reset all config variables to their default values
                self._create_config_vars()
                messagebox.showinfo("Success", "Settings reset to defaults!")
                self.logger.info("Settings reset to defaults")
            
        except Exception as e:
            self.logger.error(f"Error resetting settings: {e}")
            messagebox.showerror("Error", f"Failed to reset settings: {e}")
    
    def _export_config(self) -> None:
        """Export configuration to JSON file."""
        try:
            filename = filedialog.asksaveasfilename(
                title="Export Configuration",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                config_data = {}
                for var_name, var in self.config_vars.items():
                    config_data[var_name] = var.get()
                
                with open(filename, 'w') as f:
                    json.dump(config_data, f, indent=2)
                
                messagebox.showinfo("Success", f"Configuration exported to {filename}")
                self.logger.info(f"Configuration exported to {filename}")
            
        except Exception as e:
            self.logger.error(f"Error exporting configuration: {e}")
            messagebox.showerror("Error", f"Failed to export configuration: {e}")
    
    def _import_config(self) -> None:
        """Import configuration from JSON file."""
        try:
            filename = filedialog.askopenfilename(
                title="Import Configuration",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                with open(filename, 'r') as f:
                    config_data = json.load(f)
                
                # Update config variables
                for var_name, value in config_data.items():
                    if var_name in self.config_vars:
                        self.config_vars[var_name].set(value)
                
                messagebox.showinfo("Success", f"Configuration imported from {filename}")
                self.logger.info(f"Configuration imported from {filename}")
            
        except Exception as e:
            self.logger.error(f"Error importing configuration: {e}")
            messagebox.showerror("Error", f"Failed to import configuration: {e}")
    
    def get_config_dict(self) -> Dict[str, Any]:
        """Get current configuration as dictionary.
        
        Returns:
            Configuration dictionary.
        """
        config = {}
        for var_name, var in self.config_vars.items():
            config[var_name] = var.get()
        return config
    
    def set_config_dict(self, config: Dict[str, Any]) -> None:
        """Set configuration from dictionary.
        
        Args:
            config: Configuration dictionary.
        """
        for var_name, value in config.items():
            if var_name in self.config_vars:
                self.config_vars[var_name].set(value)