#!/usr/bin/env python3
"""
اختبار الاستراتيجية مباشرة
"""

import os
import sys
import time
import logging
from datetime import datetime

# إضافة مسار المشروع
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# تفعيل التسجيل
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

try:
    from src.alpaca_bot.config.settings import Settings
    from src.alpaca_bot.services.alpaca_client import AlpacaClient
    from src.alpaca_bot.strategies.safe_strategy import SafeStrategy
    
    print("=" * 60)
    print("🧪 اختبار الاستراتيجية مباشرة")
    print("=" * 60)
    
    # تحميل الإعدادات
    settings = Settings()
    print(f"✅ تم تحميل الإعدادات")
    
    # إنشاء عميل Alpaca
    alpaca_client = AlpacaClient()
    print(f"✅ تم إنشاء عميل Alpaca")
    
    # تخطي خدمة بيانات السوق لأنها غير موجودة
    print(f"⚠️ تخطي خدمة بيانات السوق")
    
    # إنشاء الاستراتيجية
    strategy = SafeStrategy(alpaca_client)
    print(f"✅ تم إنشاء الاستراتيجية الآمنة")
    
    # قائمة الأسهم للاختبار - قائمة موسعة
    symbols = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA',
        'JPM', 'JNJ', 'PG', 'KO', 'PEP', 'WMT', 'HD', 'DIS',
        'VZ', 'T', 'INTC', 'IBM', 'ORCL', 'CRM', 'ADBE'
    ]
    
    print(f"\n🔍 اختبار التحليل للأسهم: {symbols}")
    print("-" * 60)
    
    for symbol in symbols:
        try:
            print(f"\n📊 تحليل {symbol}:")
            
            # جلب بيانات السهم
            stock_data = strategy.analyze_symbol(symbol)
            
            if stock_data:
                print(f"   ✅ تم جلب البيانات - السعر: ${stock_data.current_price:.2f}")
                
                # تحليل الإشارات
                signals = strategy.generate_signals(stock_data)
                
                if signals:
                    print(f"   📈 تم العثور على {len(signals)} إشارة:")
                    for signal in signals:
                        print(f"      - {signal.action} {signal.symbol} - الثقة: {signal.confidence:.2f} - السبب: {signal.reason}")
                        
                        # محاولة تنفيذ الإشارة (تجريبي)
                        print(f"      🔄 محاولة تنفيذ الإشارة...")
                        success = strategy.execute_signal(signal)
                        print(f"      {'✅ نجح' if success else '❌ فشل'} التنفيذ")
                else:
                    print(f"   ⚪ لا توجد إشارات تداول")
            else:
                print(f"   ❌ فشل في جلب البيانات")
                
        except Exception as e:
            print(f"   ❌ خطأ في تحليل {symbol}: {e}")
    
    # عرض حالة الاستراتيجية النهائية
    print(f"\n📊 حالة الاستراتيجية النهائية:")
    print("-" * 40)
    status = strategy.get_status()
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    print(f"\n🚦 إمكانية التداول: {'✅ نعم' if strategy._can_trade() else '❌ لا'}")
    
except Exception as e:
    print(f"❌ خطأ عام: {e}")
    import traceback
    traceback.print_exc()