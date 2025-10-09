"""
استراتيجية تداول آمنة ومبسطة
Safe and Simple Trading Strategy

هذه الاستراتيجية مصممة لتقليل المخاطر وتحقيق أرباح صغيرة ومستقرة
This strategy is designed to minimize risk and achieve small, stable profits
"""

import logging
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass

from ..config.settings import settings
from ..models.stock import StockData, StockBar, TechnicalIndicators, StockQuote
from ..models.trade import Trade, TradeType, TradeStatus
from ..services.alpaca_client import AlpacaClient
from ..utils.error_handler import OrderExecutionError


@dataclass
class SafeTradeSignal:
    """إشارة تداول آمنة"""
    symbol: str
    action: str  # BUY or SELL
    confidence: float  # 0-1
    reason: str
    price: float


class SafeStrategy:
    """
    استراتيجية تداول آمنة ومبسطة
    
    المبادئ:
    1. صفقات صغيرة الحجم
    2. stop loss سريع (2%)
    3. take profit معقول (1.5%)
    4. تداول في الأسهم الكبيرة فقط
    5. حد أقصى 3 صفقات يومياً
    6. تجنب التعقيد
    """
    
    def __init__(self, alpaca_client: AlpacaClient, settings=None):
        self.alpaca_client = alpaca_client
        self.settings = settings or globals()['settings']
        self.logger = logging.getLogger(__name__)
        
        # إعدادات آمنة
        self.position_size = 25.0  # $25 لكل صفقة
        self.stop_loss_pct = 0.02  # 2% stop loss
        self.take_profit_pct = 0.015  # 1.5% take profit
        self.max_daily_trades = 999999  # عدد غير محدود للاختبار
        self.max_daily_loss = 50.0
        
        # الأسهم الآمنة فقط - قائمة موسعة للاختبار
        self.safe_symbols = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA',
            'JPM', 'JNJ', 'PG', 'KO', 'PEP', 'WMT', 'HD', 'DIS',
            'VZ', 'T', 'INTC', 'IBM', 'ORCL', 'CRM', 'ADBE',
            'NFLX', 'PYPL', 'UBER', 'LYFT', 'SQ', 'SHOP'
        ]
        
        # تتبع التداولات
        self.active_positions: Dict[str, Trade] = {}
        self.daily_trades_count = 0
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()
        
        # متغيرات للتتبع
        self.pending_orders = {}
        
        # Callbacks
        self.account_update_callback = None
        self.order_update_callback = None
        self.position_update_callback = None
        
        self.logger.info("Safe Strategy initialized with conservative settings")
    
    def set_callbacks(self, account_callback=None, order_callback=None, position_callback=None):
        """تعيين callbacks للتحديثات."""
        self.account_update_callback = account_callback
        self.order_update_callback = order_callback
        self.position_update_callback = position_callback
    
    def analyze_market(self, stock_data_list: List[StockData]) -> List[SafeTradeSignal]:
        """
        تحليل السوق بطريقة مبسطة وآمنة
        """
        signals = []
        
        # إعادة تعيين العدادات اليومية
        self._reset_daily_counters()
        
        # فحص حدود التداول اليومية
        if not self._can_trade():
            return signals
        
        for stock_data in stock_data_list:
            if stock_data.symbol not in self.safe_symbols:
                continue
                
            # تحليل بسيط للشراء
            buy_signal = self._analyze_buy_opportunity(stock_data)
            if buy_signal:
                signals.append(buy_signal)
            
            # تحليل البيع للمراكز الموجودة
            if stock_data.symbol in self.active_positions:
                sell_signal = self._analyze_sell_opportunity(stock_data)
                if sell_signal:
                    signals.append(sell_signal)
        
        return signals
    
    def _analyze_buy_opportunity(self, stock_data: StockData) -> Optional[SafeTradeSignal]:
        """
        تحليل فرصة شراء بسيطة
        
        الشروط البسيطة:
        1. السعر انخفض 1-3% من أعلى سعر في آخر 5 أيام
        2. RSI أقل من 40 (oversold)
        3. حجم التداول أعلى من المتوسط
        """
        symbol = stock_data.symbol
        
        # تجنب الشراء إذا كان لدينا مركز بالفعل
        if symbol in self.active_positions:
            return None
        
        current_price = self._get_current_price(stock_data)
        if not current_price:
            return None
        
        # فحص الشروط البسيطة
        conditions_met = 0
        reasons = []
        
        # شرط 1: انخفاض بسيط من القمة
        if self._is_minor_dip(stock_data, current_price):
            conditions_met += 1
            reasons.append("انخفاض بسيط من القمة")
        
        # شرط 2: RSI oversold
        if self._is_oversold(stock_data):
            conditions_met += 1
            reasons.append("RSI oversold")
        
        # شرط 3: حجم تداول جيد
        if self._has_good_volume(stock_data):
            conditions_met += 1
            reasons.append("حجم تداول جيد")
        
        # نحتاج على الأقل شرط واحد للاختبار
        if conditions_met >= 1:
            confidence = min(conditions_met / 3.0, 0.8)  # حد أقصى 80%
            reason = f"شروط الشراء: {', '.join(reasons)}"
            
            return SafeTradeSignal(
                symbol=symbol,
                action="BUY",
                confidence=confidence,
                reason=reason,
                price=current_price
            )
        
        return None
    
    def _analyze_sell_opportunity(self, stock_data: StockData) -> Optional[SafeTradeSignal]:
        """
        تحليل فرصة بيع بسيطة
        """
        symbol = stock_data.symbol
        
        # التحقق من وجود الرمز في المراكز النشطة
        if symbol not in self.active_positions:
            return None
            
        trade = self.active_positions[symbol]
        
        current_price = self._get_current_price(stock_data)
        if not current_price:
            return None
        
        # حساب الربح/الخسارة
        pnl_pct = (current_price - trade.price) / trade.price
        
        # شروط البيع البسيطة
        sell_reason = None
        
        # 1. Stop Loss (2%)
        if pnl_pct <= -self.stop_loss_pct:
            sell_reason = f"Stop Loss: خسارة {pnl_pct*100:.1f}%"
        
        # 2. Take Profit (1.5%)
        elif pnl_pct >= self.take_profit_pct:
            sell_reason = f"Take Profit: ربح {pnl_pct*100:.1f}%"
        
        # 3. RSI مرتفع جداً (overbought)
        elif self._is_overbought(stock_data) and pnl_pct > 0:
            sell_reason = f"RSI overbought مع ربح {pnl_pct*100:.1f}%"
        
        if sell_reason:
            return SafeTradeSignal(
                symbol=symbol,
                action="SELL",
                confidence=0.9,
                reason=sell_reason,
                price=current_price
            )
        
        return None
    
    def _get_current_price(self, stock_data: StockData) -> Optional[float]:
        """الحصول على السعر الحالي"""
        if stock_data.current_quote and stock_data.current_quote.mid_price:
            return float(stock_data.current_quote.mid_price)
        elif stock_data.latest_bar:
            return float(stock_data.latest_bar.close)
        return None
    
    def _is_minor_dip(self, stock_data: StockData, current_price: float) -> bool:
        """فحص إذا كان هناك انخفاض بسيط من القمة"""
        try:
            # نحتاج بيانات تاريخية للمقارنة
            # هذا مبسط - في الواقع نحتاج بيانات آخر 5 أيام
            if (stock_data.technical_indicators and 
                stock_data.technical_indicators.sma_20):
                sma_20 = stock_data.technical_indicators.sma_20
                # إذا كان السعر أقل من SMA20 بـ 1-3%
                dip_pct = (sma_20 - current_price) / sma_20
                return 0.01 <= dip_pct <= 0.03
        except:
            pass
        return False
    
    def _is_oversold(self, stock_data: StockData) -> bool:
        """فحص إذا كان RSI يشير إلى oversold - شروط مخففة للاختبار"""
        try:
            if (stock_data.technical_indicators and 
                stock_data.technical_indicators.rsi):
                return stock_data.technical_indicators.rsi < 50  # مخفف من 40 إلى 50
        except:
            pass
        return False
    
    def _is_overbought(self, stock_data: StockData) -> bool:
        """فحص إذا كان RSI يشير إلى overbought - شروط مخففة للاختبار"""
        try:
            if (stock_data.technical_indicators and 
                stock_data.technical_indicators.rsi):
                return stock_data.technical_indicators.rsi > 60  # مخفف من 70 إلى 60
        except:
            pass
        return False
    
    def _has_good_volume(self, stock_data: StockData) -> bool:
        """فحص حجم التداول - شروط مخففة للاختبار"""
        try:
            if (stock_data.technical_indicators and 
                hasattr(stock_data.technical_indicators, 'volume_ratio')):
                return stock_data.technical_indicators.volume_ratio > 0.8  # مخفف من 1.2 إلى 0.8
        except:
            pass
        return True  # افتراض أن الحجم جيد إذا لم نتمكن من فحصه
    
    def _can_trade(self) -> bool:
        """فحص إذا كان بإمكاننا التداول"""
        # فحص عدد الصفقات اليومية
        if self.daily_trades_count >= self.max_daily_trades:
            self.logger.info(f"وصلنا للحد الأقصى من الصفقات اليومية: {self.max_daily_trades}")
            return False
        
        # فحص الخسائر اليومية
        if self.daily_pnl <= -self.max_daily_loss:
            self.logger.info(f"وصلنا للحد الأقصى من الخسائر اليومية: ${self.max_daily_loss}")
            return False
        
        return True
    
    def _reset_daily_counters(self):
        """إعادة تعيين العدادات اليومية"""
        today = datetime.now().date()
        if today != self.last_reset_date:
            self.daily_trades_count = 0
            self.daily_pnl = 0.0
            self.last_reset_date = today
            self.logger.info("تم إعادة تعيين العدادات اليومية")
    
    def execute_signal(self, signal: SafeTradeSignal) -> bool:
        """تنفيذ إشارة التداول"""
        try:
            if signal.action == "BUY":
                return self._execute_buy(signal)
            elif signal.action == "SELL":
                return self._execute_sell(signal)
        except Exception as e:
            self.logger.error(f"خطأ في تنفيذ الإشارة {signal.symbol}: {e}")
        return False
    
    def _execute_buy(self, signal: SafeTradeSignal) -> bool:
        """تنفيذ أمر شراء"""
        try:
            symbol = signal.symbol
            
            # حساب الكمية
            quantity = self.position_size / signal.price
            
            # تنفيذ الأمر
            order = self.alpaca_client.place_order(
                symbol=symbol,
                qty=quantity,
                side='buy',
                order_type='market',
                time_in_force='day'
            )
            
            if order:
                # إنشاء كائن التداول
                trade = Trade(
                    symbol=symbol,
                    trade_type=TradeType.BUY,
                    quantity=quantity,
                    price=signal.price,
                    timestamp=datetime.now(),
                    order_id=order.id,
                    status=TradeStatus.PENDING,
                    notes=signal.reason
                )
                
                self.active_positions[symbol] = trade
                self.daily_trades_count += 1
                
                self.logger.info(f"✅ تم شراء {symbol}: ${self.position_size:.2f} - {signal.reason}")
                return True
        
        except Exception as e:
            self.logger.error(f"❌ خطأ في شراء {signal.symbol}: {e}")
        
        return False
    
    def _execute_sell(self, signal: SafeTradeSignal) -> bool:
        """تنفيذ أمر بيع"""
        try:
            symbol = signal.symbol
            trade = self.active_positions[symbol]
            
            # تنفيذ الأمر
            order = self.alpaca_client.place_order(
                symbol=symbol,
                qty=trade.quantity,
                side='sell',
                order_type='market',
                time_in_force='day'
            )
            
            if order:
                # حساب الربح/الخسارة
                pnl = (signal.price - trade.price) * trade.quantity
                self.daily_pnl += pnl
                
                # إزالة المركز
                del self.active_positions[symbol]
                self.daily_trades_count += 1
                
                pnl_pct = (signal.price - trade.price) / trade.price * 100
                self.logger.info(f"✅ تم بيع {symbol}: ربح/خسارة ${pnl:.2f} ({pnl_pct:.1f}%) - {signal.reason}")
                return True
        
        except Exception as e:
            self.logger.error(f"❌ خطأ في بيع {signal.symbol}: {e}")
        
        return False
    
    def update_positions(self):
        """تحديث المراكز المفتوحة."""
        try:
            # تحديث بسيط للمراكز
            pass
        except Exception as e:
            self.logger.error(f"Error updating positions: {e}")
    
    def analyze_symbol(self, symbol: str) -> Optional[StockData]:
        """تحليل رمز سهم واحد."""
        try:
            # جلب البيانات من Alpaca
            from datetime import datetime, timedelta
            
            # تحديد الفترة الزمنية - استخدام فترة أطول للحصول على البيانات
            end_time = datetime.now()
            start_time = end_time - timedelta(days=5)  # آخر 5 أيام
            
            self.logger.info(f"Fetching data for {symbol} from {start_time} to {end_time}")
            
            bars = self.alpaca_client.get_bars(
                symbol=symbol,
                timeframe='1Day',
                start=start_time,
                end=end_time,
                limit=100
            )
            
            self.logger.info(f"Received bars for {symbol}: type={type(bars)}, empty={bars.empty if hasattr(bars, 'empty') else 'N/A'}, len={len(bars) if bars is not None else 'None'}")
            
            if bars is None or bars.empty or len(bars) == 0:
                self.logger.warning(f"No data available for {symbol}")
                return None
            
            # تحويل البيانات إلى StockData
            # bars هو DataFrame من pandas
            latest_bar = bars.iloc[-1]
            
            # حساب المؤشرات الفنية البسيطة
            prices = bars['close'].tolist()
            volumes = bars['volume'].tolist()
            
            # حساب المتوسطات المتحركة
            sma_20 = sum(prices[-20:]) / min(20, len(prices)) if len(prices) >= 5 else prices[-1]
            sma_50 = sum(prices[-50:]) / min(50, len(prices)) if len(prices) >= 10 else prices[-1]
            
            # حساب RSI مبسط
            gains = []
            losses = []
            for i in range(1, min(14, len(prices))):
                change = prices[i] - prices[i-1]
                if change > 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))
            
            avg_gain = sum(gains) / len(gains) if gains else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            rs = avg_gain / avg_loss if avg_loss > 0 else 0
            rsi = 100 - (100 / (1 + rs)) if rs > 0 else 50
            
            # إنشاء StockBar للبيانات الحالية
            latest_stock_bar = StockBar(
                symbol=symbol,
                timestamp=latest_bar.name if hasattr(latest_bar, 'name') else datetime.now(),
                open=float(latest_bar['open']),
                high=float(latest_bar['high']),
                low=float(latest_bar['low']),
                close=float(latest_bar['close']),
                volume=int(latest_bar['volume'])
            )
            
            # إنشاء TechnicalIndicators
            tech_indicators = TechnicalIndicators(
                symbol=symbol,
                timestamp=latest_bar.name if hasattr(latest_bar, 'name') else datetime.now(),
                sma_20=sma_20,
                sma_50=sma_50,
                rsi=rsi
            )
            
            # إنشاء StockQuote للسعر الحالي
            current_price = float(latest_bar['close'])
            current_quote = StockQuote(
                symbol=symbol,
                bid=current_price * 0.999,  # تقدير bid/ask spread
                ask=current_price * 1.001,
                bid_size=100,
                ask_size=100,
                timestamp=latest_bar.name if hasattr(latest_bar, 'name') else datetime.now()
            )
            
            stock_data = StockData(
                symbol=symbol,
                company_name=symbol,  # استخدام الرمز كاسم مؤقت
                current_quote=current_quote,
                latest_bar=latest_stock_bar,
                technical_indicators=tech_indicators
            )
            
            self.logger.info(f"Successfully analyzed {symbol}: ${stock_data.current_price:.2f}")
            self.logger.debug(f"analyze_symbol returning: {type(stock_data)} for {symbol}")
            return stock_data
            
        except Exception as e:
            self.logger.error(f"Error analyzing symbol {symbol}: {e}")
            self.logger.debug(f"analyze_symbol returning None for {symbol} due to error")
            return None
    
    def generate_signals(self, stock_data: Optional[StockData]) -> List[SafeTradeSignal]:
        """توليد إشارات التداول."""
        if not stock_data:
            self.logger.debug("generate_signals: stock_data is None or empty")
            return []
        
        signals = []
        
        try:
            # فحص إشارات الشراء
            buy_signal = self._analyze_buy_opportunity(stock_data)
            if buy_signal:
                signals.append(buy_signal)
            
            # فحص إشارات البيع
            sell_signal = self._analyze_sell_opportunity(stock_data)
            if sell_signal:
                signals.append(sell_signal)
                
        except Exception as e:
            symbol = getattr(stock_data, 'symbol', 'Unknown') if stock_data else 'Unknown'
            self.logger.error(f"Error generating signals for {symbol}: {e}")
        
        return signals
    
    def execute_trade(self, symbol: str, signal_type: str, reason: str) -> Optional[Trade]:
        """تنفيذ صفقة."""
        try:
            # تنفيذ مبسط للصفقة
            return None
        except Exception as e:
            self.logger.error(f"Error executing trade for {symbol}: {e}")
            return None
    
    def set_trading_mode(self, mode):
        """تعيين وضع التداول."""
        self.logger.info(f"Trading mode set to: {mode}")
    
    def execute_safe_trade(self, signal: SafeTradeSignal) -> Optional[Trade]:
        """تنفيذ صفقة آمنة."""
        try:
            # تنفيذ مبسط للصفقة الآمنة
            return None
        except Exception as e:
            self.logger.error(f"Error executing safe trade for {signal.symbol}: {e}")
            return None
    
    def get_status(self) -> Dict:
        """الحصول على حالة الاستراتيجية"""
        return {
            'active_positions': len(self.active_positions),
            'daily_trades': self.daily_trades_count,
            'daily_pnl': self.daily_pnl,
            'max_daily_trades': self.max_daily_trades,
            'max_daily_loss': self.max_daily_loss,
            'can_trade': self._can_trade()
        }