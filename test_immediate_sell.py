#!/usr/bin/env python3
"""
اختبار التنفيذ الفوري لأوامر البيع
Test immediate execution of sell orders
"""

import sys
import os
from datetime import datetime
import time

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from alpaca_bot.services.alpaca_client import AlpacaClient
from alpaca_bot.utils.market_utils import MarketHours
import alpaca_bot.config.settings as settings

def test_immediate_sell():
    """اختبار التنفيذ الفوري لأوامر البيع"""
    
    print("🔍 اختبار التنفيذ الفوري لأوامر البيع")
    print("=" * 50)
    
    # Initialize clients
    alpaca_client = AlpacaClient()
    
    # Check market status
    print("\n📊 حالة السوق:")
    market_status = MarketHours.is_market_open(
        weekend_trading_enabled=getattr(settings, 'weekend_trading_enabled', False),
        extended_hours_enabled=getattr(settings, 'extended_hours_enabled', False)
    )
    extended_hours = MarketHours.is_extended_hours()
    
    print(f"السوق مفتوح: {'✅ نعم' if market_status else '❌ لا'}")
    print(f"ساعات ممتدة: {'✅ نعم' if extended_hours else '❌ لا'}")
    
    # Get current positions
    print("\n💼 المراكز الحالية:")
    try:
        positions = alpaca_client.get_positions()
        if not positions:
            print("❌ لا توجد مراكز مفتوحة للاختبار")
            return
            
        for position in positions[:3]:  # Show first 3 positions
            symbol = position.symbol
            qty = float(position.qty)
            market_value = float(position.market_value)
            
            print(f"📈 {symbol}: {qty} سهم (${market_value:.2f})")
            
            # Test different order configurations
            test_configs = [
                {
                    "name": "أمر سوق عادي",
                    "params": {
                        "order_type": "market",
                        "time_in_force": "day"
                    }
                },
                {
                    "name": "أمر سوق GTC",
                    "params": {
                        "order_type": "market", 
                        "time_in_force": "gtc"
                    }
                },
                {
                    "name": "أمر سوق + ساعات ممتدة",
                    "params": {
                        "order_type": "market",
                        "time_in_force": "gtc",
                        "extended_hours": True
                    }
                },
                {
                    "name": "أمر IOC (فوري أو إلغاء)",
                    "params": {
                        "order_type": "market",
                        "time_in_force": "ioc"
                    }
                }
            ]
            
            print(f"\n🧪 اختبار تكوينات مختلفة لـ {symbol}:")
            
            for config in test_configs:
                print(f"\n  📋 {config['name']}:")
                
                try:
                    # Get current quote
                    quote = alpaca_client.get_latest_quote(symbol)
                    if quote:
                        bid_price = float(quote.get('bid', 0))
                        ask_price = float(quote.get('ask', 0))
                        print(f"     💰 السعر: Bid ${bid_price:.2f} | Ask ${ask_price:.2f}")
                    
                    # Simulate order (don't actually place it)
                    print(f"     ⚙️  المعاملات: {config['params']}")
                    
                    # Check if this configuration would work
                    if config['params'].get('extended_hours') and not extended_hours and not market_status:
                        print("     ⚠️  يتطلب ساعات ممتدة أو سوق مفتوح")
                    elif config['params']['time_in_force'] == 'ioc' and not market_status:
                        print("     ⚠️  IOC يتطلب سوق مفتوح")
                    elif config['params']['time_in_force'] == 'day' and not market_status:
                        print("     ⏳ سينتظر حتى فتح السوق")
                    else:
                        print("     ✅ يمكن تنفيذه الآن")
                        
                except Exception as e:
                    print(f"     ❌ خطأ: {str(e)}")
            
            break  # Test only first position
            
    except Exception as e:
        print(f"❌ خطأ في الحصول على المراكز: {str(e)}")
    
    # Show recommendations
    print("\n💡 التوصيات:")
    print("=" * 30)
    
    if market_status:
        print("✅ السوق مفتوح - يمكن استخدام أي تكوين")
        print("🚀 الأفضل: أمر سوق عادي مع time_in_force='ioc'")
    elif extended_hours:
        print("🌙 ساعات ممتدة - استخدم extended_hours=True")
        print("🚀 الأفضل: أمر سوق مع time_in_force='gtc' و extended_hours=True")
    else:
        print("😴 السوق مغلق - الأوامر ستنتظر حتى الفتح")
        print("🚀 الأفضل: أمر سوق مع time_in_force='gtc'")
    
    print("\n🔧 إعدادات الحساب:")
    print(f"التداول في الساعات الممتدة: {'✅ مفعل' if getattr(settings, 'extended_hours_enabled', False) else '❌ معطل'}")
    print(f"نوع التداول: {getattr(settings, 'trading_mode', 'غير محدد')}")

if __name__ == "__main__":
    test_immediate_sell()