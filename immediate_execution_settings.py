"""
إعدادات التنفيذ الفوري للأوامر
Immediate Order Execution Settings
"""

# ===== إعدادات التنفيذ الفوري =====
# Immediate Execution Settings

# استخدام أوامر السوق للبيع السريع (يتم تحويلها لـ limit في الساعات الممتدة)
USE_MARKET_ORDERS_FOR_SELL = True

# استخدام التداول في الساعات الممتدة
EXTENDED_HOURS_TRADING = True

# نوع time_in_force للتنفيذ السريع ('day' مطلوب للساعات الممتدة في Alpaca)
IMMEDIATE_TIME_IN_FORCE = "day"  # 'day' مطلوب للساعات الممتدة في Alpaca

# إعدادات التنفيذ حسب حالة السوق
IMMEDIATE_EXECUTION_CONFIG = {
    "market_open": {
        "order_type": "market",
        "time_in_force": "day",
        "extended_hours": False
    },
    "extended_hours": {
        "order_type": "market",  # سيتم تحويله لـ limit تلقائياً في alpaca_client
        "time_in_force": "day",  # مطلوب للساعات الممتدة
        "extended_hours": True
    },
    "market_closed": {
        "order_type": "limit",
        "time_in_force": "gtc",
        "extended_hours": False   # لا يمكن التنفيذ عند إغلاق السوق
    }
}

# ===== إعدادات تحسين التنفيذ =====
# Execution Optimization Settings

# الحد الأقصى لانتظار تنفيذ الأمر (بالثواني)
MAX_ORDER_WAIT_TIME = 30

# إعادة المحاولة للأوامر غير المنفذة
RETRY_FAILED_ORDERS = True
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 5

# إلغاء الأوامر القديمة تلقائياً
AUTO_CANCEL_OLD_ORDERS = True
MAX_ORDER_AGE_MINUTES = 2  # إلغاء الأوامر الأقدم من دقيقتين

# ===== إعدادات مراقبة التنفيذ =====
# Execution Monitoring Settings

# تسجيل تفصيلي لعملية التنفيذ
DETAILED_EXECUTION_LOGGING = True

# إشعارات التنفيذ
EXECUTION_NOTIFICATIONS = {
    "immediate_execution": True,   # إشعار عند التنفيذ الفوري
    "delayed_execution": True,     # إشعار عند التأخير
    "failed_execution": True,      # إشعار عند الفشل
    "cancelled_orders": True       # إشعار عند الإلغاء
}

# ===== إعدادات الأمان =====
# Safety Settings

# التحقق من السيولة قبل الأمر
CHECK_LIQUIDITY_BEFORE_ORDER = True
MIN_VOLUME_THRESHOLD = 10000  # الحد الأدنى للحجم اليومي

# التحقق من انتشار السعر
CHECK_SPREAD_BEFORE_ORDER = True
MAX_SPREAD_PERCENTAGE = 2.0  # الحد الأقصى لانتشار السعر (%)

# حماية من التقلبات الشديدة
VOLATILITY_PROTECTION = True
MAX_VOLATILITY_THRESHOLD = 5.0  # الحد الأقصى للتقلب (%)

# ===== دالة الحصول على إعدادات التنفيذ =====
def get_execution_config(market_status="unknown"):
    """
    الحصول على إعدادات التنفيذ المناسبة حسب حالة السوق
    Get appropriate execution settings based on market status
    
    Args:
        market_status: "open", "extended", "closed", or "unknown"
    
    Returns:
        dict: إعدادات التنفيذ المناسبة
    """
    
    if market_status == "open":
        return IMMEDIATE_EXECUTION_CONFIG["market_open"]
    elif market_status == "extended":
        return IMMEDIATE_EXECUTION_CONFIG["extended_hours"]
    elif market_status == "closed":
        return IMMEDIATE_EXECUTION_CONFIG["market_closed"]
    else:
            # إعدادات افتراضية آمنة للساعات الممتدة
            return {
                "order_type": "market",  # سيتم تحويله لـ limit في alpaca_client
                "time_in_force": "day",
                "extended_hours": True
            }

# ===== دالة التحقق من إمكانية التنفيذ الفوري =====
def can_execute_immediately(symbol, market_utils=None):
    """
    التحقق من إمكانية التنفيذ الفوري للرمز
    Check if immediate execution is possible for the symbol
    
    Args:
        symbol: رمز السهم
        market_utils: أداة فحص السوق (اختيارية)
    
    Returns:
        tuple: (يمكن التنفيذ, السبب, الإعدادات المقترحة)
    """
    
    try:
        if market_utils:
            is_open = market_utils.is_market_open()
            is_extended = market_utils.is_extended_hours()
            
            if is_open:
                return True, "السوق مفتوح", get_execution_config("open")
            elif is_extended and EXTENDED_HOURS_TRADING:
                return True, "ساعات ممتدة متاحة", get_execution_config("extended")
            else:
                return False, "السوق مغلق", get_execution_config("closed")
        else:
            # إعدادات افتراضية عند عدم توفر معلومات السوق
            return True, "إعدادات افتراضية", get_execution_config("unknown")
            
    except Exception as e:
        return False, f"خطأ في التحقق: {str(e)}", get_execution_config("unknown")

# ===== مثال على الاستخدام =====
if __name__ == "__main__":
    print("🚀 إعدادات التنفيذ الفوري")
    print("=" * 30)
    
    for status in ["open", "extended", "closed"]:
        config = get_execution_config(status)
        print(f"\n📊 حالة السوق: {status}")
        print(f"   نوع الأمر: {config['order_type']}")
        print(f"   مدة الصلاحية: {config['time_in_force']}")
        print(f"   ساعات ممتدة: {config['extended_hours']}")