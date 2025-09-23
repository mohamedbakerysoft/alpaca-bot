#!/usr/bin/env python3
"""
Test script using the updated scalping strategy to test selling with pending order checks
"""

import os
import sys
from datetime import datetime

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from alpaca_bot.services.alpaca_client import AlpacaClient
from alpaca_bot.strategies.scalping_strategy import ScalpingStrategy
from alpaca_bot.config.settings import Settings


def test_strategy_sell():
    """Test selling using the updated scalping strategy with pending order checks"""
    print("🧪 Testing scalping strategy with pending order checks...")
    
    # Initialize client and strategy
    client = AlpacaClient()
    strategy = ScalpingStrategy(client)
    
    # Get current positions
    positions = client.get_positions()
    
    if not positions:
        print("❌ No positions found!")
        return
        
    print(f"✅ Found {len(positions)} positions")
    
    # Test symbols that were having issues
    test_symbols = ['TSLA', 'QQQ', 'VTI', 'GOOGL', 'IWM']
    
    for position in positions:
        symbol = position.symbol
        if symbol not in test_symbols:
            continue
            
        # Calculate profit percentage
        unrealized_pl = float(position.unrealized_pl or 0)
        market_value = float(position.market_value or 0)
        
        if market_value == 0:
            continue
            
        profit_pct = (unrealized_pl / market_value) * 100
        qty = float(position.qty)
        
        print(f"\n🔍 Testing {symbol} with strategy:")
        print(f"   Quantity: {qty}")
        print(f"   Market Value: ${market_value:.2f}")
        print(f"   Unrealized P&L: ${unrealized_pl:.2f}")
        print(f"   Profit %: {profit_pct:.2f}%")
        
        # Only test profitable positions
        if profit_pct > 0.10:
            print(f"   ✅ {symbol} is profitable ({profit_pct:.2f}%), testing strategy sell...")
            
            # First, cancel any existing pending orders for this symbol
            canceled_count = strategy.cancel_pending_orders(symbol)
            if canceled_count > 0:
                print(f"   🚫 Canceled {canceled_count} pending orders for {symbol}")
            
            # Add position to strategy's active positions for testing
            from alpaca_bot.models.trade import Trade, TradeType, TradeStatus
            
            # Create a mock trade object for the existing position
            avg_cost = float(getattr(position, 'avg_cost_basis', getattr(position, 'avg_cost', 100.0)))
            mock_trade = Trade(
                symbol=symbol,
                trade_type=TradeType.BUY,
                quantity=qty,
                price=avg_cost,
                timestamp=datetime.now(),
                order_id="mock_order_id",
                status=TradeStatus.FILLED,
                notes="Mock trade for testing"
            )
            
            # Add to strategy's active positions
            strategy.active_positions[symbol] = mock_trade
            
            # Try to execute sell order using strategy
            try:
                trade = strategy._execute_sell_order(symbol, "Test sell", 1.0)
                
                if trade:
                    print(f"   🎉 SUCCESS: Strategy sell order placed for {symbol}")
                    print(f"      Order ID: {trade.order_id}")
                    print(f"      Status: {trade.status}")
                    print(f"      Quantity: {trade.quantity}")
                else:
                    print(f"   ⚠️  Strategy returned None - likely due to pending order check")
                    
            except Exception as e:
                print(f"   ❌ ERROR with strategy sell for {symbol}: {str(e)}")
                print(f"      Error type: {type(e).__name__}")
                
        else:
            print(f"   ⏭️  {symbol} profit ({profit_pct:.2f}%) below 0.10% threshold, skipping")


def test_cancel_all_pending():
    """Test canceling all pending sell orders"""
    print("\n🚫 Testing cancel all pending orders...")
    
    client = AlpacaClient()
    strategy = ScalpingStrategy(client)
    
    canceled_count = strategy.cancel_pending_orders()
    print(f"✅ Canceled {canceled_count} pending sell orders")
    
    return canceled_count


def main():
    print("🚀 Scalping Strategy Sell Test with Pending Order Checks")
    print("=" * 70)
    
    # First, cancel all pending orders to start fresh
    canceled_count = test_cancel_all_pending()
    
    if canceled_count > 0:
        print(f"\n⏳ Waiting 2 seconds for order cancellations to process...")
        import time
        time.sleep(2)
    
    # Test strategy selling
    print("\n" + "=" * 70)
    test_strategy_sell()
    
    print("\n" + "=" * 70)
    print("✅ Strategy sell test completed!")


if __name__ == "__main__":
    main()