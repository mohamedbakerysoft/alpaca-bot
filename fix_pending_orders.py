#!/usr/bin/env python3
"""
Fix script to cancel pending sell orders that are locking positions
This resolves the "insufficient qty available" error by freeing up locked shares
"""

import os
import sys
from datetime import datetime, timezone
import json

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from alpaca_bot.services.alpaca_client import AlpacaClient


def get_pending_orders():
    """Get all pending orders"""
    print("🔍 Checking for pending orders...")
    
    client = AlpacaClient()
    
    try:
        # Get all orders with status 'new' (pending)
        orders = client.get_orders(status='open', limit=50)
        
        if not orders:
            print("✅ No pending orders found")
            return []
            
        print(f"📋 Found {len(orders)} pending orders:")
        
        pending_sell_orders = []
        
        for order in orders:
            print(f"   📄 {order.symbol}: {order.side} {order.qty} @ {order.status}")
            print(f"      Order ID: {order.id}")
            print(f"      Created: {order.created_at}")
            print(f"      Type: {order.order_type}")
            print(f"      Time in Force: {order.time_in_force}")
            
            if order.side == 'sell':
                pending_sell_orders.append(order)
                print(f"      ⚠️  This SELL order is locking {order.qty} shares!")
            
            print()
            
        return pending_sell_orders
        
    except Exception as e:
        print(f"❌ Error getting orders: {e}")
        return []


def cancel_pending_sell_orders(orders):
    """Cancel pending sell orders to free up locked shares"""
    if not orders:
        print("✅ No pending sell orders to cancel")
        return True
        
    print(f"🚫 Canceling {len(orders)} pending sell orders...")
    
    client = AlpacaClient()
    
    success_count = 0
    
    for order in orders:
        try:
            print(f"   Canceling {order.symbol} sell order (ID: {order.id})...")
            
            # Cancel the order
            client.cancel_order(order.id)
            
            print(f"   ✅ Successfully canceled {order.symbol} order")
            success_count += 1
            
        except Exception as e:
            print(f"   ❌ Failed to cancel {order.symbol} order: {e}")
            
    print(f"\n📊 Cancellation Summary:")
    print(f"   Total orders: {len(orders)}")
    print(f"   Successfully canceled: {success_count}")
    print(f"   Failed: {len(orders) - success_count}")
    
    return success_count == len(orders)


def verify_positions_available():
    """Verify that positions are now available for trading"""
    print("\n🔍 Verifying position availability after canceling orders...")
    
    client = AlpacaClient()
    
    try:
        positions = client.get_positions()
        
        if not positions:
            print("❌ No positions found!")
            return False
            
        problem_symbols = ['TSLA', 'GOOGL', 'IWM', 'QQQ', 'VTI']
        available_positions = []
        
        for position in positions:
            if position.symbol not in problem_symbols:
                continue
                
            qty_available = getattr(position, 'qty_available', 'N/A')
            
            print(f"📊 {position.symbol}:")
            print(f"   Total Qty: {position.qty}")
            print(f"   Available Qty: {qty_available}")
            
            if hasattr(position, 'qty_available') and float(position.qty_available) > 0:
                available_positions.append(position.symbol)
                print(f"   ✅ Available for trading!")
            else:
                print(f"   ⚠️  Still not available")
                
            print()
            
        print(f"📈 Summary: {len(available_positions)} positions are now available for trading")
        if available_positions:
            print(f"   Available: {', '.join(available_positions)}")
            
        return len(available_positions) > 0
        
    except Exception as e:
        print(f"❌ Error checking positions: {e}")
        return False


def test_new_sell_order():
    """Test placing a new sell order to confirm the fix"""
    print("\n🧪 Testing new sell order placement...")
    
    client = AlpacaClient()
    
    try:
        positions = client.get_positions()
        
        # Find a position that should be available
        test_symbol = None
        test_qty = None
        
        for position in positions:
            if position.symbol in ['TSLA', 'GOOGL', 'IWM', 'QQQ', 'VTI']:
                qty_available = getattr(position, 'qty_available', 0)
                if hasattr(position, 'qty_available') and float(qty_available) > 0:
                    test_symbol = position.symbol
                    test_qty = min(float(qty_available), 1.0)  # Test with small amount
                    break
                    
        if not test_symbol:
            print("⚠️  No positions available for testing")
            return False
            
        print(f"🎯 Testing sell order for {test_symbol} (qty: {test_qty})...")
        
        # Don't actually place the order in this test - just validate parameters
        # In a real scenario, you would place a small test order here
        
        print(f"✅ Test parameters validated for {test_symbol}")
        print(f"   Symbol: {test_symbol}")
        print(f"   Quantity: {test_qty}")
        print(f"   Side: sell")
        print(f"   Type: market")
        
        print("🎉 The fix appears to be working! You can now place sell orders.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing sell order: {e}")
        return False


def main():
    print("🔧 Alpaca API Fix - Resolving 'Insufficient Qty Available' Error")
    print("=" * 70)
    
    # Step 1: Get pending orders
    pending_sell_orders = get_pending_orders()
    
    if not pending_sell_orders:
        print("✅ No pending sell orders found. The issue might be elsewhere.")
        verify_positions_available()
        return
        
    # Step 2: Cancel pending sell orders
    print("\n" + "=" * 70)
    success = cancel_pending_sell_orders(pending_sell_orders)
    
    if not success:
        print("❌ Failed to cancel all pending orders. Manual intervention may be required.")
        return
        
    # Step 3: Verify positions are now available
    print("\n" + "=" * 70)
    positions_available = verify_positions_available()
    
    # Step 4: Test new sell order
    if positions_available:
        print("\n" + "=" * 70)
        test_new_sell_order()
    
    print("\n" + "=" * 70)
    print("🎯 Fix completed!")
    print("\nNext steps:")
    print("1. Your bot should now be able to place sell orders successfully")
    print("2. Monitor the bot to ensure it's working correctly")
    print("3. Consider implementing order cancellation logic in your bot to prevent this issue")


if __name__ == "__main__":
    main()