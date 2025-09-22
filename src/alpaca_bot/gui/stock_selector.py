"""Stock selector component for the Alpaca trading bot.

This module provides:
- Manual stock selection via dropdown
- Popular stock presets
- Custom symbol input
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Callable, Optional

from ..services.alpaca_client import AlpacaClient
from ..utils.logging_utils import get_logger


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
        # Manual selection frame
        self.manual_frame = ttk.Frame(self.frame)
        self.manual_frame.pack(fill=tk.X, pady=(0, 10))
        
        self._create_manual_selection()
        
        # Selected symbols display
        self._create_symbols_display()
        
        # Set popular stocks as selected by default after all widgets are created
        self._update_manual_selection()
    
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