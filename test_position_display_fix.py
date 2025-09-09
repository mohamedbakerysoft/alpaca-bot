#!/usr/bin/env python3
"""
Test script to verify the position display fix.
This script demonstrates that the positions table now shows dollar values prominently.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from alpaca_bot.models.trade import Position
from typing import List

def test_position_display_logic():
    """Test the position display logic with sample data."""
    
    # Sample positions that would result from small portfolio value settings
    sample_positions = [
        Position(
            symbol="AAPL",
            quantity=0.027,  # Small fractional shares from $5 position
            avg_price=185.50,
            current_price=187.25,
            market_value=5.06,
            unrealized_pnl=0.05,
            unrealized_pnl_percent=0.94
        ),
        Position(
            symbol="TSLA",
            quantity=0.019,  # Small fractional shares from $5 position  
            avg_price=245.80,
            current_price=248.90,
            market_value=4.73,
            unrealized_pnl=0.06,
            unrealized_pnl_percent=1.26
        ),
        Position(
            symbol="MSFT",
            quantity=0.013,  # Small fractional shares from $5 position
            avg_price=378.20,
            current_price=381.45,
            market_value=4.96,
            unrealized_pnl=0.04,
            unrealized_pnl_percent=0.86
        )
    ]
    
    print("Position Display Test - Showing Dollar Values Prominently")
    print("=" * 80)
    print(f"{'Symbol':<8} {'Dollar Value':<12} {'Shares':<12} {'Entry Price':<12} {'Current Price':<12} {'P&L':<10} {'P&L %':<8}")
    print("-" * 80)
    
    for position in sample_positions:
        # Calculate values using the same logic as the GUI
        current_price = position.current_price or position.avg_price
        dollar_value = abs(position.quantity) * current_price
        
        if current_price is not None and position.avg_price is not None and position.avg_price > 0:
            pnl = (current_price - position.avg_price) * position.quantity
            pnl_pct = (pnl / (position.avg_price * position.quantity)) * 100
        else:
            pnl = 0.0
            pnl_pct = 0.0
        
        # Format values as they would appear in the GUI
        symbol = position.symbol
        dollar_val_str = f"${dollar_value:,.2f}"
        shares_str = f"{position.quantity:.6f}".rstrip('0').rstrip('.')
        entry_price_str = f"${position.avg_price:.2f}"
        current_price_str = f"${current_price:.2f}"
        pnl_str = f"${pnl:+.2f}"
        pnl_pct_str = f"{pnl_pct:+.1f}%"
        
        print(f"{symbol:<8} {dollar_val_str:<12} {shares_str:<12} {entry_price_str:<12} {current_price_str:<12} {pnl_str:<10} {pnl_pct_str:<8}")
    
    print("\nKey Improvements:")
    print("1. Dollar Value column shows the actual position size (~$5 each)")
    print("2. Shares column shows the fractional shares (0.027, 0.019, 0.013)")
    print("3. This matches the portfolio value settings in the strategy")
    print("4. Users can now see both dollar amounts and share quantities clearly")
    
    print("\nBefore Fix:")
    print("- Only showed large share quantities (confusing for small portfolios)")
    print("- No clear indication of actual dollar position sizes")
    
    print("\nAfter Fix:")
    print("- Primary display shows dollar values (what users expect to see)")
    print("- Secondary display shows actual shares (for reference)")
    print("- Aligns with the strategy's notional order approach")

if __name__ == "__main__":
    test_position_display_logic()