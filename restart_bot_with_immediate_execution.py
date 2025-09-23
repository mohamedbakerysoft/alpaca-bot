#!/usr/bin/env python3
"""
إعادة تشغيل البوت مع إعدادات التنفيذ الفوري
Restart Bot with Immediate Execution Settings
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def check_settings():
    """فحص الإعدادات الحالية"""
    print("🔍 فحص الإعدادات الحالية...")
    
    # فحص ملف .env
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, 'r') as f:
            content = f.read()
            
        settings_to_check = {
            'EXTENDED_HOURS_ENABLED': 'True',
            'TRADING_MODE': 'smart'
        }
        
        for setting, expected in settings_to_check.items():
            if f"{setting}={expected}" in content:
                print(f"✅ {setting} = {expected}")
            else:
                print(f"❌ {setting} غير مضبوط بشكل صحيح")
                return False
    else:
        print("❌ ملف .env غير موجود")
        return False
    
    return True

def restart_bot():
    """إعادة تشغيل البوت"""
    print("\n🔄 إعادة تشغيل البوت...")
    
    # إيقاف أي عمليات تشغيل سابقة
    try:
        subprocess.run(["pkill", "-f", "main.py"], check=False)
        subprocess.run(["pkill", "-f", "alpaca_bot"], check=False)
        time.sleep(2)
        print("✅ تم إيقاف العمليات السابقة")
    except Exception as e:
        print(f"⚠️ تحذير: {e}")
    
    # تشغيل البوت
    try:
        print("🚀 تشغيل البوت مع الإعدادات الجديدة...")
        
        # تشغيل البوت في الخلفية
        process = subprocess.Popen([
            sys.executable, "-m", "alpaca_bot.main"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # انتظار قليل للتأكد من بدء التشغيل
        time.sleep(3)
        
        # فحص حالة العملية
        if process.poll() is None:
            print("✅ تم تشغيل البوت بنجاح!")
            print(f"🆔 معرف العملية: {process.pid}")
            return True
        else:
            stdout, stderr = process.communicate()
            print(f"❌ فشل في تشغيل البوت:")
            print(f"خطأ: {stderr.decode()}")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في تشغيل البوت: {e}")
        return False

def test_immediate_execution():
    """اختبار التنفيذ الفوري"""
    print("\n🧪 اختبار التنفيذ الفوري...")
    
    try:
        result = subprocess.run([
            sys.executable, "test_immediate_sell.py"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ اختبار التنفيذ الفوري نجح!")
            print("\n📊 نتائج الاختبار:")
            print(result.stdout)
        else:
            print("❌ فشل اختبار التنفيذ الفوري:")
            print(result.stderr)
            
    except subprocess.TimeoutExpired:
        print("⏰ انتهت مهلة الاختبار")
    except Exception as e:
        print(f"❌ خطأ في الاختبار: {e}")

def main():
    """الدالة الرئيسية"""
    print("🤖 إعادة تشغيل البوت مع إعدادات التنفيذ الفوري")
    print("=" * 50)
    
    # فحص الإعدادات
    if not check_settings():
        print("\n❌ الإعدادات غير صحيحة. يرجى تشغيل enable_immediate_execution.py أولاً")
        return
    
    # إعادة تشغيل البوت
    if restart_bot():
        print("\n✅ تم إعادة تشغيل البوت بنجاح!")
        
        # اختبار التنفيذ الفوري
        test_immediate_execution()
        
        print("\n📋 الخطوات التالية:")
        print("1. راقب سجلات البوت للتأكد من عمله بشكل صحيح")
        print("2. اختبر أوامر البيع للتأكد من التنفيذ الفوري")
        print("3. راجع الأوامر في واجهة Alpaca")
        
        print("\n🔧 أوامر مفيدة:")
        print("- لمراقبة السجلات: tail -f logs/alpaca_bot.log")
        print("- لإيقاف البوت: pkill -f alpaca_bot")
        print("- لاختبار التنفيذ: python test_immediate_sell.py")
        
    else:
        print("\n❌ فشل في إعادة تشغيل البوت")

if __name__ == "__main__":
    main()