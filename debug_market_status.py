#!/usr/bin/env python3
"""
Debug script to investigate the "insufficient qty available" error
This script will check market status, position details, and trading hours
"""

import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
import json

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from alpaca_bot.services.alpaca_client import AlpacaClient


def check_market_status():
    """Check current market status and trading hours"""
    print("🕐 Checking market status...")
    
    client = AlpacaClient()
    
    try:
        # Get market clock
        clock = client.api.get_clock()
        print(f"✅ Market Status:")
        print(f"   Is Open: {clock.is_open}")
        print(f"   Current Time: {clock.timestamp}")
        print(f"   Next Open: {clock.next_open}")
        print(f"   Next Close: {clock.next_close}")
        
        # Check if we're in extended hours
        now = datetime.now(timezone.utc)
        market_open = clock.next_open if not clock.is_open else None
        market_close = clock.next_close if clock.is_open else None
        
        print(f"   Current UTC Time: {now}")
        
        # Get calendar for today
        calendar = client.api.get_calendar(start=now.date(), end=now.date())
        if calendar:
            today_session = calendar[0]
            print(f"   Regular Hours: {today_session.open} - {today_session.close}")
            
            # Check if we're in pre-market or after-hours
            if hasattr(today_session, 'session_open') and hasattr(today_session, 'session_close'):
                print(f"   Extended Hours: {today_session.session_open} - {today_session.session_close}")
        
        return clock.is_open
        
    except Exception as e:
        print(f"❌ Error checking market status: {e}")
        return False


def check_position_details():
    """Check detailed position information"""
    print("\n📊 Checking position details...")
    
    client = AlpacaClient()
    
    try:
        positions = client.get_positions()
        
        if not positions:
            print("❌ No positions found!")
            return
            
        print(f"✅ Found {len(positions)} positions")
        
        # Focus on the problematic symbols
        problem_symbols = ['TSLA', 'GOOGL', 'IWM', 'QQQ', 'VTI']
        
        for position in positions:
            if position.symbol not in problem_symbols:
                continue
                
            print(f"\n🔍 {position.symbol} Position Details:")
            print(f"   Quantity: {position.qty}")
            print(f"   Market Value: ${float(position.market_value):.2f}")
            print(f"   Side: {position.side}")
            print(f"   Average Entry Price: ${float(position.avg_entry_price):.2f}")
            print(f"   Current Price: ${float(position.current_price):.2f}")
            print(f"   Unrealized P&L: ${float(position.unrealized_pl):.2f}")
            
            # Check additional attributes that might affect availability
            if hasattr(position, 'qty_available'):
                print(f"   Quantity Available: {position.qty_available}")
            
            # Check if position is long or short
            qty_float = float(position.qty)
            if qty_float > 0:
                print(f"   Position Type: LONG")
            elif qty_float < 0:
                print(f"   Position Type: SHORT")
            else:
                print(f"   Position Type: ZERO (This might be the issue!)")
                
            # Try to get more details about the position
            try:
                # Check recent orders for this symbol
                orders = client.get_orders(status='all', limit=20)
                symbol_orders = [o for o in orders if o.symbol == position.symbol]
                
                print(f"   Recent Orders: {len(symbol_orders)}")
                for order in symbol_orders[-3:]:  # Last 3 orders
                    print(f"      {order.side} {order.qty} @ {order.status} ({order.created_at})")
                    if hasattr(order, 'filled_qty') and order.filled_qty:
                        print(f"         Filled: {order.filled_qty}")
                        
            except Exception as order_error:
                print(f"   ⚠️  Could not get order details: {order_error}")
                
    except Exception as e:
        print(f"❌ Error checking positions: {e}")


def check_account_details():
    """Check account configuration and capabilities"""
    print("\n🏦 Checking account details...")
    
    client = AlpacaClient()
    
    try:
        account = client.get_account()
        
        print(f"✅ Account Information:")
        print(f"   Status: {account.status}")
        print(f"   Account Type: {getattr(account, 'account_type', 'N/A')}")
        print(f"   Trading Blocked: {getattr(account, 'trading_blocked', 'N/A')}")
        print(f"   Transfers Blocked: {getattr(account, 'transfers_blocked', 'N/A')}")
        print(f"   Account Blocked: {getattr(account, 'account_blocked', 'N/A')}")
        print(f"   Pattern Day Trader: {getattr(account, 'pattern_day_trader', 'N/A')}")
        print(f"   Day Trading Buying Power: ${float(getattr(account, 'daytrading_buying_power', 0)):.2f}")
        print(f"   Buying Power: ${float(account.buying_power):.2f}")
        print(f"   Cash: ${float(account.cash):.2f}")
        print(f"   Portfolio Value: ${float(account.portfolio_value):.2f}")
        
        # Check for any restrictions
        if hasattr(account, 'max_margin_multiplier'):
            print(f"   Max Margin Multiplier: {account.max_margin_multiplier}")
            
        # Check crypto and options trading
        if hasattr(account, 'crypto_status'):
            print(f"   Crypto Status: {account.crypto_status}")
        if hasattr(account, 'options_trading_level'):
            print(f"   Options Trading Level: {account.options_trading_level}")
            
    except Exception as e:
        print(f"❌ Error checking account: {e}")


def test_fractional_shares():
    """Test if the issue is related to fractional shares"""
    print("\n🔢 Testing fractional share handling...")
    
    client = AlpacaClient()
    
    try:
        positions = client.get_positions()
        
        for position in positions:
            if position.symbol not in ['TSLA', 'GOOGL']:  # Test with 2 symbols
                continue
                
            qty = float(position.qty)
            print(f"\n🧮 {position.symbol} Quantity Analysis:")
            print(f"   Original Qty: {qty}")
            print(f"   Is Fractional: {qty != int(qty)}")
            print(f"   Rounded Down: {int(qty)}")
            print(f"   Decimal Part: {qty - int(qty):.8f}")
            
            # Try different quantity approaches
            if qty > 0:
                test_quantities = [
                    qty,  # Original quantity
                    int(qty),  # Rounded down
                    round(qty, 6),  # Rounded to 6 decimals
                    round(qty, 2),  # Rounded to 2 decimals
                ]
                
                for test_qty in test_quantities:
                    if test_qty <= 0:
                        continue
                        
                    print(f"   Testing qty {test_qty}...")
                    
                    # Don't actually place the order, just validate parameters
                    try:
                        # This is just parameter validation, not actual order placement
                        if test_qty > 0:
                            print(f"      ✅ Qty {test_qty} would be valid for order")
                    except Exception as e:
                        print(f"      ❌ Qty {test_qty} validation failed: {e}")
                        
    except Exception as e:
        print(f"❌ Error testing fractional shares: {e}")


def check_extended_hours_config():
    """Check extended hours trading configuration"""
    print("\n🌙 Checking extended hours configuration...")
    
    # Check if our bot is configured for extended hours
    try:
        from alpaca_bot.config.settings import settings
        
        print(f"✅ Bot Configuration:")
        print(f"   Extended Hours Enabled: {getattr(settings, 'extended_hours_enabled', 'Not set')}")
        print(f"   Trading Mode: {getattr(settings, 'trading_mode', 'Not set')}")
        
        # Check environment variables
        import os
        extended_hours = os.getenv('EXTENDED_HOURS_ENABLED', 'Not set')
        print(f"   ENV Extended Hours: {extended_hours}")
        
    except Exception as e:
        print(f"❌ Error checking configuration: {e}")


if __name__ == "__main__":
    print("🔍 Alpaca API Debug - Insufficient Qty Investigation")
    print("=" * 60)
    
    # Run all checks
    market_open = check_market_status()
    check_account_details()
    check_position_details()
    test_fractional_shares()
    check_extended_hours_config()
    
    print("\n" + "=" * 60)
    print("🎯 Investigation completed!")
    
    if not market_open:
        print("⚠️  Market is currently CLOSED - this might affect position availability")
    else:
        print("✅ Market is OPEN - position availability issue needs further investigation")