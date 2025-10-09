#!/usr/bin/env python3
"""
سكريبت لفحص حالة الاستراتيجية الحالية
"""

import os
import sys
from datetime import datetime

# إضافة مسار المشروع
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from src.alpaca_bot.config.settings import Settings
    from src.alpaca_bot.services.alpaca_client import AlpacaClient
    from src.alpaca_bot.strategies.safe_strategy import SafeStrategy
    
    print("=" * 60)
    print("🔍 فحص حالة الاستراتيجية")
    print("=" * 60)
    
    # تحميل الإعدادات
    settings = Settings()
    print(f"📊 إعدادات محملة من: {settings}")
    
    # إنشاء عميل Alpaca
    alpaca_client = AlpacaClient()
    print(f"🔗 عميل Alpaca: متصل")
    
    # إنشاء الاستراتيجية
    strategy = SafeStrategy(alpaca_client)
    print(f"🛡️ الاستراتيجية الآمنة: مُحملة")
    
    # عرض الحالة
    status = strategy.get_status()
    print("\n📈 حالة الاستراتيجية:")
    print("-" * 40)
    
    for key, value in status.items():
        if key == 'daily_trades':
            print(f"   📊 الصفقات اليومية: {value}/{strategy.max_daily_trades}")
        elif key == 'daily_pnl':
            print(f"   💰 الربح/الخسارة اليومية: ${value:.2f}")
        elif key == 'max_daily_loss':
            print(f"   🛑 الحد الأقصى للخسارة: ${value:.2f}")
        elif key == 'position_size':
            print(f"   📏 حجم المركز: ${value:.2f}")
        else:
            print(f"   {key}: {value}")
    
    # فحص إمكانية التداول
    can_trade = strategy._can_trade()
    print(f"\n🚦 إمكانية التداول: {'✅ نعم' if can_trade else '❌ لا'}")
    
    if not can_trade:
        print("\n🚨 أسباب منع التداول:")
        if strategy.daily_trades_count >= strategy.max_daily_trades:
            print(f"   - وصلنا للحد الأقصى من الصفقات: {strategy.daily_trades_count}/{strategy.max_daily_trades}")
        if strategy.daily_pnl <= -strategy.max_daily_loss:
            print(f"   - وصلنا للحد الأقصى من الخسائر: ${strategy.daily_pnl:.2f}/${strategy.max_daily_loss:.2f}")
    
    print("\n💡 الحلول المقترحة:")
    if strategy.daily_trades_count >= strategy.max_daily_trades:
        print("   1. زيادة MAX_DAILY_TRADES في ملف .env")
        print("   2. انتظار حتى اليوم التالي لإعادة تعيين العداد")
        print("   3. إعادة تشغيل البرنامج لإعادة تعيين العداد يدوياً")
    
    if strategy.daily_pnl <= -strategy.max_daily_loss:
        print("   1. زيادة MAX_DAILY_LOSS في ملف .env")
        print("   2. مراجعة الاستراتيجية لتقليل المخاطر")
    
except Exception as e:
    print(f"❌ خطأ: {e}")
    import traceback
    traceback.print_exc()