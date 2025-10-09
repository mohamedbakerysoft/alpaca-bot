#!/usr/bin/env python3
"""
سكريبت لفحص عدد الصفقات المنفذة اليوم
"""

import os
import sys
from datetime import datetime, timedelta

# إضافة مسار المشروع
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # إذا لم تكن dotenv متوفرة، نحاول تحميل الإعدادات من src
    try:
        from src.alpaca_bot.config.settings import Settings
        settings = Settings()
    except ImportError:
        print("❌ لا يمكن تحميل الإعدادات")
        sys.exit(1)

try:
    import alpaca_trade_api as tradeapi
except ImportError:
    print("❌ لا يمكن استيراد alpaca_trade_api")
    sys.exit(1)

def check_daily_trades():
    """فحص عدد الصفقات المنفذة اليوم"""
    
    # إعداد Alpaca API
    api = tradeapi.REST(
        os.getenv('ALPACA_API_KEY'),
        os.getenv('ALPACA_SECRET_KEY'),
        base_url=os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets'),
        api_version='v2'
    )
    
    # تاريخ اليوم
    today = datetime.now().date()
    start_time = datetime.combine(today, datetime.min.time())
    end_time = datetime.combine(today, datetime.max.time())
    
    print("=" * 60)
    print("📊 فحص الصفقات اليومية")
    print("=" * 60)
    print(f"📅 التاريخ: {today}")
    print(f"⏰ من: {start_time.strftime('%H:%M:%S')}")
    print(f"⏰ إلى: {end_time.strftime('%H:%M:%S')}")
    print()
    
    try:
        # جلب الأوامر لليوم
        orders = api.list_orders(
            status='all',
            after=start_time.isoformat(),
            until=end_time.isoformat(),
            limit=500
        )
        
        # تصنيف الأوامر
        filled_orders = []
        canceled_orders = []
        pending_orders = []
        
        for order in orders:
            if order.status == 'filled':
                filled_orders.append(order)
            elif order.status == 'canceled':
                canceled_orders.append(order)
            else:
                pending_orders.append(order)
        
        print(f"📈 إجمالي الأوامر: {len(orders)}")
        print(f"✅ أوامر منفذة: {len(filled_orders)}")
        print(f"❌ أوامر ملغاة: {len(canceled_orders)}")
        print(f"⏳ أوامر معلقة: {len(pending_orders)}")
        print()
        
        # عرض الأوامر المنفذة
        if filled_orders:
            print("✅ الأوامر المنفذة:")
            print("-" * 80)
            for order in filled_orders:
                order_time = datetime.fromisoformat(order.filled_at.replace('Z', '+00:00')).strftime('%H:%M:%S')
                print(f"   {order.symbol} | {order.side} | {order.qty} | ${order.filled_avg_price} | {order_time}")
        
        # عرض آخر الأوامر الملغاة
        if canceled_orders:
            print("\n❌ آخر 5 أوامر ملغاة:")
            print("-" * 80)
            for order in canceled_orders[:5]:
                order_time = datetime.fromisoformat(order.created_at.replace('Z', '+00:00')).strftime('%H:%M:%S')
                print(f"   {order.symbol} | {order.side} | {order.qty} | ${order.limit_price or 'market'} | {order_time}")
        
        print()
        
        # فحص الحد الأقصى
        max_daily_trades = int(os.getenv('MAX_DAILY_TRADES', 10))
        print(f"🔢 الحد الأقصى للصفقات اليومية: {max_daily_trades}")
        print(f"📊 الصفقات المنفذة اليوم: {len(filled_orders)}")
        
        if len(filled_orders) >= max_daily_trades:
            print("🚨 تحذير: تم الوصول للحد الأقصى للصفقات اليومية!")
            print("💡 هذا قد يكون سبب إلغاء الأوامر الجديدة")
        else:
            remaining = max_daily_trades - len(filled_orders)
            print(f"✅ متبقي: {remaining} صفقة")
        
        print()
        
        # فحص أسباب الإلغاء
        if canceled_orders:
            print("🔍 تحليل أسباب الإلغاء:")
            cancel_reasons = {}
            for order in canceled_orders:
                # محاولة استخراج سبب الإلغاء من الوقت
                created_time = datetime.fromisoformat(order.created_at.replace('Z', '+00:00'))
                canceled_time = datetime.fromisoformat(order.canceled_at.replace('Z', '+00:00')) if order.canceled_at else None
                
                if canceled_time:
                    duration = (canceled_time - created_time).total_seconds()
                    if duration < 60:
                        reason = "إلغاء سريع (أقل من دقيقة)"
                    elif duration < 300:
                        reason = "إلغاء متوسط (1-5 دقائق)"
                    else:
                        reason = "إلغاء بطيء (أكثر من 5 دقائق)"
                else:
                    reason = "سبب غير محدد"
                
                cancel_reasons[reason] = cancel_reasons.get(reason, 0) + 1
            
            for reason, count in cancel_reasons.items():
                print(f"   - {reason}: {count} أمر")
        
    except Exception as e:
        print(f"❌ خطأ في جلب البيانات: {e}")
        return False
    
    return True

if __name__ == "__main__":
    check_daily_trades()