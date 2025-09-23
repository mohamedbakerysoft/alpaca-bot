#!/usr/bin/env python3
"""
اختبار أمر بيع فعلي في الساعات الممتدة
Test Actual Extended Hours Sell Order
"""

import os
import sys
from pathlib import Path

# إضافة مسار المشروع
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from alpaca_bot.config.settings import Settings
from alpaca_bot.services.alpaca_client import AlpacaClient
from alpaca_bot.utils.market_utils import MarketHours

def test_extended_hours_sell():
    """اختبار أمر بيع في الساعات الممتدة"""
    print("🧪 اختبار أمر بيع فعلي في الساعات الممتدة")
    print("=" * 50)
    
    try:
        # تحميل الإعدادات
        settings = Settings()
        
        # إنشاء عميل Alpaca
        client = AlpacaClient()
        
        # فحص حالة السوق
        market_hours = MarketHours()
        is_open = market_hours.is_market_open(
            weekend_trading_enabled=getattr(settings, 'weekend_trading_enabled', False),
            extended_hours_enabled=getattr(settings, 'extended_hours_enabled', False)
        )
        is_extended = MarketHours.is_extended_hours()
        
        print(f"📊 حالة السوق:")
        print(f"السوق مفتوح: {'✅ نعم' if is_open else '❌ لا'}")
        print(f"ساعات ممتدة: {'✅ نعم' if is_extended else '❌ لا'}")
        
        # الحصول على المراكز
        positions = client.get_positions()
        if not positions:
            print("❌ لا توجد مراكز للبيع")
            return
        
        # اختيار أول مركز للاختبار
        position = positions[0]
        symbol = position.symbol
        qty = float(position.qty)
        
        print(f"\n💼 المركز المختار للاختبار:")
        print(f"📈 {symbol}: {qty} سهم")
        
        # اختبار أمر بيع صغير (1% من المركز)
        test_qty = max(0.01, qty * 0.01)  # 1% أو 0.01 كحد أدنى
        
        print(f"\n🧪 اختبار بيع {test_qty:.6f} سهم من {symbol}")
        
        if is_extended:
            print("🌙 الساعات الممتدة نشطة - سيتم تحويل أمر السوق إلى limit")
            
            # تجربة أمر بيع في الساعات الممتدة
            try:
                order = client.place_order(
                    symbol=symbol,
                    qty=test_qty,
                    side="sell",
                    order_type="market",  # سيتم تحويله إلى limit
                    time_in_force="day",  # مطلوب للساعات الممتدة
                    extended_hours=True
                )
                
                print(f"✅ تم وضع الأمر بنجاح!")
                print(f"🆔 معرف الأمر: {order.id}")
                print(f"📊 نوع الأمر: {order.order_type}")
                print(f"⏰ صالح حتى: {order.time_in_force}")
                print(f"💰 السعر: {getattr(order, 'limit_price', 'سوق')}")
                print(f"🌙 ساعات ممتدة: {getattr(order, 'extended_hours', False)}")
                
                return order
                
            except Exception as e:
                print(f"❌ فشل في وضع الأمر: {e}")
                return None
        else:
            print("⏰ السوق مغلق والساعات الممتدة غير نشطة")
            print("💡 سيتم وضع أمر GTC للتنفيذ عند فتح السوق")
            
            try:
                order = client.place_order(
                    symbol=symbol,
                    qty=test_qty,
                    side="sell",
                    order_type="market",
                    time_in_force="gtc"
                )
                
                print(f"✅ تم وضع أمر GTC بنجاح!")
                print(f"🆔 معرف الأمر: {order.id}")
                
                return order
                
            except Exception as e:
                print(f"❌ فشل في وضع الأمر: {e}")
                return None
                
    except Exception as e:
        print(f"❌ خطأ في الاختبار: {e}")
        return None

def check_order_status(order_id):
    """فحص حالة الأمر"""
    try:
        client = AlpacaClient()
        order = client.get_order(order_id)
        
        print(f"\n📋 حالة الأمر {order_id}:")
        print(f"📊 الحالة: {order.status}")
        print(f"💰 الكمية المنفذة: {order.filled_qty}")
        print(f"💵 السعر المنفذ: {getattr(order, 'filled_avg_price', 'غير محدد')}")
        
        return order
        
    except Exception as e:
        print(f"❌ خطأ في فحص الأمر: {e}")
        return None

def main():
    """الدالة الرئيسية"""
    print("🤖 اختبار التنفيذ الفوري في الساعات الممتدة")
    print("=" * 60)
    
    # اختبار أمر البيع
    order = test_extended_hours_sell()
    
    if order:
        print(f"\n⏳ انتظار 5 ثوان لفحص حالة الأمر...")
        import time
        time.sleep(5)
        
        # فحص حالة الأمر
        check_order_status(order.id)
        
        print(f"\n📋 ملخص الاختبار:")
        print(f"✅ تم وضع الأمر بنجاح")
        print(f"🆔 معرف الأمر: {order.id}")
        print(f"💡 يمكنك مراقبة الأمر في واجهة Alpaca")
        
    else:
        print(f"\n❌ فشل الاختبار")
        print(f"💡 تحقق من الإعدادات والاتصال")

if __name__ == "__main__":
    main()