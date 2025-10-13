#!/usr/bin/env python3

import sys
import os
sys.path.append('src')

from alpaca_bot.services.alpaca_client import AlpacaClient
from alpaca_bot.strategies.safe_strategy import SafeStrategy

def check_trading_status():
    print("🔍 فحص حالة التداول...")
    
    try:
        # إنشاء العميل
        client = AlpacaClient()
        strategy = SafeStrategy(client)
        
        # الحصول على المراكز الحالية
        positions = client.get_positions()
        print(f"\n📊 عدد المراكز الحالية: {len(positions)}")
        
        for pos in positions:
            symbol = pos.symbol
            qty = float(pos.qty)
            market_value = float(pos.market_value)
            unrealized_pl = float(pos.unrealized_pl)
            unrealized_plpc = float(pos.unrealized_plpc) * 100
            
            print(f"\n🔸 {symbol}:")
            print(f"   الكمية: {qty}")
            print(f"   القيمة: ${market_value:.2f}")
            print(f"   الربح/الخسارة: ${unrealized_pl:.2f} ({unrealized_plpc:.2f}%)")
            
            # فحص إذا كان يجب البيع
            if unrealized_plpc >= 1.5:  # 1.5% profit target
                print(f"   ⚠️ يجب البيع! وصل للهدف {unrealized_plpc:.2f}%")
            elif unrealized_plpc <= -2.0:  # 2% stop loss
                print(f"   🛑 يجب البيع! وصل لحد الخسارة {unrealized_plpc:.2f}%")
            else:
                print(f"   ✅ ضمن النطاق المقبول")
        
        # فحص حالة الاستراتيجية
        print(f"\n🤖 حالة الاستراتيجية:")
        print(f"   المراكز النشطة: {len(getattr(strategy, 'active_positions', {}))}")
        print(f"   آخر فحص: {getattr(strategy, 'last_check_time', 'غير محدد')}")
        
    except Exception as e:
        print(f"❌ خطأ: {e}")

if __name__ == "__main__":
    check_trading_status()
