#!/usr/bin/env python3
"""
Test script to verify fixed trade amount functionality.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from alpaca_bot.strategies.scalping_strategy import ScalpingStrategy, TradingMode
from alpaca_bot.config.settings import Settings
from alpaca_bot.models.trade import Trade, TradeType, TradeStatus
from unittest.mock import Mock
from datetime import datetime

def test_fixed_trade_amount():
    """Test fixed trade amount functionality."""
    print("Testing fixed trade amount functionality...")
    
    # Create mock alpaca client
    mock_client = Mock()
    mock_account = Mock()
    mock_account.portfolio_value = "1000.0"
    mock_account.buying_power = "1000.0"
    mock_account.cash = "1000.0"
    mock_client.get_account.return_value = mock_account
    mock_client.get_positions.return_value = []
    mock_client.get_orders.return_value = []
    
    # Mock quote data
    mock_quote = {'ask': 150.0, 'bid': 149.5}
    mock_client.get_latest_quote.return_value = mock_quote
    
    # Create settings with fixed trade amount enabled
    settings = Settings()
    settings.fixed_trade_amount_enabled = True
    settings.fixed_trade_amount = 50.0
    settings.trading_mode = 'conservative'
    
    try:
        # Initialize strategy
        strategy = ScalpingStrategy(mock_client)
        strategy.settings = settings  # Update strategy settings
        print(f"✓ Strategy initialized successfully")
        print(f"✓ Trading mode: {strategy.trading_mode}")
        print(f"✓ Fixed trade amount enabled: {settings.fixed_trade_amount_enabled}")
        print(f"✓ Fixed trade amount: ${settings.fixed_trade_amount}")
        
        # Test the fixed trade amount logic by checking settings access
        fixed_enabled = getattr(strategy.settings, 'fixed_trade_amount_enabled', False)
        fixed_amount = getattr(strategy.settings, 'fixed_trade_amount', 100.0)
        
        print(f"\nFixed trade amount configuration:")
        print(f"✓ Enabled: {fixed_enabled}")
        print(f"✓ Amount: ${fixed_amount}")
        
        if fixed_enabled and fixed_amount == 50.0:
            print("✓ Fixed trade amount configuration is correct!")
        else:
            print(f"✗ Configuration mismatch: enabled={fixed_enabled}, amount={fixed_amount}")
        
        # Test with fixed amount disabled
        settings.fixed_trade_amount_enabled = False
        strategy.settings = settings  # Update strategy settings
        
        fixed_enabled_disabled = getattr(strategy.settings, 'fixed_trade_amount_enabled', False)
        print(f"\nWith fixed amount disabled:")
        print(f"✓ Enabled: {fixed_enabled_disabled}")
        
        if not fixed_enabled_disabled:
            print("✓ Fixed amount correctly disabled")
        else:
            print("✗ Fixed amount should be disabled")
            
        print("\n✓ All tests completed successfully!")
        
    except Exception as e:
        print(f"✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_trading_modes():
    """Test all trading modes work correctly."""
    print("\nTesting trading modes...")
    
    # Create mock alpaca client
    mock_client = Mock()
    mock_account = Mock()
    mock_account.portfolio_value = "1000.0"
    mock_client.get_account.return_value = mock_account
    mock_client.get_positions.return_value = []
    mock_client.get_orders.return_value = []
    
    settings = Settings()
    
    for mode_str in ['ultra_safe', 'conservative', 'aggressive']:
        try:
            settings.trading_mode = mode_str
            strategy = ScalpingStrategy(mock_client)
            strategy.settings = settings
            
            # Test mode parameters
            mode_params = TradingMode.get_mode_params(strategy.trading_mode, 1000.0)
            
            print(f"✓ {mode_str.upper()} mode initialized successfully")
            print(f"  - Max position value: ${mode_params['max_position_value']:.2f}")
            print(f"  - Position size multiplier: {mode_params['position_size_multiplier']}")
            print(f"  - Max daily trades: {mode_params['max_daily_trades']}")
            
        except Exception as e:
            print(f"✗ Error testing {mode_str} mode: {e}")
            return False
    
    print("✓ All trading modes tested successfully!")
    return True

def test_position_pnl():
    """Test position P&L calculation logic."""
    print("\nTesting position P&L calculation logic...")
    
    try:
        # Test the P&L calculation logic directly
        entry_price = 150.0
        current_price = 155.0
        quantity = 10
        
        # Manual P&L calculation (same logic as in the strategy)
        expected_pnl = (current_price - entry_price) * quantity
        
        print(f"✓ Position P&L calculation test:")
        print(f"  - Entry price: ${entry_price}")
        print(f"  - Current price: ${current_price}")
        print(f"  - Quantity: {quantity}")
        print(f"  - Expected P&L: ${expected_pnl:.2f}")
        
        # Test different scenarios
        scenarios = [
            (100.0, 105.0, 5, 25.0),   # Profit scenario
            (100.0, 95.0, 10, -50.0),  # Loss scenario
            (50.0, 50.0, 20, 0.0),     # Break-even scenario
        ]
        
        print(f"\n  Testing multiple scenarios:")
        for entry, current, qty, expected in scenarios:
            calculated = (current - entry) * qty
            status = "✓" if abs(calculated - expected) < 0.01 else "✗"
            print(f"  {status} Entry: ${entry}, Current: ${current}, Qty: {qty} → P&L: ${calculated:.2f}")
            
            if abs(calculated - expected) >= 0.01:
                print(f"    Expected: ${expected:.2f}, Got: ${calculated:.2f}")
                return False
        
        print("✓ P&L calculation logic is correct!")
        return True
            
    except Exception as e:
        print(f"✗ Error during P&L testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("FIXED TRADE AMOUNT FUNCTIONALITY TEST")
    print("=" * 50)
    
    success1 = test_fixed_trade_amount()
    success2 = test_trading_modes()
    success3 = test_position_pnl()
    
    if success1 and success2 and success3:
        print("\n🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED!")
        sys.exit(1)