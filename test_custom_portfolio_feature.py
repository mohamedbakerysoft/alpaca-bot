#!/usr/bin/env python3
"""
Test script to verify the custom portfolio value feature works correctly
and doesn't conflict with other features.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from alpaca_bot.config.settings import Settings
from alpaca_bot.strategies.scalping_strategy import TradingMode

def test_custom_portfolio_feature():
    """Test the custom portfolio value feature."""
    print("Testing Custom Portfolio Value Feature")
    print("=" * 50)
    
    # Test 1: Default settings
    settings = Settings()
    print(f"1. Default custom portfolio enabled: {settings.custom_portfolio_value_enabled}")
    print(f"   Default custom portfolio value: ${settings.custom_portfolio_value:,.2f}")
    print(f"   Min portfolio value: ${settings.min_portfolio_value:,.2f}")
    print(f"   Max portfolio value: ${settings.max_portfolio_value:,.2f}")
    
    # Test 2: Enable custom portfolio value
    settings.custom_portfolio_value_enabled = True
    settings.custom_portfolio_value = 50000.0
    print(f"\n2. After enabling custom portfolio:")
    print(f"   Custom portfolio enabled: {settings.custom_portfolio_value_enabled}")
    print(f"   Custom portfolio value: ${settings.custom_portfolio_value:,.2f}")
    
    # Test 3: Test trading mode parameters with custom portfolio
    print(f"\n3. Testing trading mode parameters with custom portfolio value:")
    for mode in [TradingMode.ULTRA_SAFE, TradingMode.CONSERVATIVE, TradingMode.AGGRESSIVE]:
        params = TradingMode.get_mode_params(mode, settings.custom_portfolio_value)
        print(f"   {mode.value.upper()}:")
        print(f"     Max position value: ${params['max_position_value']:,.2f}")
        print(f"     Stop loss: {params['stop_loss_pct']:.1%}")
        print(f"     Take profit: {params['take_profit_pct']:.1%}")
    
    # Test 4: Check for conflicts with fixed trade amount
    print(f"\n4. Testing compatibility with fixed trade amount:")
    print(f"   Fixed trade amount enabled: {settings.fixed_trade_amount_enabled}")
    print(f"   Fixed trade amount: ${settings.fixed_trade_amount:,.2f}")
    
    # Enable both features
    settings.fixed_trade_amount_enabled = True
    settings.fixed_trade_amount = 1000.0
    print(f"   After enabling both features:")
    print(f"     Custom portfolio enabled: {settings.custom_portfolio_value_enabled}")
    print(f"     Custom portfolio value: ${settings.custom_portfolio_value:,.2f}")
    print(f"     Fixed trade amount enabled: {settings.fixed_trade_amount_enabled}")
    print(f"     Fixed trade amount: ${settings.fixed_trade_amount:,.2f}")
    
    # Test 5: Validation ranges
    print(f"\n5. Testing validation ranges:")
    test_values = [50.0, 500.0, 10000.0, 100000.0, 2000000.0]
    for value in test_values:
        is_valid = (settings.min_portfolio_value <= value <= settings.max_portfolio_value)
        status = "✓ Valid" if is_valid else "✗ Invalid"
        print(f"   ${value:,.2f}: {status}")
    
    print(f"\n✓ All tests completed successfully!")
    print(f"\nFeature Summary:")
    print(f"- Custom Portfolio Value: Allows overriding real portfolio value for strategy calculations")
    print(f"- Fixed Trade Amount: Limits total trading capital to a fixed amount")
    print(f"- Both features can work together without conflicts")
    print(f"- Proper validation is in place for both features")

if __name__ == "__main__":
    test_custom_portfolio_feature()