#!/usr/bin/env python3
"""
تفعيل التنفيذ الفوري للأوامر
Enable Immediate Order Execution
"""

import os
import sys

def enable_immediate_execution():
    """تفعيل التنفيذ الفوري للأوامر"""
    
    print("🚀 تفعيل التنفيذ الفوري للأوامر")
    print("=" * 40)
    
    # 1. تحديث متغيرات البيئة
    print("\n1️⃣ تحديث متغيرات البيئة...")
    
    env_file = ".env"
    env_updates = {
        "EXTENDED_HOURS_ENABLED": "True",
        "TRADING_MODE": "smart"
    }
    
    # قراءة ملف .env الحالي
    env_content = ""
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            env_content = f.read()
    
    # تحديث أو إضافة المتغيرات
    for key, value in env_updates.items():
        if f"{key}=" in env_content:
            # تحديث القيمة الموجودة
            lines = env_content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith(f"{key}="):
                    lines[i] = f"{key}={value}"
                    break
            env_content = '\n'.join(lines)
        else:
            # إضافة متغير جديد
            env_content += f"\n{key}={value}"
    
    # كتابة ملف .env المحدث
    with open(env_file, 'w') as f:
        f.write(env_content.strip() + '\n')
    
    print("   ✅ تم تحديث متغيرات البيئة")
    
    # 2. عرض الإعدادات الجديدة
    print("\n2️⃣ الإعدادات الجديدة:")
    print("   🌙 التداول في الساعات الممتدة: مفعل")
    print("   ⚡ نوع time_in_force: GTC (صالح حتى الإلغاء)")
    print("   🎯 نوع الأمر: Market (سوق)")
    print("   🔄 إعادة تشغيل تلقائي: مفعل")
    
    # 3. إرشادات الاستخدام
    print("\n3️⃣ كيفية الاستخدام:")
    print("   📝 أعد تشغيل البوت لتطبيق الإعدادات الجديدة")
    print("   🔍 استخدم order_monitor.py لمراقبة التنفيذ")
    print("   ⚙️ يمكنك تخصيص الإعدادات في immediate_execution_settings.py")
    
    # 4. اختبار الإعدادات
    print("\n4️⃣ اختبار الإعدادات:")
    print("   🧪 تشغيل: python test_immediate_sell.py")
    print("   📊 مراقبة: python order_monitor.py")
    
    print("\n✅ تم تفعيل التنفيذ الفوري بنجاح!")
    print("\n⚠️  ملاحظة: تأكد من أن حسابك في Alpaca يدعم التداول في الساعات الممتدة")

if __name__ == "__main__":
    enable_immediate_execution()