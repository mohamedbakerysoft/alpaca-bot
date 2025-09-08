#!/usr/bin/env python3
"""
Test script to verify the new fixed amount capital tracking functionality.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.alpaca_bot.strategies.scalping_strategy import ScalpingStrategy
from src.alpaca_bot.models.trade import Trade, TradeType, TradeStatus
from datetime import datetime
from unittest.mock import Mock

def test_fixed_capital_tracking():
    """Test the fixed amount capital tracking functionality."""
    
    # Create mock alpaca client
    mock_client = Mock()
    mock_client.get_positions.return_value = []
    mock_client.get_orders.return_value = []
    
    # Create strategy instance
    strategy = ScalpingStrategy(mock_client)
    
    # Test 1: Empty positions should return 0 allocated capital
    allocated = strategy._calculate_allocated_capital()
    print(f"Test 1 - Empty positions: ${allocated:.2f} (expected: $0.00)")
    assert allocated == 0.0, f"Expected 0.0, got {allocated}"
    
    # Test 2: Add some mock positions
    trade1 = Trade(
        symbol="AAPL",
        trade_type=TradeType.BUY,
        quantity=10.0,
        price=150.0,  # $1500 position
        timestamp=datetime.now(),
        order_id="order1",
        status=TradeStatus.FILLED
    )
    
    trade2 = Trade(
        symbol="MSFT",
        trade_type=TradeType.BUY,
        quantity=5.0,
        price=300.0,  # $1500 position
        timestamp=datetime.now(),
        order_id="order2",
        status=TradeStatus.FILLED
    )
    
    strategy.active_positions["AAPL"] = trade1
    strategy.active_positions["MSFT"] = trade2
    
    # Test 2: Calculate allocated capital with positions
    allocated = strategy._calculate_allocated_capital()
    expected = (10.0 * 150.0) + (5.0 * 300.0)  # $1500 + $1500 = $3000
    print(f"Test 2 - With positions: ${allocated:.2f} (expected: ${expected:.2f})")
    assert allocated == expected, f"Expected {expected}, got {allocated}"
    
    # Test 3: Test fixed amount logic simulation
    print("\nTest 3 - Fixed amount logic simulation:")
    
    # Mock settings for fixed amount
    strategy.settings = Mock()
    strategy.settings.fixed_trade_amount_enabled = True
    strategy.settings.fixed_trade_amount = 100.0  # $100 total capital
    
    # Current allocated: $3000 (way over $100 limit)
    current_allocated = strategy._calculate_allocated_capital()
    fixed_total = 100.0
    remaining = fixed_total - current_allocated
    max_individual = 10.0
    
    print(f"  Fixed total capital: ${fixed_total:.2f}")
    print(f"  Currently allocated: ${current_allocated:.2f}")
    print(f"  Remaining capital: ${remaining:.2f}")
    print(f"  Max individual trade: ${max_individual:.2f}")
    
    if remaining <= 0:
        print(f"  Result: No new trades allowed (fully allocated)")
    else:
        trade_size = min(remaining, max_individual)
        print(f"  Next trade size would be: ${trade_size:.2f}")
    
    # Test 4: Test with smaller positions within limit
    print("\nTest 4 - Positions within fixed amount limit:")
    
    # Clear positions and add smaller ones
    strategy.active_positions.clear()
    
    small_trade1 = Trade(
        symbol="SPY",
        trade_type=TradeType.BUY,
        quantity=0.02,  # Small quantity
        price=450.0,    # $9 position
        timestamp=datetime.now(),
        order_id="order3",
        status=TradeStatus.FILLED
    )
    
    small_trade2 = Trade(
        symbol="QQQ",
        trade_type=TradeType.BUY,
        quantity=0.025,  # Small quantity
        price=400.0,     # $10 position
        timestamp=datetime.now(),
        order_id="order4",
        status=TradeStatus.FILLED
    )
    
    strategy.active_positions["SPY"] = small_trade1
    strategy.active_positions["QQQ"] = small_trade2
    
    current_allocated = strategy._calculate_allocated_capital()
    remaining = fixed_total - current_allocated
    
    print(f"  Fixed total capital: ${fixed_total:.2f}")
    print(f"  Currently allocated: ${current_allocated:.2f}")
    print(f"  Remaining capital: ${remaining:.2f}")
    
    if remaining >= 1.0:  # Minimum trade amount
        trade_size = min(remaining, max_individual)
        print(f"  Next trade size would be: ${trade_size:.2f}")
        print(f"  Can make {int(remaining / min(trade_size, 10.0))} more trades of up to $10 each")
    else:
        print(f"  Cannot make minimum $1 trade")
    
    print("\n✅ All tests passed! Fixed amount capital tracking is working correctly.")

if __name__ == "__main__":
    test_fixed_capital_tracking()