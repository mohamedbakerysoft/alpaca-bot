#!/usr/bin/env python3
"""
مراقب الأوامر في الوقت الفعلي
===============================

هذا السكريبت يراقب أوامر البيع في الوقت الفعلي ويعرض إحصائيات مفصلة
"""

import sys
import os
import time
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Optional
import json

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from alpaca_bot.clients.alpaca_client import AlpacaClient


class OrderMonitor:
    """مراقب الأوامر في الوقت الفعلي."""
    
    def __init__(self):
        """تهيئة مراقب الأوامر."""
        self.alpaca_client = AlpacaClient()
        self.order_history = deque(maxlen=1000)  # آخر 1000 أمر
        self.symbol_stats = defaultdict(lambda: {
            'total_orders': 0,
            'executed': 0,
            'cancelled': 0,
            'pending': 0,
            'avg_execution_time': 0,
            'last_order_time': None
        })
        self.start_time = datetime.now()
        
    def get_order_status_emoji(self, status: str) -> str:
        """الحصول على رمز تعبيري لحالة الأمر."""
        status_emojis = {
            'new': '🆕',
            'pending_new': '⏳',
            'accepted': '✅',
            'filled': '💰',
            'done_for_day': '📅',
            'cancelled': '❌',
            'expired': '⏰',
            'replaced': '🔄',
            'pending_cancel': '⏸️',
            'pending_replace': '🔄',
            'rejected': '🚫'
        }
        return status_emojis.get(status.lower(), '❓')
    
    def format_duration(self, seconds: float) -> str:
        """تنسيق المدة الزمنية."""
        if seconds < 60:
            return f"{seconds:.1f}ث"
        elif seconds < 3600:
            return f"{seconds/60:.1f}د"
        else:
            return f"{seconds/3600:.1f}س"
    
    def get_recent_orders(self, hours: int = 1) -> List:
        """الحصول على الأوامر الحديثة."""
        try:
            # Get orders from the last few hours
            orders = self.alpaca_client.get_orders(
                status='all',
                limit=500,
                after=(datetime.now() - timedelta(hours=hours)).isoformat()
            )
            
            # Filter for sell orders only
            sell_orders = [order for order in orders if order.side == 'sell']
            return sell_orders
            
        except Exception as e:
            print(f"❌ خطأ في جلب الأوامر: {e}")
            return []
    
    def analyze_order(self, order) -> Dict:
        """تحليل أمر واحد."""
        try:
            # Handle different datetime formats
            created_at = order.created_at
            if hasattr(created_at, 'timestamp'):
                created_time = created_at
            else:
                created_time = datetime.fromisoformat(str(created_at).replace('Z', '+00:00'))
            
            # Calculate order age
            current_time = datetime.now()
            age = current_time - created_time.replace(tzinfo=None)
            age_seconds = age.total_seconds()
            
            # Get filled time if available
            filled_time = None
            execution_time = None
            if hasattr(order, 'filled_at') and order.filled_at:
                try:
                    if hasattr(order.filled_at, 'timestamp'):
                        filled_time = order.filled_at
                    else:
                        filled_time = datetime.fromisoformat(str(order.filled_at).replace('Z', '+00:00'))
                    execution_time = (filled_time - created_time).total_seconds()
                except:
                    pass
            
            return {
                'id': order.id,
                'symbol': order.symbol,
                'qty': float(order.qty),
                'status': order.status,
                'order_type': order.order_type,
                'created_at': created_time,
                'filled_at': filled_time,
                'age_seconds': age_seconds,
                'execution_time': execution_time,
                'price': getattr(order, 'limit_price', None) or getattr(order, 'filled_avg_price', None)
            }
            
        except Exception as e:
            print(f"❌ خطأ في تحليل الأمر {order.id}: {e}")
            return None
    
    def update_stats(self, order_data: Dict):
        """تحديث إحصائيات الرمز."""
        symbol = order_data['symbol']
        status = order_data['status']
        
        stats = self.symbol_stats[symbol]
        stats['total_orders'] += 1
        stats['last_order_time'] = order_data['created_at']
        
        if status in ['filled', 'done_for_day']:
            stats['executed'] += 1
            if order_data['execution_time']:
                # Update average execution time
                current_avg = stats['avg_execution_time']
                executed_count = stats['executed']
                stats['avg_execution_time'] = (current_avg * (executed_count - 1) + order_data['execution_time']) / executed_count
        elif status in ['cancelled', 'expired', 'rejected']:
            stats['cancelled'] += 1
        elif status in ['new', 'pending_new', 'accepted']:
            stats['pending'] += 1
    
    def print_header(self):
        """طباعة رأس التقرير."""
        print("\n" + "="*80)
        print("📊 مراقب أوامر البيع في الوقت الفعلي")
        print("="*80)
        print(f"🕐 وقت البدء: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🕐 الوقت الحالي: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
    
    def print_summary(self, orders: List[Dict]):
        """طباعة ملخص الأوامر."""
        if not orders:
            print("📭 لا توجد أوامر بيع حديثة")
            return
        
        total = len(orders)
        executed = len([o for o in orders if o['status'] in ['filled', 'done_for_day']])
        cancelled = len([o for o in orders if o['status'] in ['cancelled', 'expired', 'rejected']])
        pending = len([o for o in orders if o['status'] in ['new', 'pending_new', 'accepted']])
        
        print(f"\n📈 ملخص الأوامر (آخر ساعة):")
        print(f"   📊 إجمالي الأوامر: {total}")
        print(f"   💰 تم التنفيذ: {executed} ({executed/total*100:.1f}%)")
        print(f"   ❌ تم الإلغاء: {cancelled} ({cancelled/total*100:.1f}%)")
        print(f"   ⏳ معلق: {pending} ({pending/total*100:.1f}%)")
        
        if executed > 0:
            execution_times = [o['execution_time'] for o in orders if o['execution_time']]
            if execution_times:
                avg_execution = sum(execution_times) / len(execution_times)
                print(f"   ⚡ متوسط وقت التنفيذ: {self.format_duration(avg_execution)}")
    
    def print_recent_orders(self, orders: List[Dict], limit: int = 10):
        """طباعة الأوامر الحديثة."""
        print(f"\n🔄 آخر {min(limit, len(orders))} أوامر:")
        print("-" * 80)
        
        for order in orders[:limit]:
            emoji = self.get_order_status_emoji(order['status'])
            age_str = self.format_duration(order['age_seconds'])
            
            price_str = ""
            if order['price']:
                price_str = f" @ ${float(order['price']):.2f}"
            
            exec_time_str = ""
            if order['execution_time']:
                exec_time_str = f" (تنفيذ: {self.format_duration(order['execution_time'])})"
            
            print(f"{emoji} {order['symbol']} | {order['qty']} سهم{price_str} | {order['status']} | عمر: {age_str}{exec_time_str}")
    
    def print_symbol_stats(self, limit: int = 10):
        """طباعة إحصائيات الرموز."""
        if not self.symbol_stats:
            return
        
        print(f"\n📊 إحصائيات الرموز (أفضل {limit}):")
        print("-" * 80)
        
        # Sort by total orders
        sorted_symbols = sorted(
            self.symbol_stats.items(),
            key=lambda x: x[1]['total_orders'],
            reverse=True
        )
        
        for symbol, stats in sorted_symbols[:limit]:
            total = stats['total_orders']
            executed = stats['executed']
            cancelled = stats['cancelled']
            pending = stats['pending']
            
            exec_rate = executed / total * 100 if total > 0 else 0
            cancel_rate = cancelled / total * 100 if total > 0 else 0
            
            avg_exec_str = ""
            if stats['avg_execution_time'] > 0:
                avg_exec_str = f" | متوسط التنفيذ: {self.format_duration(stats['avg_execution_time'])}"
            
            print(f"📈 {symbol}: {total} أوامر | تنفيذ: {exec_rate:.1f}% | إلغاء: {cancel_rate:.1f}%{avg_exec_str}")
    
    def monitor_once(self):
        """مراقبة واحدة."""
        orders = self.get_recent_orders(hours=1)
        analyzed_orders = []
        
        for order in orders:
            order_data = self.analyze_order(order)
            if order_data:
                analyzed_orders.append(order_data)
                self.update_stats(order_data)
        
        # Sort by creation time (newest first)
        analyzed_orders.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Clear screen and print report
        os.system('clear' if os.name == 'posix' else 'cls')
        
        self.print_header()
        self.print_summary(analyzed_orders)
        self.print_recent_orders(analyzed_orders)
        self.print_symbol_stats()
        
        print(f"\n🔄 التحديث التالي خلال 30 ثانية...")
        print("اضغط Ctrl+C للخروج")
    
    def run(self):
        """تشغيل المراقب."""
        print("🚀 بدء مراقب الأوامر...")
        
        try:
            while True:
                self.monitor_once()
                time.sleep(30)  # Update every 30 seconds
                
        except KeyboardInterrupt:
            print("\n\n👋 تم إيقاف المراقب بواسطة المستخدم")
        except Exception as e:
            print(f"\n❌ خطأ في المراقب: {e}")


if __name__ == "__main__":
    monitor = OrderMonitor()
    monitor.run()