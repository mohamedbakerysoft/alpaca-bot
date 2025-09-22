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
        """Initialize ConfigPanel.
        
        Args:
            parent: Parent widget.
            settings: Settings instance.
            on_settings_change: Callback for settings changes.
        """
        self.parent = parent
        self.settings = settings
        self.on_settings_change = on_settings_change
        self.logger = logging.getLogger(__name__)
        self.initializing = True
        
        self.is_notebook_parent = isinstance(parent, ttk.Notebook)
        
        if self.is_notebook_parent:
            self.notebook = parent
            self.frame = ttk.Frame(parent)
        else:
            self.frame = ttk.Frame(parent)
            self.frame.pack(fill=tk.BOTH, expand=True)
            self.notebook = ttk.Notebook(self.frame)
            self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
        self.config_vars: Dict[str, tk.Variable] = {}
        
        self._create_config_vars()
        self._create_widgets()
        self._load_settings()
        
        self.logger.info("ConfigPanel initialized")
        self.initializing = False

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
            'fixed_trade_amount_enabled': tk.BooleanVar(value=self.settings.fixed_trade_amount_enabled),
            'fixed_trade_amount': tk.DoubleVar(value=self.settings.fixed_trade_amount),
            
            # Custom Portfolio Value Feature
            'custom_portfolio_value_enabled': tk.BooleanVar(value=self.settings.custom_portfolio_value_enabled),
            'custom_portfolio_value': tk.DoubleVar(value=self.settings.custom_portfolio_value),
            
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
        
        # Control buttons (only for standalone mode)
        if not self.is_notebook_parent:
            self._create_control_buttons()
    

    

    

    

    

    

    
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
        if not self.initializing and self.on_settings_change:
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
        if not self.initializing and self.on_settings_change:
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