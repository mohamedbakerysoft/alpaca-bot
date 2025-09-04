"""Stock selector component for the Alpaca trading bot.

This module provides:
- Manual stock selection via dropdown
- Auto-selection of optimal stocks for scalping
- Popular stock presets
- Custom symbol input
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Callable, Optional, Dict, Any
import threading
import pandas as pd

from ..services.alpaca_client import AlpacaClient
from ..utils.logging_utils import get_logger
from ..utils.technical_analysis import calculate_volatility


class StockSelectorFrame:
    """Stock selector frame component."""
    
    # Popular stocks for scalping
    POPULAR_STOCKS = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA',
        'NVDA', 'META', 'NFLX', 'AMD', 'INTC',
        'SPY', 'QQQ', 'IWM', 'DIA', 'VTI'
    ]
    
    def __init__(self, parent: tk.Widget, callback: Callable[[List[str]], None]):
        """Initialize the stock selector.
        
        Args:
            parent: Parent widget.
            callback: Callback function for symbol changes.
        """
        self.logger = get_logger(__name__)
        self.callback = callback
        self.selected_symbols: List[str] = []
        self.alpaca_client: Optional[AlpacaClient] = None
        
        # Create main frame
        self.frame = ttk.LabelFrame(parent, text="Stock Selection", padding=10)
        self.frame.pack(fill=tk.X, padx=5, pady=5)
        
        self._create_widgets()
        
        # Initialize with Alpaca client if available
        try:
            self.alpaca_client = AlpacaClient()
        except Exception as e:
            self.logger.warning(f"Could not initialize Alpaca client: {e}")
    
    def _create_widgets(self) -> None:
        """Create the selector widgets."""
        # Selection mode
        mode_frame = ttk.Frame(self.frame)
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(mode_frame, text="Selection Mode:").pack(side=tk.LEFT)
        
        self.mode_var = tk.StringVar(value="manual")
        
        manual_radio = ttk.Radiobutton(
            mode_frame,
            text="Manual",
            variable=self.mode_var,
            value="manual",
            command=self._on_mode_changed
        )
        manual_radio.pack(side=tk.LEFT, padx=(10, 5))
        
        auto_radio = ttk.Radiobutton(
            mode_frame,
            text="Auto-Select",
            variable=self.mode_var,
            value="auto",
            command=self._on_mode_changed
        )
        auto_radio.pack(side=tk.LEFT, padx=5)
        
        # Manual selection frame
        self.manual_frame = ttk.Frame(self.frame)
        self.manual_frame.pack(fill=tk.X, pady=(0, 10))
        
        self._create_manual_selection()
        
        # Auto selection frame
        self.auto_frame = ttk.Frame(self.frame)
        self.auto_frame.pack(fill=tk.X, pady=(0, 10))
        
        self._create_auto_selection()
        
        # Selected symbols display
        self._create_symbols_display()
        
        # Set popular stocks as selected by default after all widgets are created
        self._update_manual_selection()
        
        # Initially show manual mode
        self._on_mode_changed()
    
    def _create_manual_selection(self) -> None:
        """Create manual selection widgets."""
        # Popular stocks section
        popular_frame = ttk.LabelFrame(self.manual_frame, text="Popular Stocks", padding=5)
        popular_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create checkboxes for popular stocks
        self.popular_vars: Dict[str, tk.BooleanVar] = {}
        
        # Arrange in rows of 5
        for i, symbol in enumerate(self.POPULAR_STOCKS):
            row = i // 5
            col = i % 5
            
            # Set popular stocks as selected by default
            var = tk.BooleanVar(value=True)
            self.popular_vars[symbol] = var
            
            cb = ttk.Checkbutton(
                popular_frame,
                text=symbol,
                variable=var,
                command=self._update_manual_selection
            )
            cb.grid(row=row, column=col, sticky=tk.W, padx=5, pady=2)
        
        # Custom symbol input
        custom_frame = ttk.LabelFrame(self.manual_frame, text="Custom Symbol", padding=5)
        custom_frame.pack(fill=tk.X, pady=(0, 10))
        
        input_frame = ttk.Frame(custom_frame)
        input_frame.pack(fill=tk.X)
        
        ttk.Label(input_frame, text="Symbol:").pack(side=tk.LEFT)
        
        self.custom_entry = ttk.Entry(input_frame, width=10)
        self.custom_entry.pack(side=tk.LEFT, padx=(5, 5))
        self.custom_entry.bind('<Return>', self._add_custom_symbol)
        
        ttk.Button(
            input_frame,
            text="Add",
            command=self._add_custom_symbol
        ).pack(side=tk.LEFT)
        
        # Preset buttons
        preset_frame = ttk.LabelFrame(self.manual_frame, text="Presets", padding=5)
        preset_frame.pack(fill=tk.X)
        
        presets = [
            ("Tech Giants", ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']),
            ("ETFs", ['SPY', 'QQQ', 'IWM', 'DIA', 'VTI']),
            ("High Volume", ['TSLA', 'NVDA', 'AMD', 'NFLX', 'INTC']),
            ("Clear All", [])
        ]
        
        for i, (name, symbols) in enumerate(presets):
            ttk.Button(
                preset_frame,
                text=name,
                command=lambda s=symbols: self._apply_preset(s)
            ).grid(row=0, column=i, padx=5, pady=2, sticky=tk.EW)
        
        # Configure grid weights
        for i in range(len(presets)):
            preset_frame.columnconfigure(i, weight=1)
    
    def _create_auto_selection(self) -> None:
        """Create auto selection widgets."""
        # Auto selection parameters
        params_frame = ttk.LabelFrame(self.auto_frame, text="Selection Criteria", padding=5)
        params_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Max symbols
        max_frame = ttk.Frame(params_frame)
        max_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(max_frame, text="Max Symbols:").pack(side=tk.LEFT)
        
        self.max_symbols_var = tk.IntVar(value=5)
        max_spinbox = ttk.Spinbox(
            max_frame,
            from_=1,
            to=20,
            width=5,
            textvariable=self.max_symbols_var
        )
        max_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        
        # Min volume
        volume_frame = ttk.Frame(params_frame)
        volume_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(volume_frame, text="Min Volume (M):").pack(side=tk.LEFT)
        
        self.min_volume_var = tk.DoubleVar(value=1.0)
        volume_spinbox = ttk.Spinbox(
            volume_frame,
            from_=0.1,
            to=100.0,
            increment=0.1,
            width=8,
            textvariable=self.min_volume_var
        )
        volume_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        
        # Price range
        price_frame = ttk.Frame(params_frame)
        price_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(price_frame, text="Price Range:").pack(side=tk.LEFT)
        
        self.min_price_var = tk.DoubleVar(value=10.0)
        min_price_spinbox = ttk.Spinbox(
            price_frame,
            from_=1.0,
            to=1000.0,
            increment=1.0,
            width=8,
            textvariable=self.min_price_var
        )
        min_price_spinbox.pack(side=tk.LEFT, padx=(5, 5))
        
        ttk.Label(price_frame, text="to").pack(side=tk.LEFT)
        
        self.max_price_var = tk.DoubleVar(value=500.0)
        max_price_spinbox = ttk.Spinbox(
            price_frame,
            from_=1.0,
            to=10000.0,
            increment=1.0,
            width=8,
            textvariable=self.max_price_var
        )
        max_price_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        
        # Volatility filter
        volatility_frame = ttk.Frame(params_frame)
        volatility_frame.pack(fill=tk.X, pady=2)
        
        self.volatility_filter_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            volatility_frame,
            text="Filter by volatility (good for scalping)",
            variable=self.volatility_filter_var
        ).pack(side=tk.LEFT)
        
        # Auto select button
        button_frame = ttk.Frame(self.auto_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.auto_select_btn = ttk.Button(
            button_frame,
            text="Auto-Select Stocks",
            command=self._auto_select_stocks
        )
        self.auto_select_btn.pack(side=tk.LEFT)
        
        self.auto_status = ttk.Label(button_frame, text="")
        self.auto_status.pack(side=tk.LEFT, padx=(10, 0))
    
    def _create_symbols_display(self) -> None:
        """Create selected symbols display."""
        display_frame = ttk.LabelFrame(self.frame, text="Selected Symbols", padding=5)
        display_frame.pack(fill=tk.X)
        
        # Symbols listbox
        list_frame = ttk.Frame(display_frame)
        list_frame.pack(fill=tk.X)
        
        self.symbols_listbox = tk.Listbox(list_frame, height=4)
        self.symbols_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.symbols_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.symbols_listbox.yview)
        
        # Remove button
        button_frame = ttk.Frame(display_frame)
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(
            button_frame,
            text="Remove Selected",
            command=self._remove_selected_symbol
        ).pack(side=tk.LEFT)
        
        ttk.Button(
            button_frame,
            text="Clear All",
            command=self._clear_all_symbols
        ).pack(side=tk.LEFT, padx=(5, 0))
        
        # Symbol count
        self.count_label = ttk.Label(button_frame, text="0 symbols selected")
        self.count_label.pack(side=tk.RIGHT)
    
    def _on_mode_changed(self) -> None:
        """Handle selection mode change."""
        mode = self.mode_var.get()
        
        if mode == "manual":
            self.manual_frame.pack(fill=tk.X, pady=(0, 10))
            self.auto_frame.pack_forget()
        else:
            self.auto_frame.pack(fill=tk.X, pady=(0, 10))
            self.manual_frame.pack_forget()
    
    def _update_manual_selection(self) -> None:
        """Update selection based on manual checkboxes."""
        selected = []
        
        for symbol, var in self.popular_vars.items():
            if var.get():
                selected.append(symbol)
        
        # Add any existing custom symbols
        for symbol in self.selected_symbols:
            if symbol not in self.POPULAR_STOCKS and symbol not in selected:
                selected.append(symbol)
        
        self._update_selected_symbols(selected)
    
    def _add_custom_symbol(self, event=None) -> None:
        """Add a custom symbol.
        
        Args:
            event: Optional event object.
        """
        symbol = self.custom_entry.get().strip().upper()
        
        if not symbol:
            return
        
        if len(symbol) > 10:
            messagebox.showerror("Error", "Symbol too long (max 10 characters)")
            return
        
        if symbol in self.selected_symbols:
            messagebox.showwarning("Warning", f"Symbol {symbol} already selected")
            return
        
        # Validate symbol if Alpaca client is available
        if self.alpaca_client:
            try:
                assets = self.alpaca_client.get_tradable_assets()
                if assets:
                    valid_symbols = [asset.symbol for asset in assets]
                    if symbol not in valid_symbols:
                        if not messagebox.askyesno(
                            "Warning",
                            f"Symbol {symbol} may not be tradable. Add anyway?"
                        ):
                            return
            except Exception as e:
                self.logger.warning(f"Could not validate symbol {symbol}: {e}")
        
        # Add symbol
        new_symbols = self.selected_symbols + [symbol]
        self._update_selected_symbols(new_symbols)
        
        # Clear entry
        self.custom_entry.delete(0, tk.END)
    
    def _apply_preset(self, symbols: List[str]) -> None:
        """Apply a preset selection.
        
        Args:
            symbols: List of symbols to select.
        """
        # Clear current selection
        for var in self.popular_vars.values():
            var.set(False)
        
        # Set new selection
        for symbol in symbols:
            if symbol in self.popular_vars:
                self.popular_vars[symbol].set(True)
        
        self._update_manual_selection()
    
    def _auto_select_stocks(self) -> None:
        """Auto-select stocks based on criteria."""
        if not self.alpaca_client:
            messagebox.showerror(
                "Error",
                "Alpaca client not available for auto-selection"
            )
            return
        
        # Disable button and show status
        self.auto_select_btn.config(state='disabled')
        self.auto_status.config(text="Analyzing stocks...")
        
        # Run in thread to avoid blocking UI
        thread = threading.Thread(
            target=self._auto_select_worker,
            daemon=True
        )
        thread.start()
    
    def _auto_select_worker(self) -> None:
        """Worker thread for auto-selection."""
        try:
            # Get selection criteria
            max_symbols = self.max_symbols_var.get()
            min_volume = self.min_volume_var.get() * 1_000_000  # Convert to actual volume
            min_price = self.min_price_var.get()
            max_price = self.max_price_var.get()
            use_volatility = self.volatility_filter_var.get()
            
            # Get tradable assets
            assets = self.alpaca_client.get_tradable_assets()
            if not assets:
                raise Exception("Could not get tradable assets")
            
            # Filter by basic criteria
            candidates = []
            
            for asset in assets:
                if not asset.tradable or not asset.shortable:
                    continue
                
                symbol = asset.symbol
                
                try:
                    # Get latest quote
                    quote = self.alpaca_client.get_latest_quote(symbol)
                    if not quote:
                        continue
                    
                    price = quote.bid
                    if price < min_price or price > max_price:
                        continue
                    
                    # Get recent bars for volume check
                    bars = self.alpaca_client.get_bars(
                        symbol,
                        timeframe='1Day',
                        limit=5
                    )
                    
                    if not bars:
                        continue
                    
                    # Check average volume
                    avg_volume = sum(bar.volume for bar in bars) / len(bars)
                    if avg_volume < min_volume:
                        continue
                    
                    # Calculate volatility if requested
                    volatility_score = 0
                    if use_volatility:
                        try:
                            # Get more bars for volatility calculation
                            vol_bars = self.alpaca_client.get_bars(
                                symbol,
                                timeframe='1Hour',
                                limit=50
                            )
                            
                            if vol_bars and len(vol_bars) >= 20:
                                closes = [bar.close for bar in vol_bars]
                                vol_df = pd.DataFrame({'close': closes})
                                volatility_score = calculate_volatility(vol_df)
                            
                        except Exception as e:
                            self.logger.debug(f"Could not calculate volatility for {symbol}: {e}")
                    
                    candidates.append({
                        'symbol': symbol,
                        'price': price,
                        'volume': avg_volume,
                        'volatility': volatility_score
                    })
                    
                    # Update status
                    self.frame.after(0, lambda: self.auto_status.config(
                        text=f"Analyzed {len(candidates)} candidates..."
                    ))
                    
                except Exception as e:
                    self.logger.debug(f"Error analyzing {symbol}: {e}")
                    continue
            
            # Sort candidates
            if use_volatility:
                # Sort by volatility (higher is better for scalping)
                candidates.sort(key=lambda x: x['volatility'], reverse=True)
            else:
                # Sort by volume (higher is better)
                candidates.sort(key=lambda x: x['volume'], reverse=True)
            
            # Select top candidates
            selected_symbols = [c['symbol'] for c in candidates[:max_symbols]]
            
            # Update UI in main thread
            self.frame.after(0, lambda: self._auto_select_complete(selected_symbols))
            
        except Exception as e:
            self.logger.error(f"Error in auto-selection: {e}")
            self.frame.after(0, lambda: self._auto_select_error(str(e)))
    
    def _auto_select_complete(self, symbols: List[str]) -> None:
        """Complete auto-selection.
        
        Args:
            symbols: Selected symbols.
        """
        self._update_selected_symbols(symbols)
        
        self.auto_select_btn.config(state='normal')
        self.auto_status.config(text=f"Selected {len(symbols)} stocks")
        
        if symbols:
            messagebox.showinfo(
                "Auto-Selection Complete",
                f"Selected {len(symbols)} stocks:\n{', '.join(symbols)}"
            )
        else:
            messagebox.showwarning(
                "No Stocks Found",
                "No stocks met the specified criteria. Try adjusting the parameters."
            )
    
    def _auto_select_error(self, error: str) -> None:
        """Handle auto-selection error.
        
        Args:
            error: Error message.
        """
        self.auto_select_btn.config(state='normal')
        self.auto_status.config(text="Error occurred")
        
        messagebox.showerror(
            "Auto-Selection Error",
            f"Error during auto-selection: {error}"
        )
    
    def _update_selected_symbols(self, symbols: List[str]) -> None:
        """Update the selected symbols list.
        
        Args:
            symbols: New list of selected symbols.
        """
        self.selected_symbols = symbols
        
        # Update listbox
        self.symbols_listbox.delete(0, tk.END)
        for symbol in symbols:
            self.symbols_listbox.insert(tk.END, symbol)
        
        # Update count
        count = len(symbols)
        self.count_label.config(text=f"{count} symbol{'s' if count != 1 else ''} selected")
        
        # Call callback
        self.callback(symbols)
        
        self.logger.info(f"Selected symbols updated: {symbols}")
    
    def _remove_selected_symbol(self) -> None:
        """Remove the selected symbol from the list."""
        selection = self.symbols_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "No symbol selected to remove")
            return
        
        index = selection[0]
        symbol = self.selected_symbols[index]
        
        # Remove from list
        new_symbols = [s for i, s in enumerate(self.selected_symbols) if i != index]
        
        # Uncheck if it's a popular stock
        if symbol in self.popular_vars:
            self.popular_vars[symbol].set(False)
        
        self._update_selected_symbols(new_symbols)
    
    def _clear_all_symbols(self) -> None:
        """Clear all selected symbols."""
        if not self.selected_symbols:
            return
        
        if messagebox.askyesno("Confirm", "Clear all selected symbols?"):
            # Uncheck all popular stocks
            for var in self.popular_vars.values():
                var.set(False)
            
            self._update_selected_symbols([])
    
    def get_selected_symbols(self) -> List[str]:
        """Get the currently selected symbols.
        
        Returns:
            List of selected symbols.
        """
        return self.selected_symbols.copy()
    
    def set_selected_symbols(self, symbols: List[str]) -> None:
        """Set the selected symbols.
        
        Args:
            symbols: List of symbols to select.
        """
        # Clear current selection
        for var in self.popular_vars.values():
            var.set(False)
        
        # Set popular stocks
        for symbol in symbols:
            if symbol in self.popular_vars:
                self.popular_vars[symbol].set(True)
        
        self._update_selected_symbols(symbols)