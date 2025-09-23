#!/usr/bin/env python3
"""
Manual test script to sell profitable positions and test Alpaca API
This script will help identify if the issue is with the bot logic or Alpaca Paper Trading API
"""

import os
import sys
from decimal import Decimal
from typing import List, Dict, Any

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from alpaca_bot.services.alpaca_client import AlpacaClient
from alpaca_bot.config.settings import Settings


def test_manual_sell():
    """Test manual selling of profitable positions"""
    print("🔧 Starting manual sell test...")
    
    # Initialize client (no parameters needed)
    client = AlpacaClient()
    
    try:
        # Get current positions
        print("\n📊 Getting current positions...")
        positions = client.get_positions()
        
        if not positions:
            print("❌ No positions found!")
            return
            
        print(f"✅ Found {len(positions)} positions")
        
        # Define profitable positions to test (based on the screenshot)
        profitable_symbols = ['TSLA', 'GOOGL', 'IWM', 'AAPL', 'QQQ', 'VTI', 'DIA']
        
        for position in positions:
            symbol = position.symbol
            if symbol not in profitable_symbols:
                continue
                
            # Calculate profit percentage
            unrealized_pl = float(position.unrealized_pl or 0)
            market_value = float(position.market_value or 0)
            
            if market_value == 0:
                continue
                
            profit_pct = (unrealized_pl / market_value) * 100
            qty = float(position.qty)
            
            print(f"\n🔍 Testing {symbol}:")
            print(f"   Quantity: {qty}")
            print(f"   Market Value: ${market_value:.2f}")
            print(f"   Unrealized P&L: ${unrealized_pl:.2f}")
            print(f"   Profit %: {profit_pct:.2f}%")
            
            # Only attempt to sell if profitable above 0.10%
            if profit_pct > 0.10:
                print(f"   ✅ {symbol} is profitable ({profit_pct:.2f}%), attempting to sell...")
                
                try:
                    # Attempt to place sell order
                    order = client.place_order(
                        symbol=symbol,
                        qty=abs(qty),  # Use absolute value
                        side='sell',
                        order_type='market',
                        time_in_force='day'
                    )
                    
                    if order:
                        print(f"   🎉 SUCCESS: Sell order placed for {symbol}")
                        print(f"      Order ID: {order.id}")
                        print(f"      Status: {order.status}")
                        print(f"      Quantity: {order.qty}")
                    else:
                        print(f"   ❌ FAILED: No order returned for {symbol}")
                        
                except Exception as e:
                    print(f"   ❌ ERROR selling {symbol}: {str(e)}")
                    print(f"      Error type: {type(e).__name__}")
                    
                    # Check if it's the "insufficient qty" error
                    if "insufficient qty available" in str(e).lower():
                        print(f"      🔍 This is the 'insufficient qty' error we've been seeing!")
                        
                        # Try to get more details about the position
                        try:
                            account = client.get_account()
                            print(f"      Account buying power: ${float(account.buying_power):.2f}")
                            print(f"      Account equity: ${float(account.equity):.2f}")
                            
                            # Check recent orders for this symbol
                            orders = client.get_orders(status='all', limit=10)
                            recent_orders = [o for o in orders if o.symbol == symbol]
                            print(f"      Recent orders for {symbol}: {len(recent_orders)}")
                            
                        except Exception as detail_error:
                            print(f"      Could not get additional details: {detail_error}")
                            
            else:
                print(f"   ⏭️  {symbol} profit ({profit_pct:.2f}%) below 0.10% threshold, skipping")
                
    except Exception as e:
        print(f"❌ Error in test_manual_sell: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()


def test_account_info():
    """Test getting account information"""
    print("\n🏦 Testing account information...")
    
    client = AlpacaClient()
    
    try:
        account = client.get_account()
        print(f"✅ Account Status: {account.status}")
        print(f"   Buying Power: ${float(account.buying_power):.2f}")
        print(f"   Cash: ${float(account.cash):.2f}")
        print(f"   Portfolio Value: ${float(account.portfolio_value):.2f}")
        print(f"   Equity: ${float(account.equity):.2f}")
        
    except Exception as e:
        print(f"❌ Error getting account info: {str(e)}")


def test_recent_orders():
    """Test getting recent orders"""
    print("\n📋 Testing recent orders...")
    
    client = AlpacaClient()
    
    try:
        orders = client.get_orders(status='all', limit=20)
        print(f"✅ Found {len(orders)} recent orders")
        
        for order in orders[-5:]:  # Show last 5 orders
            print(f"   {order.symbol}: {order.side} {order.qty} @ {order.status}")
            if hasattr(order, 'filled_at') and order.filled_at:
                print(f"      Filled at: {order.filled_at}")
                
    except Exception as e:
        print(f"❌ Error getting orders: {str(e)}")


if __name__ == "__main__":
    print("🚀 Alpaca Bot Manual Sell Test")
    print("=" * 50)
    
    # Test account info first
    test_account_info()
    
    # Test recent orders
    test_recent_orders()
    
    # Test manual selling
    test_manual_sell()
    
    print("\n" + "=" * 50)
    print("✅ Manual sell test completed!")