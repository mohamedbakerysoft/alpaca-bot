#!/usr/bin/env python3
"""Debug script to investigate why no trading orders are being executed."""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from alpaca_bot.config.settings import settings
from alpaca_bot.services.alpaca_client import AlpacaClient
from alpaca_bot.strategies.simple_strategy import EnhancedStrategy
from alpaca_bot.utils.logging_utils import setup_logging, get_logger

def main():
    """Debug trading issues."""
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)
    
    print("=== Alpaca Trading Bot Debug ===")
    print()
    
    try:
        # Initialize Alpaca client
        print("1. Initializing Alpaca client...")
        alpaca_client = AlpacaClient()
        print("✓ Alpaca client initialized successfully")
        
        # Check account status
        print("\n2. Checking account status...")
        account = alpaca_client.get_account()
        if account:
            print(f"✓ Account Status: {account.status}")
            print(f"✓ Portfolio Value: ${float(account.portfolio_value):,.2f}")
            print(f"✓ Buying Power: ${float(account.buying_power):,.2f}")
            print(f"✓ Cash: ${float(account.cash):,.2f}")
            print(f"✓ Day Trade Buying Power: ${float(account.daytrading_buying_power):,.2f}")
            print(f"✓ Pattern Day Trader: {account.pattern_day_trader}")
        else:
            print("✗ Failed to get account information")
            return
        
        # Check positions
        print("\n3. Checking current positions...")
        positions = alpaca_client.get_positions()
        if positions:
            print(f"✓ Found {len(positions)} positions:")
            for pos in positions:
                print(f"  - {pos.symbol}: {pos.qty} shares @ ${float(pos.avg_cost):.2f}")
        else:
            print("✓ No current positions")
        
        # Check orders
        print("\n4. Checking recent orders...")
        orders = alpaca_client.api.list_orders(status='all', limit=10)
        if orders:
            print(f"✓ Found {len(orders)} recent orders:")
            for order in orders:
                print(f"  - {order.symbol}: {order.side} {order.qty} @ {order.order_type} - {order.status}")
        else:
            print("✓ No recent orders")
        
        # Initialize strategy
        print("\n5. Initializing strategy...")
        strategy = EnhancedStrategy(alpaca_client, settings)
        print("✓ Strategy initialized successfully")
        
        # Check strategy settings
        print("\n6. Strategy Configuration:")
        print(f"✓ Position Size %: {strategy.position_size_pct * 100:.2f}%")
        print(f"✓ Stop Loss %: {strategy.stop_loss_pct * 100:.2f}%")
        print(f"✓ Take Profit %: {strategy.take_profit_pct * 100:.2f}%")
        print(f"✓ Max Daily Trades: {strategy.max_daily_trades}")
        print(f"✓ Daily Trades Count: {strategy.daily_trades_count}")
        print(f"✓ Active Positions: {len(strategy.active_positions)}")
        
        # Test symbol analysis
        print("\n7. Testing symbol analysis...")
        test_symbols = ['AAPL', 'MSFT', 'GOOGL']
        
        for symbol in test_symbols:
            print(f"\nAnalyzing {symbol}:")
            try:
                # Analyze symbol
                stock_data = strategy.analyze_symbol(symbol)
                if stock_data:
                    print(f"  ✓ Stock data retrieved")
                    print(f"  ✓ Current Price: ${stock_data.current_quote.bid:.2f}")
                    
                    # Generate signals
                    signals = strategy.generate_signals(stock_data)
                    if signals:
                        print(f"  ✓ Generated {len(signals)} signals:")
                        for signal_type, reason in signals:
                            print(f"    - {signal_type}: {reason}")
                    else:
                        print(f"  ✓ No signals generated (conditions not met)")
                        
                        # Show technical indicators for debugging
                        if stock_data.technical_indicators:
                            ti = stock_data.technical_indicators
                            print(f"    RSI: {ti.rsi:.1f}")
                            print(f"    MACD: {ti.macd:.4f} vs Signal: {ti.macd_signal:.4f}")
                            print(f"    SMA20: ${ti.sma_20:.2f}, SMA50: ${ti.sma_50:.2f}")
                            
                            # Check trend
                            trend = strategy._analyze_trend(ti)
                            print(f"    Trend: {trend}")
                else:
                    print(f"  ✗ Failed to get stock data for {symbol}")
                    
            except Exception as e:
                print(f"  ✗ Error analyzing {symbol}: {e}")
        
        # Check market conditions
        print("\n8. Market Conditions:")
        print(f"✓ Paper Trading: {settings.paper_trading}")
        print(f"✓ Extended Hours Enabled: {settings.extended_hours_enabled}")
        print(f"✓ Fixed Trade Amount Enabled: {settings.fixed_trade_amount_enabled}")
        if settings.fixed_trade_amount_enabled:
            print(f"✓ Fixed Trade Amount: ${settings.fixed_trade_amount:.2f}")
        
        # Calculate position size for debugging
        print("\n9. Position Size Calculation:")
        portfolio_value = float(account.portfolio_value)
        position_value = portfolio_value * strategy.position_size_pct
        print(f"✓ Portfolio Value: ${portfolio_value:,.2f}")
        print(f"✓ Position Size %: {strategy.position_size_pct * 100:.2f}%")
        print(f"✓ Position Value: ${position_value:,.2f}")
        print(f"✓ Minimum Position Value: $1.00")
        
        if position_value < 1.0:
            print("⚠️  WARNING: Calculated position value is less than $1.00")
        
        print("\n=== Debug Complete ===")
        
    except Exception as e:
        print(f"✗ Error during debug: {e}")
        logger.error(f"Debug error: {e}", exc_info=True)

if __name__ == "__main__":
    main()