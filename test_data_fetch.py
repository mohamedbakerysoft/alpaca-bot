#!/usr/bin/env python3
"""
اختبار جلب البيانات من Alpaca
"""

import sys
import os
from datetime import datetime, timedelta

# إضافة مسار المشروع
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.alpaca_bot.services.alpaca_client import AlpacaClient
from src.alpaca_bot.config.settings import settings

def test_data_fetch():
    """اختبار جلب البيانات"""
    print("🔍 اختبار جلب البيانات من Alpaca")
    print("=" * 50)
    
    try:
        # إنشاء العميل
        client = AlpacaClient()
        print("✅ تم إنشاء عميل Alpaca")
        
        # اختبار الاتصال
        account = client.get_account()
        if account:
            print(f"✅ الاتصال ناجح - الحساب: {account.account_number}")
        else:
            print("❌ فشل في الاتصال")
            return
        
        # اختبار حالة السوق
        try:
            clock = client.api.get_clock()
            if clock:
                print(f"🕐 وقت السوق: {clock.timestamp}")
                print(f"📈 السوق مفتوح: {'نعم' if clock.is_open else 'لا'}")
        except Exception as e:
            print(f"⚠️ لا يمكن الحصول على حالة السوق: {e}")
        
        # اختبار جلب البيانات
        symbols = ['AAPL', 'MSFT', 'NVDA']
        
        for symbol in symbols:
            print(f"\n📊 اختبار {symbol}:")
            
            try:
                # طريقة 1: جلب البيانات مع فترة زمنية
                end_time = datetime.now()
                start_time = end_time - timedelta(days=1)
                
                bars = client.get_bars(
                    symbol=symbol,
                    timeframe='1Min',
                    start=start_time,
                    end=end_time,
                    limit=10
                )
                
                if bars is not None and not bars.empty:
                    print(f"   ✅ تم جلب {len(bars)} شريط")
                    print(f"   💰 آخر سعر: ${bars.iloc[-1]['close']:.2f}")
                else:
                    print("   ❌ لا توجد بيانات")
                    
                # طريقة 2: جلب آخر سعر
                quote = client.get_latest_quote(symbol)
                if quote:
                    print(f"   📈 آخر عرض: ${quote.bid:.2f}")
                    print(f"   📉 آخر طلب: ${quote.ask:.2f}")
                else:
                    print("   ❌ لا يوجد سعر حالي")
                    
            except Exception as e:
                print(f"   ❌ خطأ: {e}")
        
        print("\n" + "=" * 50)
        print("✅ انتهى الاختبار")
        
    except Exception as e:
        print(f"❌ خطأ عام: {e}")

if __name__ == "__main__":
    test_data_fetch()