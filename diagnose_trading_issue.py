#!/usr/bin/env python3
"""
سكريبت تشخيص مشاكل التداول
Trading Issues Diagnostic Script
"""

import os
import sys
from datetime import datetime, timezone
import pytz

# إضافة مسار المشروع
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from alpaca_bot.config.settings import settings
from alpaca_bot.services.alpaca_client import AlpacaClient
from alpaca_bot.utils.market_utils import MarketHours

def check_market_status():
    """فحص حالة السوق"""
    print("=" * 50)
    print("🔍 فحص حالة السوق")
    print("=" * 50)
    
    try:
        # الوقت الحالي
        now = datetime.now(pytz.timezone('America/New_York'))
        print(f"⏰ الوقت الحالي (ET): {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        # حالة السوق
        market_hours = MarketHours()
        is_open = market_hours.is_market_open(
            weekend_trading_enabled=settings.weekend_trading_enabled,
            extended_hours_enabled=settings.extended_hours_enabled
        )
        
        status = market_hours.get_market_status(
            weekend_trading_enabled=settings.weekend_trading_enabled,
            extended_hours_enabled=settings.extended_hours_enabled
        )
        
        print(f"📈 حالة السوق: {status}")
        print(f"🟢 السوق مفتوح: {'نعم' if is_open else 'لا'}")
        
        # الساعات الممتدة
        is_extended = MarketHours.is_extended_hours()
        print(f"🌙 الساعات الممتدة: {'نعم' if is_extended else 'لا'}")
        
        return is_open, is_extended
        
    except Exception as e:
        print(f"❌ خطأ في فحص حالة السوق: {e}")
        return False, False

def check_alpaca_connection():
    """فحص الاتصال بـ Alpaca"""
    print("\n" + "=" * 50)
    print("🔗 فحص الاتصال بـ Alpaca")
    print("=" * 50)
    
    try:
        client = AlpacaClient()
        
        # فحص الحساب
        account = client.get_account()
        print(f"💰 رصيد الحساب: ${float(account.cash):,.2f}")
        print(f"📊 قوة الشراء: ${float(account.buying_power):,.2f}")
        print(f"🏦 نوع الحساب: {'ورقي' if account.account_blocked else 'حقيقي'}")
        
        # فحص المراكز
        positions = client.get_positions()
        print(f"📍 عدد المراكز المفتوحة: {len(positions)}")
        
        # فحص الأوامر المعلقة
        orders = client.get_orders(status='open')
        print(f"📋 عدد الأوامر المعلقة: {len(orders)}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في الاتصال بـ Alpaca: {e}")
        return False

def check_recent_orders():
    """فحص الأوامر الأخيرة"""
    print("\n" + "=" * 50)
    print("📋 فحص الأوامر الأخيرة")
    print("=" * 50)
    
    try:
        client = AlpacaClient()
        
        # الحصول على آخر 10 أوامر
        orders = client.get_orders(status='all', limit=10)
        
        if not orders:
            print("📭 لا توجد أوامر")
            return
        
        print(f"📊 آخر {len(orders)} أوامر:")
        print("-" * 80)
        print(f"{'الرمز':<8} {'النوع':<6} {'الكمية':<10} {'الحالة':<12} {'الوقت':<20}")
        print("-" * 80)
        
        for order in orders:
            symbol = order.symbol
            side = order.side
            qty = order.qty
            status = order.status
            created_at = order.created_at.strftime('%H:%M:%S')
            
            print(f"{symbol:<8} {side:<6} {qty:<10} {status:<12} {created_at:<20}")
        
        # إحصائيات الحالات
        status_counts = {}
        for order in orders:
            status = order.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("\n📊 إحصائيات الحالات:")
        for status, count in status_counts.items():
            print(f"   {status}: {count}")
            
    except Exception as e:
        print(f"❌ خطأ في فحص الأوامر: {e}")

def check_settings():
    """فحص الإعدادات"""
    print("\n" + "=" * 50)
    print("⚙️ فحص الإعدادات")
    print("=" * 50)
    
    print(f"💵 حجم المركز الافتراضي: ${settings.default_position_size}")
    print(f"🛑 نسبة وقف الخسارة: {settings.stop_loss_percentage * 100:.1f}%")
    print(f"🎯 نسبة جني الأرباح: {settings.take_profit_percentage * 100:.1f}%")
    print(f"📈 الحد الأقصى للخسارة اليومية: ${getattr(settings, 'max_daily_loss', 'غير محدد')}")
    print(f"🔢 الحد الأقصى للصفقات اليومية: {getattr(settings, 'max_daily_trades', 'غير محدد')}")
    print(f"🌙 الساعات الممتدة مفعلة: {'نعم' if settings.extended_hours_enabled else 'لا'}")
    print(f"📅 تداول نهاية الأسبوع مفعل: {'نعم' if settings.weekend_trading_enabled else 'لا'}")

def suggest_solutions(is_market_open, is_extended, alpaca_connected):
    """اقتراح الحلول"""
    print("\n" + "=" * 50)
    print("💡 اقتراحات الحلول")
    print("=" * 50)
    
    if not alpaca_connected:
        print("🔧 مشكلة الاتصال بـ Alpaca:")
        print("   - تحقق من مفاتيح API")
        print("   - تحقق من الاتصال بالإنترنت")
        print("   - تحقق من حالة خدمة Alpaca")
    
    if not is_market_open and not is_extended:
        print("🕐 السوق مغلق:")
        print("   - انتظر حتى فتح السوق")
        print("   - فعّل الساعات الممتدة إذا كنت تريد التداول الآن")
        print("   - تحقق من أوقات السوق")
    
    if is_extended:
        print("🌙 تداول الساعات الممتدة:")
        print("   - تأكد من تفعيل extended_hours=True في الأوامر")
        print("   - استخدم أوامر محدودة بدلاً من أوامر السوق")
        print("   - كن حذراً من السيولة المنخفضة")
    
    print("\n🔧 حلول عامة:")
    print("   - إعادة تشغيل البرنامج")
    print("   - فحص ملف السجلات للأخطاء")
    print("   - تحديث الإعدادات إذا لزم الأمر")

def main():
    """الدالة الرئيسية"""
    print("🚀 بدء تشخيص مشاكل التداول...")
    
    # فحص حالة السوق
    is_market_open, is_extended = check_market_status()
    
    # فحص الاتصال بـ Alpaca
    alpaca_connected = check_alpaca_connection()
    
    # فحص الأوامر الأخيرة
    if alpaca_connected:
        check_recent_orders()
    
    # فحص الإعدادات
    check_settings()
    
    # اقتراح الحلول
    suggest_solutions(is_market_open, is_extended, alpaca_connected)
    
    print("\n✅ انتهى التشخيص")

if __name__ == "__main__":
    main()