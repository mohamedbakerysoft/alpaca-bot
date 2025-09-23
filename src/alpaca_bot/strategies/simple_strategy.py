"""Enhanced trading strategy implementation for automated trading.

This module implements an optimized strategy that:
1. Uses multiple technical indicators with confirmations
2. Analyzes market trend before taking positions
3. Implements smart risk management
4. Focuses on high-probability trades
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np
from alpaca_trade_api.rest import REST

from ..config.settings import settings
from ..models.stock import StockData, StockQuote, StockBar, TechnicalIndicators
from ..models.trade import Trade, TradeType, OrderType, TradeStatus
from ..services.alpaca_client import AlpacaClient
from ..utils.technical_analysis import calculate_rsi, calculate_sma
from ..utils.logging_utils import trade_logger
from ..utils.error_handler import (
    ErrorHandler, MarketDataError, OrderExecutionError,
    safe_execute
)


class EnhancedStrategy:
    """Enhanced trading strategy with improved signal generation and risk management."""
    
    def __init__(self, alpaca_client: AlpacaClient, settings=None):
        """Initialize the enhanced strategy.
        
        Args:
            alpaca_client: Alpaca API client.
            settings: Strategy settings.
        """
        self.alpaca_client = alpaca_client
        self.settings = settings or globals()['settings']
        self.logger = logging.getLogger(__name__)
        
        # Enhanced strategy parameters - Using unified settings
        self.position_size_pct = getattr(self.settings, 'max_position_percentage', 0.03)  # % of portfolio per trade
        self.stop_loss_pct = getattr(self.settings, 'stop_loss_percentage', 0.015)     # Stop loss from settings
        self.take_profit_pct = getattr(self.settings, 'take_profit_percentage', 0.001)    # Take profit from settings - 0.1%
        self.max_daily_trades = getattr(self.settings, 'max_daily_trades', 8)      # Maximum trades per day from settings
        self.min_volume_threshold = 50000  # Reduced from 100000 to 50000 - Minimum daily volume
        
        # Technical indicator thresholds
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.rsi_neutral_low = 40
        self.rsi_neutral_high = 60
        
        # Trend analysis parameters
        self.trend_strength_threshold = 0.02  # 2% for strong trend
        self.volume_spike_threshold = 1.5     # 1.5x average volume
        
        # State tracking
        self.active_positions: Dict[str, Trade] = {}
        self.recently_removed_positions: Dict[str, float] = {}  # symbol -> timestamp when removed
        self.removal_cooldown = 300  # 5 minutes cooldown before re-adding removed positions
        self.pending_orders: Dict[str, str] = {}
        self.daily_trades_count = 0
        self.last_reset_date = datetime.now().date()
        
        # API call optimization
        self.last_position_refresh = 0.0  # timestamp of last position refresh
        self.position_refresh_interval = 30.0  # refresh positions every 30 seconds instead of every update
        self.last_order_batch_check = 0.0  # timestamp of last batch order check
        self.order_check_interval = 10.0  # check orders every 10 seconds
        
        # Callbacks
        self.account_update_callback = None
        self.order_update_callback = None
        self.position_update_callback = None
        
        self.logger.info(f"Enhanced strategy initialized with optimized parameters")
        self.logger.info(f"Using unified settings - Stop Loss: {self.stop_loss_pct:.4f} ({self.stop_loss_pct*100:.2f}%), Take Profit: {self.take_profit_pct:.4f} ({self.take_profit_pct*100:.2f}%)")
        
        # Load existing positions from Alpaca
        self._load_existing_positions()

    def _load_existing_positions(self):
        """Load existing positions from Alpaca into the strategy's tracking system."""
        try:
            self.logger.info("Attempting to load existing positions from Alpaca...")
            positions = self.alpaca_client.get_positions()
            
            if positions:
                self.logger.info(f"Found {len(positions)} positions in Alpaca account")
                loaded_count = 0
                
                for position in positions:
                    try:
                        symbol = position.symbol
                        qty = float(position.qty)
                        avg_entry_price = float(position.avg_entry_price)
                        market_value = float(position.market_value) if hasattr(position, 'market_value') else 0
                        unrealized_pl = float(position.unrealized_pl) if hasattr(position, 'unrealized_pl') else 0
                        
                        self.logger.info(f"Processing position: {symbol} - Qty: {qty}, Entry: ${avg_entry_price:.2f}, Value: ${market_value:.2f}, P&L: ${unrealized_pl:.2f}")
                        
                        if qty > 0 and avg_entry_price > 0:  # Only track long positions
                            # Create a Trade object for tracking
                            trade = Trade(
                                symbol=symbol,
                                trade_type=TradeType.BUY,
                                quantity=qty,
                                price=avg_entry_price,
                                timestamp=datetime.now(),
                                order_type=OrderType.MARKET,
                                status=TradeStatus.FILLED,
                                notes="Existing position loaded from Alpaca"
                            )
                            self.active_positions[symbol] = trade
                            loaded_count += 1
                            
                            # Calculate current P&L percentage for logging
                            if market_value > 0 and qty > 0:
                                current_price = market_value / qty
                                pnl_pct = ((current_price - avg_entry_price) / avg_entry_price) * 100
                                self.logger.info(f"✓ Loaded position: {symbol} - {qty:.4f} shares at ${avg_entry_price:.2f}, Current P&L: {pnl_pct:.2f}%")
                            else:
                                self.logger.info(f"✓ Loaded position: {symbol} - {qty:.4f} shares at ${avg_entry_price:.2f}")
                        else:
                            self.logger.warning(f"Skipping position {symbol}: qty={qty}, price={avg_entry_price}")
                            
                    except Exception as pos_error:
                        self.logger.error(f"Error processing position {symbol}: {pos_error}")
                        continue
                
                self.logger.info(f"Successfully loaded {loaded_count} existing positions from Alpaca")
                
                # Log current take profit and stop loss settings for reference
                self.logger.info(f"Strategy settings - Take Profit: {self.take_profit_pct*100:.2f}%, Stop Loss: {self.stop_loss_pct*100:.2f}%")
                
            else:
                self.logger.info("No existing positions found in Alpaca account")
                
        except Exception as e:
            self.logger.error(f"Error loading existing positions: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")

    def set_callbacks(self, account_callback=None, order_callback=None, position_callback=None):
        """Set callback functions for updates."""
        self.account_update_callback = account_callback
        self.order_update_callback = order_callback
        self.position_update_callback = position_callback

    def _reset_daily_counters_if_needed(self):
        """Reset daily counters if it's a new trading day."""
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            self.daily_trades_count = 0
            self.last_reset_date = current_date
            self.logger.info("Daily counters reset for new trading day")

    def analyze_symbol(self, symbol: str) -> Optional[StockData]:
        """Analyze a symbol with enhanced technical indicators.
        
        Args:
            symbol: Stock symbol to analyze.
            
        Returns:
            StockData object with enhanced analysis or None if error.
        """
        try:
            # Get market data for the last 30 days to ensure we have enough data
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            bars = self.alpaca_client.get_bars(
                symbol, 
                timeframe='1Day', 
                start=start_date,
                end=end_date,
                limit=100
            )
            self.logger.info(f"{symbol}: Retrieved {len(bars) if bars is not None and not bars.empty else 0} bars")
            if bars is None or bars.empty or len(bars) < 20:  # Reduced from 50 to 20 days
                self.logger.warning(f"{symbol}: Insufficient data for analysis (got {len(bars) if bars is not None and not bars.empty else 0} bars, need 20)")
                return None
            
            # Convert to DataFrame for analysis (bars is already a DataFrame)
            df = bars.copy()
            
            # Ensure required columns exist
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_columns):
                self.logger.error(f"{symbol}: Missing required columns in market data")
                return None
            
            # Check minimum volume requirement
            avg_volume = df['volume'].tail(20).mean()
            if avg_volume < self.min_volume_threshold:
                self.logger.warning(f"{symbol}: Volume too low ({avg_volume:.0f} < {self.min_volume_threshold})")
                return None
            
            # Calculate enhanced technical indicators
            df['rsi'] = self._calculate_rsi(df['close'], 14)
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            df['ema_12'] = df['close'].ewm(span=12).mean()
            df['ema_26'] = df['close'].ewm(span=26).mean()
            df['macd'] = df['ema_12'] - df['ema_26']
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['bb_upper'], df['bb_lower'] = self._calculate_bollinger_bands(df['close'], 20, 2)
            df['volume_sma'] = df['volume'].rolling(window=20).mean()
            
            # Get latest values
            latest = df.iloc[-1]
            
            # Create technical indicators object
            technical_indicators = TechnicalIndicators(
                symbol=symbol,
                timestamp=datetime.now(),
                rsi=float(latest['rsi']) if pd.notna(latest['rsi']) else 50.0,
                sma_20=float(latest['sma_20']) if pd.notna(latest['sma_20']) else latest['close'],
                sma_50=float(latest['sma_50']) if pd.notna(latest['sma_50']) else latest['close'],
                bollinger_upper=float(latest['bb_upper']) if pd.notna(latest['bb_upper']) else latest['close'] * 1.02,
                bollinger_lower=float(latest['bb_lower']) if pd.notna(latest['bb_lower']) else latest['close'] * 0.98,
                bollinger_middle=float(latest['sma_20']) if pd.notna(latest['sma_20']) else latest['close'],
                macd=float(latest['macd']) if pd.notna(latest['macd']) else 0.0,
                macd_signal=float(latest['macd_signal']) if pd.notna(latest['macd_signal']) else 0.0,
                macd_histogram=float(latest['macd'] - latest['macd_signal']) if pd.notna(latest['macd']) and pd.notna(latest['macd_signal']) else 0.0
            )
            
            # Add custom attributes for enhanced analysis
            technical_indicators.ema_12 = float(latest['ema_12']) if pd.notna(latest['ema_12']) else latest['close']
            technical_indicators.ema_26 = float(latest['ema_26']) if pd.notna(latest['ema_26']) else latest['close']
            technical_indicators.volume_ratio = float(latest['volume'] / latest['volume_sma']) if pd.notna(latest['volume_sma']) and latest['volume_sma'] > 0 else 1.0
            
            # Get current quote
            quote_data = self.alpaca_client.get_latest_quote(symbol)
            if not quote_data:
                self.logger.warning(f"{symbol}: Could not get current quote")
                return None
            
            # Create StockQuote object from quote data
            current_quote = StockQuote(
                symbol=symbol,
                bid=float(quote_data['bid']),
                ask=float(quote_data['ask']),
                bid_size=int(quote_data['bid_size']),
                ask_size=int(quote_data['ask_size']),
                timestamp=datetime.now()
            )
            
            # Create stock data object
            stock_data = StockData(
                symbol=symbol,
                company_name=symbol,
                current_quote=current_quote,
                technical_indicators=technical_indicators
            )
            
            return stock_data
            
        except Exception as e:
            self.logger.error(f"Error analyzing {symbol}: {e}")
            return None

    def generate_signals(self, stock_data: StockData) -> List[Tuple[str, str]]:
        """Generate enhanced trading signals with multiple confirmations.
        
        Args:
            stock_data: Stock data with technical indicators.
            
        Returns:
            List of (signal_type, reason) tuples.
        """
        signals = []
        symbol = stock_data.symbol
        
        if not stock_data.technical_indicators or not stock_data.current_quote:
            return signals
        
        ti = stock_data.technical_indicators
        current_price = float(stock_data.current_quote.bid)
        
        # Check if we already have a position
        has_position = symbol in self.active_positions
        
        # Reset daily counters if needed
        self._reset_daily_counters_if_needed()
        
        # Check daily trade limit
        if self.daily_trades_count >= self.max_daily_trades:
            return signals
        
        # Analyze market trend
        trend_direction = self._analyze_trend(ti)
        trend_strength = abs((ti.sma_20 - ti.sma_50) / ti.sma_50) if ti.sma_50 > 0 else 0
        
        # BUY SIGNALS (only if no position and uptrend)
        if not has_position and trend_direction == "UP":
            buy_score = 0
            buy_reasons = []
            
            # RSI conditions (stronger signals)
            if ti.rsi < self.rsi_oversold:
                buy_score += 3
                buy_reasons.append(f"RSI oversold ({ti.rsi:.1f})")
            elif ti.rsi < self.rsi_neutral_low:
                buy_score += 1
                buy_reasons.append(f"RSI favorable ({ti.rsi:.1f})")
            
            # MACD bullish signal
            if ti.macd > ti.macd_signal:
                buy_score += 2
                buy_reasons.append("MACD bullish crossover")
            
            # Price near support (Bollinger Band lower)
            if current_price <= ti.bollinger_lower * 1.02:  # Within 2% of lower band
                buy_score += 2
                buy_reasons.append("Price near support level")
            
            # Strong uptrend confirmation
            if trend_strength > self.trend_strength_threshold:
                buy_score += 2
                buy_reasons.append(f"Strong uptrend ({trend_strength*100:.1f}%)")
            
            # Volume confirmation
            if hasattr(ti, 'volume_ratio') and ti.volume_ratio > self.volume_spike_threshold:
                buy_score += 1
                buy_reasons.append(f"High volume ({ti.volume_ratio:.1f}x)")
            
            # Price action confirmation
            if hasattr(ti, 'ema_12') and hasattr(ti, 'ema_26') and current_price > ti.ema_12 and ti.ema_12 > ti.ema_26:
                buy_score += 1
                buy_reasons.append("Bullish price action")
            
            # Generate BUY signal if score is high enough
            if buy_score >= 4:  # Require strong confirmation
                reason = f"Score: {buy_score}/10 - " + "; ".join(buy_reasons)
                signals.append(("BUY", reason))
                self.logger.info(f"{symbol}: BUY signal generated - {reason}")
        
        # SELL SIGNALS (only if we have a position)
        elif has_position:
            sell_reasons = []
            position_trade = self.active_positions[symbol]
            entry_price = position_trade.price
            
            # Calculate profit/loss percentage
            pnl_pct = (current_price - entry_price) / entry_price
            
            # Mandatory exits (risk management)
            if pnl_pct >= self.take_profit_pct:
                sell_reasons.append(f"Take profit ({pnl_pct*100:.1f}%)")
            elif pnl_pct <= -self.stop_loss_pct:
                sell_reasons.append(f"Stop loss ({pnl_pct*100:.1f}%)")
            
            # Technical exits
            elif ti.rsi > self.rsi_overbought:
                sell_reasons.append(f"RSI overbought ({ti.rsi:.1f})")
            elif ti.macd < ti.macd_signal and pnl_pct > 0.005:  # MACD bearish with small profit
                sell_reasons.append("MACD bearish crossover")
            elif current_price >= ti.bollinger_upper * 0.98 and pnl_pct > 0.01:  # Near resistance with profit
                sell_reasons.append("Price near resistance")
            elif trend_direction == "DOWN" and pnl_pct > 0:  # Trend reversal with profit
                sell_reasons.append("Trend reversal detected")
            
            # Generate SELL signal
            if sell_reasons:
                reason = "; ".join(sell_reasons)
                signals.append(("SELL", reason))
                self.logger.info(f"{symbol}: SELL signal generated - {reason}")
        
        return signals

    def _analyze_trend(self, ti: TechnicalIndicators) -> str:
        """Analyze market trend direction.
        
        Args:
            ti: Technical indicators.
            
        Returns:
            Trend direction: "UP", "DOWN", or "SIDEWAYS".
        """
        # Multiple timeframe trend analysis
        sma_trend = "UP" if ti.sma_20 > ti.sma_50 else "DOWN"
        macd_trend = "UP" if ti.macd > ti.macd_signal else "DOWN"
        
        # EMA trend if available
        ema_trend = "NEUTRAL"
        if hasattr(ti, 'ema_12') and hasattr(ti, 'ema_26'):
            ema_trend = "UP" if ti.ema_12 > ti.ema_26 else "DOWN"
        
        # Count bullish signals
        bullish_signals = [sma_trend == "UP", macd_trend == "UP"]
        if ema_trend != "NEUTRAL":
            bullish_signals.append(ema_trend == "UP")
        
        bullish_count = sum(bullish_signals)
        total_signals = len(bullish_signals)
        
        if bullish_count >= total_signals * 0.7:  # 70% bullish
            return "UP"
        elif bullish_count <= total_signals * 0.3:  # 30% or less bullish
            return "DOWN"
        else:
            return "SIDEWAYS"

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: float = 2) -> Tuple[pd.Series, pd.Series]:
        """Calculate Bollinger Bands."""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        return upper_band, lower_band

    def execute_trade(self, symbol: str, signal_type: str, reason: str) -> Optional[Trade]:
        """Execute a trade based on the signal.
        
        Args:
            symbol: Stock symbol.
            signal_type: Type of signal (BUY/SELL).
            reason: Reason for the trade.
            
        Returns:
            Trade object if successful, None otherwise.
        """
        try:
            if signal_type == "BUY":
                return self._execute_buy_order(symbol, reason)
            elif signal_type == "SELL":
                return self._execute_sell_order(symbol, reason)
            else:
                self.logger.warning(f"Unknown signal type: {signal_type}")
                return None
        except Exception as e:
            self.logger.error(f"Error executing {signal_type} trade for {symbol}: {e}")
            return None

    def _execute_buy_order(self, symbol: str, reason: str) -> Optional[Trade]:
        """Execute a buy order."""
        try:
            # Get account information
            account = self.alpaca_client.get_account()
            if not account:
                raise OrderExecutionError("Could not get account information")
            
            # Calculate position size
            portfolio_value = float(account.portfolio_value)
            position_value = portfolio_value * self.position_size_pct
            position_value = max(position_value, 1.0)  # Minimum $1
            
            # Get current quote
            quote = self.alpaca_client.get_latest_quote(symbol)
            if not quote:
                raise OrderExecutionError(f"Could not get quote for {symbol}")
            
            current_price = float(quote['ask'])
            quantity = position_value / current_price
            
            # Place market buy order
            order = self.alpaca_client.place_order(
                symbol=symbol,
                qty=quantity,
                side='buy',
                order_type='market',
                time_in_force='day'
            )
            
            if not order:
                raise OrderExecutionError("Failed to submit buy order")
            
            # Create trade object
            trade = Trade(
                symbol=symbol,
                trade_type=TradeType.BUY,
                quantity=quantity,
                price=current_price,
                timestamp=datetime.now(),
                order_id=order.id,
                status=TradeStatus.PENDING,
                notes=reason
            )
            
            # Track the order and position
            self.pending_orders[symbol] = order.id
            self.active_positions[symbol] = trade
            self.daily_trades_count += 1
            
            self.logger.info(f"Buy order placed for {symbol}: ${position_value:.2f} ({quantity:.4f} shares) at ${current_price:.2f}")
            
            # Trigger callbacks
            if self.account_update_callback:
                self.account_update_callback()
            if self.order_update_callback:
                self.order_update_callback()
            
            return trade
            
        except Exception as e:
            self.logger.error(f"Error executing buy order for {symbol}: {e}")
            return None

    def _execute_sell_order(self, symbol: str, reason: str) -> Optional[Trade]:
        """Execute a sell order."""
        try:
            # Check if we have a position
            if symbol not in self.active_positions:
                self.logger.warning(f"No active position for {symbol}")
                return None
            
            position_trade = self.active_positions[symbol]
            
            # Verify actual position quantity with Alpaca before selling
            try:
                alpaca_position = self.alpaca_client.get_position(symbol)
                if alpaca_position:
                    actual_quantity = float(alpaca_position.qty)
                    if actual_quantity <= 0:
                        self.logger.warning(f"No actual position for {symbol} in Alpaca (qty: {actual_quantity}). Removing from tracking.")
                        del self.active_positions[symbol]
                        return None
                    
                    # Use the actual quantity from Alpaca, not our tracked quantity
                    quantity = actual_quantity
                    
                    # Update our tracked quantity if it differs
                    if abs(quantity - position_trade.quantity) > 0.0001:
                        self.logger.info(f"Updating tracked quantity for {symbol}: {position_trade.quantity} -> {quantity}")
                        position_trade.quantity = quantity
                else:
                    self.logger.warning(f"Position {symbol} not found in Alpaca. Removing from tracking.")
                    del self.active_positions[symbol]
                    return None
            except Exception as e:
                self.logger.error(f"Error verifying position for {symbol}: {e}")
                # Fall back to tracked quantity if verification fails
                quantity = position_trade.quantity
            
            # Get current quote
            quote = self.alpaca_client.get_latest_quote(symbol)
            if not quote:
                raise OrderExecutionError(f"Could not get quote for {symbol}")
            
            current_price = float(quote['bid'])
            
            # Place market sell order
            try:
                order = self.alpaca_client.place_order(
                    symbol=symbol,
                    qty=quantity,
                    side='sell',
                    order_type='market',
                    time_in_force='day'
                )
            except Exception as order_error:
                # Handle insufficient quantity and other order errors gracefully
                error_msg = str(order_error).lower()
                if 'insufficient qty' in error_msg or 'insufficient quantity' in error_msg:
                    self.logger.warning(f"Insufficient quantity for {symbol}. Removing from tracking and adding to cooldown.")
                    # Remove from tracking since we can't sell it
                    del self.active_positions[symbol]
                    # Add to recently removed positions with current timestamp
                    self.recently_removed_positions[symbol] = time.time()
                    # Force a position refresh to sync with Alpaca
                    self._refresh_positions_from_alpaca()
                    return None
                else:
                    # Re-raise other order errors
                    raise OrderExecutionError(f"Failed to execute sell order for {quantity} {symbol}: {order_error}")
            
            if not order:
                raise OrderExecutionError("Failed to submit sell order")
            
            # Create trade object
            trade = Trade(
                symbol=symbol,
                trade_type=TradeType.SELL,
                quantity=quantity,
                price=current_price,
                timestamp=datetime.now(),
                order_id=order.id,
                status=TradeStatus.PENDING,
                notes=reason
            )
            
            # Track the order
            self.pending_orders[symbol] = order.id
            
            # Remove from active positions
            del self.active_positions[symbol]
            self.daily_trades_count += 1
            
            self.logger.info(f"Sell order placed for {symbol}: {quantity:.4f} shares at ${current_price:.2f}")
            
            # Trigger callbacks
            if self.account_update_callback:
                self.account_update_callback()
            if self.order_update_callback:
                self.order_update_callback()
            
            return trade
            
        except Exception as e:
            self.logger.error(f"Error executing sell order for {symbol}: {e}")
            return None

    def get_active_positions(self) -> Dict[str, Trade]:
        """Get active positions."""
        return self.active_positions.copy()

    def get_daily_trades_count(self) -> int:
        """Get daily trades count."""
        self._reset_daily_counters_if_needed()
        return self.daily_trades_count

    def update_position_status(self, symbol: str, status: TradeStatus):
        """Update position status."""
        if symbol in self.active_positions:
            self.active_positions[symbol].status = status

    def remove_position(self, symbol: str):
        """Remove a position from active positions."""
        if symbol in self.active_positions:
            del self.active_positions[symbol]
        if symbol in self.pending_orders:
            del self.pending_orders[symbol]

    def _refresh_positions_from_alpaca(self):
        """Refresh position tracking from Alpaca to ensure all positions are monitored."""
        try:
            alpaca_positions = self.alpaca_client.get_positions()
            
            # Track symbols we've seen in Alpaca with positive quantities
            alpaca_symbols = set()
            
            for position in alpaca_positions:
                symbol = position.symbol
                quantity = float(position.qty)
                entry_price = float(position.avg_entry_price)
                
                # Only track positions with positive quantities
                if quantity > 0:
                    alpaca_symbols.add(symbol)
                    
                    # If we're not tracking this position, add it (but check cooldown and recent orders first)
                    if symbol not in self.active_positions:
                        # Check if this position was recently removed due to insufficient quantity
                        current_time = time.time()
                        if symbol in self.recently_removed_positions:
                            removal_time = self.recently_removed_positions[symbol]
                            if current_time - removal_time < self.removal_cooldown:
                                self.logger.info(f"Skipping re-add of {symbol} - still in cooldown period ({self.removal_cooldown - (current_time - removal_time):.1f}s remaining)")
                                continue
                            else:
                                # Cooldown expired, remove from recently removed
                                del self.recently_removed_positions[symbol]
                        
                        # Verify no recent sell orders for this symbol before re-adding
                        if self._has_recent_sell_order(symbol):
                            self.logger.info(f"Skipping re-add of {symbol} - recent sell order detected")
                            continue
                        
                        self.logger.info(f"Adding untracked position from Alpaca: {symbol} ({quantity} shares @ ${entry_price:.2f})")
                        trade = Trade(
                            symbol=symbol,
                            trade_type=TradeType.BUY,
                            quantity=quantity,
                            price=entry_price,
                            timestamp=datetime.now(),
                            order_id=f"alpaca_sync_{symbol}",
                            order_type=OrderType.MARKET,
                            notes="Position synced from Alpaca"
                        )
                        self.active_positions[symbol] = trade
                    else:
                        # Update quantity if it differs
                        tracked_trade = self.active_positions[symbol]
                        if abs(quantity - tracked_trade.quantity) > 0.0001:
                            self.logger.info(f"Updating quantity for {symbol}: {tracked_trade.quantity} -> {quantity}")
                            tracked_trade.quantity = quantity
                else:
                    # Position has zero or negative quantity - should not be tracked
                    if symbol in self.active_positions:
                        self.logger.info(f"Removing position {symbol} - quantity is {quantity} in Alpaca")
                        del self.active_positions[symbol]
            
            # Remove positions we're tracking that no longer exist in Alpaca or have zero quantity
            symbols_to_remove = []
            for symbol in list(self.active_positions.keys()):
                if symbol not in alpaca_symbols:
                    self.logger.info(f"Removing position {symbol} - no longer in Alpaca or has zero quantity")
                    symbols_to_remove.append(symbol)
            
            for symbol in symbols_to_remove:
                if symbol in self.active_positions:
                    del self.active_positions[symbol]
                
        except Exception as e:
            self.logger.error(f"Error refreshing positions from Alpaca: {e}")

    def update_positions(self) -> None:
        """Update active positions and pending orders."""
        try:
            current_time = time.time()
            
            # Only refresh positions from Alpaca if enough time has passed
            if current_time - self.last_position_refresh >= self.position_refresh_interval:
                self._refresh_positions_from_alpaca()
                self.last_position_refresh = current_time
                self.logger.debug(f"Position refresh completed (interval: {self.position_refresh_interval}s)")
            
            # Clean up expired recently removed positions
            self._cleanup_recently_removed_positions()
            
            self.logger.info(f"Checking positions - Active positions: {len(self.active_positions)}, Pending orders: {len(self.pending_orders)}")
            
            # Check pending orders using batch API call (only if enough time has passed)
            if current_time - self.last_order_batch_check >= self.order_check_interval:
                self._batch_check_pending_orders()
                self.last_order_batch_check = current_time
                self.logger.debug(f"Batch order check completed (interval: {self.order_check_interval}s)")
            
            # Check exit conditions for active positions
            for symbol in list(self.active_positions.keys()):
                try:
                    # Get current price
                    quote = self.alpaca_client.get_latest_quote(symbol)
                    if not quote:
                        continue
                        
                    current_price = quote.get('bid', 0)
                    if current_price <= 0:
                        continue
                    
                    trade = self.active_positions[symbol]
                    
                    # Check stop loss and take profit
                    if trade.trade_type == TradeType.BUY:
                        stop_loss_price = trade.price * (1 - self.stop_loss_pct)
                        take_profit_price = trade.price * (1 + self.take_profit_pct)
                        profit_pct = ((current_price - trade.price) / trade.price) * 100
                        
                        self.logger.info(f"Checking {symbol}: Entry=${trade.price:.2f}, Current=${current_price:.2f}, Profit={profit_pct:.2f}%, Take Profit Threshold={self.take_profit_pct*100:.2f}%")
                        
                        if current_price <= stop_loss_price:
                            self.logger.info(f"Stop loss triggered for {symbol} at ${current_price:.2f}")
                            self._execute_sell_order(symbol, "Stop loss triggered")
                        elif current_price >= take_profit_price:
                            self.logger.info(f"Take profit triggered for {symbol} at ${current_price:.2f} (profit: {profit_pct:.2f}%)")
                            self._execute_sell_order(symbol, "Take profit triggered")
                            
                except Exception as e:
                    self.logger.error(f"Error checking exit conditions for {symbol}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error in update_positions: {e}")

    def _cleanup_recently_removed_positions(self) -> None:
        """Clean up expired entries from recently_removed_positions."""
        try:
            current_time = time.time()
            expired_symbols = []
            
            for symbol, removal_time in self.recently_removed_positions.items():
                if current_time - removal_time >= self.removal_cooldown:
                    expired_symbols.append(symbol)
            
            for symbol in expired_symbols:
                del self.recently_removed_positions[symbol]
                self.logger.debug(f"Removed {symbol} from recently_removed_positions (cooldown expired)")
                
        except Exception as e:
            self.logger.error(f"Error cleaning up recently_removed_positions: {e}")

    def _has_recent_sell_order(self, symbol: str) -> bool:
        """Check if there's a recent sell order for the given symbol."""
        try:
            # Get recent orders for this symbol (last 24 hours)
            from datetime import datetime, timedelta
            since = datetime.now() - timedelta(hours=24)
            
            orders = self.alpaca_client.get_orders(
                status='all',
                limit=50,
                after=since.strftime('%Y-%m-%dT%H:%M:%SZ')
            )
            
            if not orders:
                return False
            
            # Check for recent sell orders for this symbol
            for order in orders:
                if (order.symbol == symbol and 
                    order.side == 'sell' and 
                    order.status in ['filled', 'partially_filled', 'new', 'pending_new']):
                    
                    # Check if the order is recent (within last 5 minutes)
                    order_time = datetime.fromisoformat(order.created_at.replace('Z', '+00:00'))
                    time_diff = datetime.now(order_time.tzinfo) - order_time
                    
                    if time_diff.total_seconds() < 300:  # 5 minutes
                        self.logger.info(f"Found recent sell order for {symbol}: {order.id} ({order.status})")
                        return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking recent sell orders for {symbol}: {e}")
            return False  # If we can't check, allow the position to be added

    def _batch_check_pending_orders(self) -> None:
        """Check all pending orders in a single batch API call."""
        if not self.pending_orders:
            return
            
        try:
            # Get all orders in a single API call
            all_orders = self.alpaca_client.get_orders(status='all', limit=100)
            if not all_orders:
                return
                
            # Create a lookup dictionary for faster access
            order_lookup = {order.id: order for order in all_orders}
            
            # Check each pending order
            for symbol, order_id in list(self.pending_orders.items()):
                # Validate order_id
                if not order_id or not isinstance(order_id, str) or order_id.strip() == "":
                    self.logger.warning(f"Invalid order_id for {symbol}: {order_id}. Removing from pending orders.")
                    del self.pending_orders[symbol]
                    continue
                
                # Look up the order in our batch result
                order = order_lookup.get(order_id)
                if not order:
                    self.logger.warning(f"Order {order_id} for {symbol} not found in batch results")
                    continue
                
                if order.status == 'filled':
                    # Update position status
                    if symbol in self.active_positions:
                        self.active_positions[symbol].status = TradeStatus.FILLED
                        self.logger.info(f"Order filled for {symbol}: {order.side} {order.qty} shares at ${order.filled_avg_price}")
                    
                    # Trigger callbacks
                    if self.account_update_callback:
                        self.account_update_callback()
                    if self.order_update_callback:
                        self.order_update_callback()
                    if self.position_update_callback:
                        self.position_update_callback()
                        
                    del self.pending_orders[symbol]
                    
                elif order.status in ['cancelled', 'rejected', 'expired']:
                    # Handle cancelled/rejected orders
                    if symbol in self.active_positions:
                        self.logger.info(f"Order {order.status} for {symbol}: {order.side} {order.qty} shares")
                        # Remove from active positions if order was cancelled
                        del self.active_positions[symbol]
                    
                    # Trigger callbacks
                    if self.order_update_callback:
                        self.order_update_callback()
                    if self.position_update_callback:
                        self.position_update_callback()
                        
                    del self.pending_orders[symbol]
                    
        except Exception as e:
            self.logger.error(f"Error in batch order checking: {e}")


# Keep backward compatibility
SimpleStrategy = EnhancedStrategy