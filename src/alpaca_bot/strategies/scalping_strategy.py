"""Scalping strategy implementation for automated trading.

This module implements a scalping strategy that:
1. Identifies support and resistance levels
2. Buys at support levels
3. Sells before resistance levels
4. Manages risk and position sizing
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
from alpaca_trade_api.rest import REST

from ..config.settings import settings
from ..models.stock import StockData, StockQuote, SupportResistanceLevel, TechnicalIndicators
from ..models.trade import Trade, TradeType, OrderType, TradeStatus
from ..services.alpaca_client import AlpacaClient
from ..utils.technical_analysis import (
    identify_support_resistance_levels,
    calculate_rsi,
    calculate_bollinger_bands,
    calculate_sma
)
from ..utils.logging_utils import trade_logger
from ..utils.error_handler import (
    ErrorHandler, MarketDataError, OrderExecutionError,
    safe_execute
)


class ScalpingStrategy:
    """Scalping strategy for automated trading."""
    
    def __init__(self, alpaca_client: AlpacaClient, account_update_callback=None, order_update_callback=None):
        """Initialize the scalping strategy.
        
        Args:
            alpaca_client: Alpaca API client instance.
            account_update_callback: Callback function to trigger account updates.
            order_update_callback: Callback function to trigger order display updates.
        """
        self.alpaca_client = alpaca_client
        self.logger = logging.getLogger(__name__)
        self.error_handler = ErrorHandler(self.logger)
        self.account_update_callback = account_update_callback
        self.order_update_callback = order_update_callback
        
        # Strategy parameters from settings
        self.support_threshold = settings.support_threshold
        self.resistance_threshold = settings.resistance_threshold
        self.rsi_oversold = getattr(settings, 'rsi_oversold', 30.0)
        self.rsi_overbought = getattr(settings, 'rsi_overbought', 70.0)
        self.position_size = getattr(settings, 'position_size', settings.default_position_size)
        self.stop_loss_pct = settings.stop_loss_percentage
        self.take_profit_pct = getattr(settings, 'take_profit_percentage', 0.02)
        
        # Enhanced exit parameters
        self.trailing_stop_enabled = True
        self.trailing_stop_pct = 0.01  # 1% trailing stop
        self.min_profit_for_trailing = 0.005  # 0.5% minimum profit before enabling trailing
        self.dynamic_exit_enabled = True
        
        # Aggressive mode parameters
        self.aggressive_mode = getattr(settings, 'aggressive_mode', False)
        self._update_aggressive_parameters()
        
        # Active positions and orders
        self.active_positions: Dict[str, Trade] = {}
        self.pending_orders: Dict[str, str] = {}  # symbol -> order_id
        self.position_high_prices: Dict[str, float] = {}  # Track highest price for trailing stops
        
        # Price data cache
        self.price_data_cache: Dict[str, StockData] = {}
        self.last_update: Dict[str, datetime] = {}
        
        self.logger.info("Scalping strategy initialized")
    
    def _update_aggressive_parameters(self) -> None:
        """Update strategy parameters based on aggressive mode."""
        if self.aggressive_mode:
            # More aggressive parameters for higher risk/reward
            self.rsi_oversold = 35.0  # Less oversold threshold
            self.rsi_overbought = 65.0  # Less overbought threshold
            self.support_threshold = 0.005  # Tighter support threshold (0.5%)
            self.resistance_threshold = 0.005  # Tighter resistance threshold (0.5%)
            self.take_profit_pct = 0.025  # Higher take profit (2.5%)
            self.stop_loss_pct = 0.012  # Tighter stop loss (1.2%)
            self.trailing_stop_pct = 0.008  # Tighter trailing stop (0.8%)
            self.min_profit_for_trailing = 0.003  # Lower threshold for trailing (0.3%)
            self.logger.info("Aggressive mode enabled - using higher risk parameters")
        else:
            # Conservative parameters
            self.rsi_oversold = getattr(settings, 'rsi_oversold', 30.0)
            self.rsi_overbought = getattr(settings, 'rsi_overbought', 70.0)
            self.support_threshold = settings.support_threshold
            self.resistance_threshold = settings.resistance_threshold
            self.take_profit_pct = getattr(settings, 'take_profit_percentage', 0.02)
            self.stop_loss_pct = settings.stop_loss_percentage
            self.trailing_stop_pct = 0.01  # Standard trailing stop (1%)
            self.min_profit_for_trailing = 0.005  # Standard threshold for trailing (0.5%)
            self.logger.info("Conservative mode enabled - using standard risk parameters")
    
    def set_aggressive_mode(self, aggressive: bool) -> None:
        """Set aggressive mode and update parameters.
        
        Args:
            aggressive: Whether to enable aggressive mode.
        """
        self.aggressive_mode = aggressive
        self._update_aggressive_parameters()
    
    def analyze_symbol(self, symbol: str, timeframe: str = '1Min', 
                      lookback_periods: int = 100) -> Optional[StockData]:
        """Analyze a symbol and return stock data with technical indicators.
        
        Args:
            symbol: Stock symbol to analyze.
            timeframe: Timeframe for analysis (1Min, 5Min, etc.).
            lookback_periods: Number of periods to look back.
            
        Returns:
            StockData: Stock data with technical analysis, or None if error.
        """
        def _perform_analysis():
            # Check cache freshness
            now = datetime.now()
            if (symbol in self.last_update and 
                now - self.last_update[symbol] < timedelta(minutes=1)):
                return self.price_data_cache.get(symbol)
            
            # Get historical data
            end_time = now
            start_time = end_time - timedelta(days=5)  # 5 days of data
            
            bars = self.alpaca_client.get_bars(
                symbol=symbol,
                timeframe=timeframe,
                start=start_time,
                end=end_time,
                limit=lookback_periods
            )
            
            if bars is None or len(bars) < 20:
                raise MarketDataError(f"Insufficient data for {symbol}")

            # bars is already a DataFrame from get_bars method
            df = bars
            
            # Calculate technical indicators
            df['sma_20'] = calculate_sma(df['close'], 20)
            df['rsi'] = calculate_rsi(df['close'])
            
            # Calculate Bollinger Bands
            bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(df['close'])
            df['bollinger_upper'] = bb_upper
            df['bollinger_middle'] = bb_middle
            df['bollinger_lower'] = bb_lower
            
            # Calculate support and resistance levels
            self.logger.info(f"{symbol}: DataFrame shape for S/R calculation: {df.shape}")
            self.logger.info(f"{symbol}: DataFrame columns: {df.columns.tolist()}")
            self.logger.info(f"{symbol}: Price range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")
            
            support_levels, resistance_levels = identify_support_resistance_levels(
                df, window=10, min_touches=1, tolerance_percent=1.0
            )
            
            self.logger.info(f"{symbol}: Found {len(support_levels)} support levels, {len(resistance_levels)} resistance levels")
            
            # Get current quote
            quote = self.alpaca_client.get_latest_quote(symbol)
            if not quote:
                raise MarketDataError(f"Could not get quote for {symbol}")
            
            current_quote = StockQuote(
                symbol=symbol,
                bid=quote['bid'],
                ask=quote['ask'],
                bid_size=quote['bid_size'],
                ask_size=quote['ask_size'],
                timestamp=datetime.now()  # Use current time since IEX doesn't provide timestamp in the dict
            )
            
            # Create stock data object
            stock_data = StockData(
                symbol=symbol,
                company_name=symbol,  # Use symbol as company name for now
                current_quote=current_quote,
                support_levels=support_levels,
                resistance_levels=resistance_levels,
                technical_indicators=TechnicalIndicators(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    rsi=df['rsi'].iloc[-1] if not pd.isna(df['rsi'].iloc[-1]) else None,
                    sma_20=df['sma_20'].iloc[-1] if not pd.isna(df['sma_20'].iloc[-1]) else None,
                    bollinger_upper=df['bollinger_upper'].iloc[-1] if not pd.isna(df['bollinger_upper'].iloc[-1]) else None,
                     bollinger_middle=df['bollinger_middle'].iloc[-1] if not pd.isna(df['bollinger_middle'].iloc[-1]) else None,
                     bollinger_lower=df['bollinger_lower'].iloc[-1] if not pd.isna(df['bollinger_lower'].iloc[-1]) else None,
                )
            )
            
            # Update cache
            self.price_data_cache[symbol] = stock_data
            self.last_update[symbol] = now
            
            return stock_data
        
        return safe_execute(
            _perform_analysis,
            default_return=None,
            log_errors=True
        )
    
    def generate_signals(self, stock_data: StockData) -> List[Tuple[str, str]]:
        """Generate trading signals based on enhanced strategy rules.
        
        Args:
            stock_data: Stock data with technical analysis.
            
        Returns:
            List of (signal_type, reason) tuples.
        """
        signals = []
        symbol = stock_data.symbol
        current_price = stock_data.current_quote.ask
        
        # Skip if already have position or pending order
        if symbol in self.active_positions or symbol in self.pending_orders:
            self.logger.debug(f"{symbol}: Skipping - already have position or pending order")
            return signals
        
        # Get technical indicators
        if stock_data.technical_indicators is None:
            self.logger.debug(f"{symbol}: No technical indicators available")
            return signals
        
        # Check market conditions first
        if not self._is_favorable_market_condition(stock_data):
            self.logger.debug(f"{symbol}: Unfavorable market conditions, skipping")
            return signals
        
        rsi = stock_data.technical_indicators.rsi
        sma_20 = stock_data.technical_indicators.sma_20
        bb_lower = stock_data.technical_indicators.bollinger_lower
        bb_upper = stock_data.technical_indicators.bollinger_upper
        bb_middle = stock_data.technical_indicators.bollinger_middle
        
        # Find nearest support and resistance levels
        nearest_support = self._find_nearest_support(stock_data, current_price)
        nearest_resistance = self._find_nearest_resistance(stock_data, current_price)
        
        # Debug logging
        rsi_str = f"{rsi:.1f}" if rsi else "N/A"
        sma_str = f"${sma_20:.2f}" if sma_20 else "N/A"
        bb_lower_str = f"${bb_lower:.2f}" if bb_lower else "N/A"
        support_str = f"${nearest_support.price:.2f}" if nearest_support else "N/A"
        resistance_str = f"${nearest_resistance.price:.2f}" if nearest_resistance else "N/A"
        
        self.logger.info(f"{symbol}: Price=${current_price:.2f}, RSI={rsi_str}, SMA20={sma_str}, "
                        f"BB_Lower={bb_lower_str}, Support={support_str}, Resistance={resistance_str}")
        
        # Enhanced buy signal conditions
        buy_conditions = []
        condition_scores = []
        
        # Condition 1: Price near support level (High priority)
        if nearest_support:
            distance_to_support = abs(current_price - nearest_support.price) / current_price
            self.logger.debug(f"{symbol}: Distance to support: {distance_to_support:.4f} (threshold: {self.support_threshold})")
            if distance_to_support <= self.support_threshold:
                buy_conditions.append(f"Near support at ${nearest_support.price:.2f}")
                condition_scores.append(3)  # High score for support
        
        # Condition 2: RSI oversold with momentum check
        if rsi:
            if rsi <= self.rsi_oversold:
                buy_conditions.append(f"RSI oversold ({rsi:.1f})")
                condition_scores.append(2)
            elif rsi <= self.rsi_oversold + 5:  # Slightly oversold
                buy_conditions.append(f"RSI approaching oversold ({rsi:.1f})")
                condition_scores.append(1)
        
        # Condition 3: Price near lower Bollinger Band
        if bb_lower and current_price <= bb_lower * 1.02:  # Within 2% of lower band
            buy_conditions.append(f"Near lower Bollinger Band (${bb_lower:.2f})")
            condition_scores.append(2)
        
        # Condition 4: Trend confirmation (price above SMA in uptrend)
        if sma_20 and current_price > sma_20 * 0.98:  # Within 2% of SMA
            buy_conditions.append(f"Price near/above SMA20 (${sma_20:.2f})")
            condition_scores.append(1)
        
        # Condition 5: Bollinger Band squeeze (low volatility)
        if bb_upper and bb_lower and bb_middle:
            bb_width = (bb_upper - bb_lower) / bb_middle
            if bb_width < 0.1:  # Tight bands indicate low volatility
                buy_conditions.append("Low volatility (BB squeeze)")
                condition_scores.append(1)
        
        # Condition 6: Risk/Reward ratio check
        if nearest_resistance and nearest_support:
            potential_profit = nearest_resistance.price - current_price
            potential_loss = current_price - nearest_support.price
            if potential_loss > 0 and potential_profit / potential_loss >= 2.0:  # 2:1 ratio
                buy_conditions.append(f"Good R/R ratio ({potential_profit/potential_loss:.1f}:1)")
                condition_scores.append(2)
        
        # Calculate total score
        total_score = sum(condition_scores)
        min_score = 4 if self.aggressive_mode else 5  # Lower threshold for aggressive mode
        
        # Log conditions found
        self.logger.info(f"{symbol}: Buy conditions met: {len(buy_conditions)} (score: {total_score}/{min_score}) - {buy_conditions}")
        
        # Generate buy signal if conditions and score met
        if len(buy_conditions) >= 2 and total_score >= min_score:
            reason = "; ".join(buy_conditions)
            signals.append(("BUY", reason))
            trade_logger.log_trade_signal(symbol, "BUY", current_price, reason)
        
        return signals
    
    def execute_trade(self, symbol: str, signal_type: str, reason: str) -> Optional[Trade]:
        """Execute a trade based on the signal.
        
        Args:
            symbol: Stock symbol.
            signal_type: Type of signal (BUY/SELL).
            reason: Reason for the trade.
            
        Returns:
            Trade object if successful, None otherwise.
        """
        def _perform_trade():
            if signal_type == "BUY":
                return self._execute_buy_order(symbol, reason)
            elif signal_type == "SELL":
                return self._execute_sell_order(symbol, reason)
            else:
                raise OrderExecutionError(f"Unknown signal type: {signal_type}")
        
        def _handle_trade_error(error: Exception):
            trade_logger.log_error(symbol, "EXECUTION_ERROR", str(error))
            return None
        
        return safe_execute(
            _perform_trade,
            default_return=None,
            log_errors=True
        )
    
    def _execute_buy_order(self, symbol: str, reason: str) -> Optional[Trade]:
        """Execute a buy order.
        
        Args:
            symbol: Stock symbol.
            reason: Reason for the trade.
            
        Returns:
            Trade object if successful, None otherwise.
        """
        def _place_buy_order():
            # Get current quote
            quote = self.alpaca_client.get_latest_quote(symbol)
            if not quote:
                raise MarketDataError(f"Could not get quote for {symbol}")
            
            # Calculate dynamic position size
            account = self.alpaca_client.get_account()
            if not account:
                raise OrderExecutionError("Could not get account information")
            
            buying_power = float(account.buying_power)
            
            # Get dynamic position size based on volatility and market conditions
            dynamic_position_size = self._calculate_dynamic_position_size(symbol, quote['ask'], buying_power)
            max_position_value = min(dynamic_position_size, buying_power * 0.95)  # Use 95% of buying power as max
            quantity = int(max_position_value / quote['ask'])
            
            if quantity <= 0:
                raise OrderExecutionError(f"Insufficient buying power for {symbol}")
            
            # Place market buy order
            order = self.alpaca_client.place_order(
                symbol=symbol,
                qty=quantity,
                side='buy',
                order_type='market',
                time_in_force='day'
            )
            
            if not order:
                raise OrderExecutionError(f"Failed to place buy order for {symbol}")
            
            # Create trade object
            trade = Trade(
                symbol=symbol,
                trade_type=TradeType.BUY,
                quantity=quantity,
                price=quote['ask'],
                timestamp=datetime.now(),
                order_id=order.id,
                status=TradeStatus.PENDING,
                notes=reason
            )
            
            # Track the order
            self.pending_orders[symbol] = order.id
            
            trade_logger.log_order_placed(
                symbol, 'buy', quantity, 'market', order_id=order.id
            )
            
            self.logger.info(f"Buy order placed for {symbol}: {quantity} shares")
            
            # Trigger account update callback if available
            if self.account_update_callback:
                self.account_update_callback()
            
            # Trigger order update callback if available
            if self.order_update_callback:
                self.order_update_callback()
            
            return trade
        
        return safe_execute(
            _place_buy_order,
            default_return=None,
            log_errors=True
        )
    
    def _execute_sell_order(self, symbol: str, reason: str) -> Optional[Trade]:
        """Execute a sell order for existing position.
        
        Args:
            symbol: Stock symbol.
            reason: Reason for the trade.
            
        Returns:
            Trade object if successful, None otherwise.
        """
        def _place_sell_order():
            # Check if we have a position
            if symbol not in self.active_positions:
                raise OrderExecutionError(f"No active position for {symbol}")
            
            position_trade = self.active_positions[symbol]
            
            # Place market sell order
            order = self.alpaca_client.place_order(
                symbol=symbol,
                qty=position_trade.quantity,
                side='sell',
                order_type='market',
                time_in_force='day'
            )
            
            if not order:
                raise OrderExecutionError(f"Failed to place sell order for {symbol}")
            
            # Get current quote for exit price
            quote = self.alpaca_client.get_latest_quote(symbol)
            exit_price = quote['bid'] if quote else position_trade.price
            
            # Create sell trade object
            trade = Trade(
                symbol=symbol,
                trade_type=TradeType.SELL,
                quantity=position_trade.quantity,
                price=exit_price,
                timestamp=datetime.now(),
                order_id=order.id,
                status=TradeStatus.PENDING,
                notes=reason
            )
            
            # Track the order
            self.pending_orders[symbol] = order.id
            
            trade_logger.log_order_placed(
                symbol, 'sell', position_trade.quantity, 'market', order_id=order.id
            )
            
            self.logger.info(f"Sell order placed for {symbol}: {position_trade.quantity} shares")
            
            # Trigger account update callback if available
            if self.account_update_callback:
                self.account_update_callback()
            
            # Trigger order update callback if available
            if self.order_update_callback:
                self.order_update_callback()
            
            return trade
        
        return safe_execute(
            _place_sell_order,
            default_return=None,
            log_errors=True
        )
    
    def check_exit_conditions(self, symbol: str) -> Optional[Tuple[str, str]]:
        """Check if exit conditions are met for an active position.
        
        Args:
            symbol: Stock symbol.
            
        Returns:
            Tuple of (signal_type, reason) if exit needed, None otherwise.
        """
        if symbol not in self.active_positions:
            return None
        
        position = self.active_positions[symbol]
        stock_data = self.analyze_symbol(symbol)
        
        if not stock_data:
            return None
        
        current_price = stock_data.current_quote.bid
        entry_price = position.price
        
        # Calculate profit/loss percentage
        pnl_pct = (current_price - entry_price) / entry_price
        
        # Update highest price for trailing stop
        if symbol not in self.position_high_prices:
            self.position_high_prices[symbol] = current_price
        else:
            self.position_high_prices[symbol] = max(self.position_high_prices[symbol], current_price)
        
        # Enhanced stop loss with trailing functionality
        if self.trailing_stop_enabled and pnl_pct >= self.min_profit_for_trailing:
            # Use trailing stop once we're in profit
            highest_price = self.position_high_prices[symbol]
            trailing_stop_price = highest_price * (1 - self.trailing_stop_pct)
            
            if current_price <= trailing_stop_price:
                return ("SELL", f"Trailing stop triggered at ${trailing_stop_price:.2f} (High: ${highest_price:.2f})")
        else:
            # Regular stop loss
            if pnl_pct <= -self.stop_loss_pct:
                return ("SELL", f"Stop loss triggered ({pnl_pct:.2%})")
        
        # Dynamic take profit based on volatility and momentum
        if self.dynamic_exit_enabled:
            dynamic_take_profit = self._calculate_dynamic_take_profit(stock_data, pnl_pct)
            if pnl_pct >= dynamic_take_profit:
                return ("SELL", f"Dynamic take profit triggered ({pnl_pct:.2%}, target: {dynamic_take_profit:.2%})")
        else:
            # Standard take profit condition
            if pnl_pct >= self.take_profit_pct:
                return ("SELL", f"Take profit triggered ({pnl_pct:.2%})")
        
        # Enhanced resistance level condition with momentum check
        nearest_resistance = self._find_nearest_resistance(stock_data, current_price)
        if nearest_resistance:
            distance_to_resistance = abs(current_price - nearest_resistance.price) / current_price
            if distance_to_resistance <= self.resistance_threshold:
                # Check if momentum is weakening near resistance
                if self._is_momentum_weakening(stock_data):
                    return ("SELL", f"Near resistance with weak momentum at ${nearest_resistance.price:.2f}")
        
        # RSI overbought condition with stricter threshold when profitable
        if stock_data.technical_indicators is None:
            return None
        
        rsi = stock_data.technical_indicators.rsi
        if rsi:
            # Use stricter RSI threshold when in profit
            rsi_threshold = self.rsi_overbought - 5 if pnl_pct > 0.01 else self.rsi_overbought
            if rsi >= rsi_threshold:
                return ("SELL", f"RSI overbought ({rsi:.1f}, threshold: {rsi_threshold:.1f})")
        
        # Upper Bollinger Band condition with volume confirmation
        bb_upper = stock_data.technical_indicators.bollinger_upper
        if bb_upper and current_price >= bb_upper * 0.99:  # Within 1% of upper band
            return ("SELL", f"Near upper Bollinger Band (${bb_upper:.2f})")
        
        return None
    
    def update_positions(self) -> None:
        """Update active positions and pending orders."""
        def _update_all_positions():
            # Check pending orders
            for symbol, order_id in list(self.pending_orders.items()):
                order = self.alpaca_client.get_order(order_id)
                if not order:
                    continue
                
                if order.status == 'filled':
                    self._handle_order_filled(symbol, order)
                    del self.pending_orders[symbol]
                elif order.status in ['cancelled', 'rejected', 'expired']:
                    self._handle_order_cancelled(symbol, order)
                    del self.pending_orders[symbol]
            
            # Check exit conditions for active positions
            for symbol in list(self.active_positions.keys()):
                exit_signal = self.check_exit_conditions(symbol)
                if exit_signal:
                    signal_type, reason = exit_signal
                    self.execute_trade(symbol, signal_type, reason)
        
        safe_execute(
            _update_all_positions,
            default_return=None,
            log_errors=True
        )
    
    def _handle_order_filled(self, symbol: str, order) -> None:
        """Handle a filled order.
        
        Args:
            symbol: Stock symbol.
            order: Filled order object.
        """
        def _process_filled_order():
            fill_price = float(order.filled_avg_price)
            quantity = int(order.filled_qty)
            
            trade_logger.log_order_filled(
                symbol, order.side, quantity, fill_price, order.id
            )
            
            if order.side == 'buy':
                # Create new position
                trade = Trade(
                    symbol=symbol,
                    trade_type=TradeType.BUY,
                    quantity=quantity,
                    price=fill_price,
                    timestamp=datetime.now(),
                    order_id=order.id,
                    status=TradeStatus.FILLED
                )
                self.active_positions[symbol] = trade
                
                trade_logger.log_position_opened(symbol, quantity, fill_price)
                
            elif order.side == 'sell':
                # Close existing position
                if symbol in self.active_positions:
                    position = self.active_positions[symbol]
                    pnl = (fill_price - position.price) * quantity
                    
                    trade_logger.log_position_closed(
                        symbol, quantity, position.price, fill_price, pnl
                    )
                    
                    del self.active_positions[symbol]
        
        safe_execute(
            _process_filled_order,
            default_return=None,
            log_errors=True
        )
    
    def _handle_order_cancelled(self, symbol: str, order) -> None:
        """Handle a cancelled order.
        
        Args:
            symbol: Stock symbol.
            order: Cancelled order object.
        """
        trade_logger.log_order_cancelled(symbol, order.id, order.status)
        self.logger.info(f"Order cancelled for {symbol}: {order.id} ({order.status})")
    
    def _find_nearest_support(self, stock_data: StockData, 
                             current_price: float) -> Optional[SupportResistanceLevel]:
        """Find the nearest support level below current price.
        
        Args:
            stock_data: Stock data with support levels.
            current_price: Current stock price.
            
        Returns:
            Nearest support level or None.
        """
        support_levels = [level for level in stock_data.support_levels 
                         if level.price < current_price]
        
        if not support_levels:
            return None
        
        return max(support_levels, key=lambda x: x.price)
    
    def _find_nearest_resistance(self, stock_data: StockData, 
                                current_price: float) -> Optional[SupportResistanceLevel]:
        """Find the nearest resistance level above current price.
        
        Args:
            stock_data: Stock data with resistance levels.
            current_price: Current stock price.
            
        Returns:
            Nearest resistance level or None.
        """
        resistance_levels = [level for level in stock_data.resistance_levels 
                           if level.price > current_price]
        
        if not resistance_levels:
            return None
        
        return min(resistance_levels, key=lambda x: x.price)
    
    def _calculate_dynamic_take_profit(self, stock_data: StockData, current_pnl_pct: float) -> float:
        """Calculate dynamic take profit based on volatility and momentum.
        
        Args:
            stock_data: Stock data with technical indicators.
            current_pnl_pct: Current profit/loss percentage.
            
        Returns:
            Dynamic take profit percentage.
        """
        base_take_profit = self.take_profit_pct
        
        # Adjust based on RSI momentum
        if stock_data.technical_indicators and stock_data.technical_indicators.rsi:
            rsi = stock_data.technical_indicators.rsi
            if rsi > 60:  # Strong momentum, increase target
                base_take_profit *= 1.2
            elif rsi < 40:  # Weak momentum, reduce target
                base_take_profit *= 0.8
        
        # Adjust based on Bollinger Band position
        if (stock_data.technical_indicators and 
            stock_data.technical_indicators.bollinger_upper and 
            stock_data.technical_indicators.bollinger_lower):
            
            current_price = stock_data.current_quote.bid
            bb_upper = stock_data.technical_indicators.bollinger_upper
            bb_lower = stock_data.technical_indicators.bollinger_lower
            bb_width = bb_upper - bb_lower
            
            # If price is in upper half of BB, increase target
            bb_position = (current_price - bb_lower) / bb_width
            if bb_position > 0.7:
                base_take_profit *= 1.15
        
        # Ensure minimum and maximum bounds
        return max(0.01, min(base_take_profit, 0.05))  # Between 1% and 5%
    
    def _is_momentum_weakening(self, stock_data: StockData) -> bool:
        """Check if momentum is weakening based on technical indicators.
        
        Args:
            stock_data: Stock data with technical indicators.
            
        Returns:
            True if momentum is weakening, False otherwise.
        """
        if not stock_data.technical_indicators:
            return False
        
        # Check RSI divergence (simplified)
        rsi = stock_data.technical_indicators.rsi
        if rsi and rsi > 70:  # Overbought territory
            return True
        
        # Check if price is at upper Bollinger Band with high RSI
        if (rsi and rsi > 65 and 
            stock_data.technical_indicators.bollinger_upper):
            current_price = stock_data.current_quote.bid
            bb_upper = stock_data.technical_indicators.bollinger_upper
            if current_price >= bb_upper * 0.98:  # Within 2% of upper band
                return True
        
        return False
    
    def _is_favorable_market_condition(self, stock_data: StockData) -> bool:
        """Check if market conditions are favorable for trading.
        
        Args:
            stock_data: Stock data with technical indicators.
            
        Returns:
            True if conditions are favorable, False otherwise.
        """
        if not stock_data.technical_indicators:
            return True  # Default to favorable if no data
        
        current_price = stock_data.current_quote.bid
        
        # Check for extreme volatility (avoid trading in highly volatile conditions)
        if (stock_data.technical_indicators.bollinger_upper and 
            stock_data.technical_indicators.bollinger_lower and
            stock_data.technical_indicators.bollinger_middle):
            
            bb_upper = stock_data.technical_indicators.bollinger_upper
            bb_lower = stock_data.technical_indicators.bollinger_lower
            bb_middle = stock_data.technical_indicators.bollinger_middle
            bb_width = (bb_upper - bb_lower) / bb_middle
            
            # Avoid trading when volatility is too high
            if bb_width > 0.25:  # 25% width indicates high volatility
                self.logger.debug(f"{stock_data.symbol}: High volatility detected (BB width: {bb_width:.3f})")
                return False
        
        # Check for extreme RSI conditions (avoid whipsaws)
        rsi = stock_data.technical_indicators.rsi
        if rsi:
            # Avoid trading when RSI is in extreme territory (potential reversal)
            if rsi > 80 or rsi < 15:
                self.logger.debug(f"{stock_data.symbol}: Extreme RSI detected ({rsi:.1f})")
                return False
        
        # Check bid-ask spread (avoid trading with wide spreads)
        bid = stock_data.current_quote.bid
        ask = stock_data.current_quote.ask
        if bid and ask:
            spread_pct = (ask - bid) / bid
            if spread_pct > 0.01:  # 1% spread threshold
                self.logger.debug(f"{stock_data.symbol}: Wide spread detected ({spread_pct:.3f})")
                return False
        
        # Check for gap conditions (avoid trading right after large gaps)
        if (stock_data.technical_indicators.sma_20 and 
            abs(current_price - stock_data.technical_indicators.sma_20) / stock_data.technical_indicators.sma_20 > 0.05):
            self.logger.debug(f"{stock_data.symbol}: Large gap from SMA20 detected")
            return False
        
        return True
    
    def _calculate_dynamic_position_size(self, symbol: str, current_price: float, buying_power: float) -> float:
        """Calculate dynamic position size based on volatility and market conditions.
        
        Args:
            symbol: Stock symbol.
            current_price: Current stock price.
            buying_power: Available buying power.
            
        Returns:
            Dynamic position size in dollars.
        """
        base_position_size = self.position_size
        
        # Get stock data for volatility analysis
        stock_data = self.price_data_cache.get(symbol)
        if not stock_data or not stock_data.technical_indicators:
            return base_position_size
        
        # Volatility adjustment based on Bollinger Bands
        volatility_multiplier = 1.0
        if (stock_data.technical_indicators.bollinger_upper and 
            stock_data.technical_indicators.bollinger_lower and
            stock_data.technical_indicators.bollinger_middle):
            
            bb_upper = stock_data.technical_indicators.bollinger_upper
            bb_lower = stock_data.technical_indicators.bollinger_lower
            bb_middle = stock_data.technical_indicators.bollinger_middle
            bb_width = (bb_upper - bb_lower) / bb_middle
            
            # Reduce position size for high volatility
            if bb_width > 0.15:  # High volatility
                volatility_multiplier = 0.7
            elif bb_width > 0.10:  # Medium volatility
                volatility_multiplier = 0.85
            elif bb_width < 0.05:  # Low volatility
                volatility_multiplier = 1.2
        
        # Account balance adjustment (Kelly Criterion inspired)
        account_multiplier = 1.0
        if buying_power > 50000:  # Large account
            account_multiplier = 1.1
        elif buying_power < 10000:  # Small account
            account_multiplier = 0.8
        
        # RSI-based adjustment (reduce size in extreme conditions)
        rsi_multiplier = 1.0
        rsi = stock_data.technical_indicators.rsi
        if rsi:
            if rsi > 75 or rsi < 25:  # Extreme conditions
                rsi_multiplier = 0.8
            elif 45 <= rsi <= 55:  # Neutral conditions
                rsi_multiplier = 1.1
        
        # Price-based adjustment (smaller positions for higher-priced stocks)
        price_multiplier = 1.0
        if current_price > 200:
            price_multiplier = 0.8
        elif current_price > 100:
            price_multiplier = 0.9
        elif current_price < 20:
            price_multiplier = 1.2
        
        # Aggressive mode adjustment
        mode_multiplier = 1.3 if self.aggressive_mode else 1.0
        
        # Calculate final position size
        dynamic_size = (base_position_size * 
                       volatility_multiplier * 
                       account_multiplier * 
                       rsi_multiplier * 
                       price_multiplier * 
                       mode_multiplier)
        
        # Ensure reasonable bounds (between 10% and 200% of base size)
        min_size = base_position_size * 0.1
        max_size = base_position_size * 2.0
        dynamic_size = max(min_size, min(dynamic_size, max_size))
        
        # Log the calculation for debugging
        self.logger.debug(f"{symbol}: Dynamic position sizing - "
                         f"Base: ${base_position_size:.0f}, "
                         f"Vol: {volatility_multiplier:.2f}, "
                         f"Acc: {account_multiplier:.2f}, "
                         f"RSI: {rsi_multiplier:.2f}, "
                         f"Price: {price_multiplier:.2f}, "
                         f"Mode: {mode_multiplier:.2f}, "
                         f"Final: ${dynamic_size:.0f}")
        
        return dynamic_size
     
    def get_strategy_status(self) -> Dict:
        """Get current strategy status.
        
        Returns:
            Dictionary with strategy status information.
        """
        return {
            'active_positions': len(self.active_positions),
            'pending_orders': len(self.pending_orders),
            'positions': {symbol: {
                'quantity': trade.quantity,
                'entry_price': trade.price,
                'current_pnl': self._calculate_position_pnl(symbol, trade)
            } for symbol, trade in self.active_positions.items()},
            'strategy_parameters': {
                'support_threshold': self.support_threshold,
                'resistance_threshold': self.resistance_threshold,
                'rsi_oversold': self.rsi_oversold,
                'rsi_overbought': self.rsi_overbought,
                'position_size': self.position_size,
                'stop_loss_pct': self.stop_loss_pct,
                'take_profit_pct': self.take_profit_pct
            }
        }
    
    def _calculate_position_pnl(self, symbol: str, trade: Trade) -> float:
        """Calculate current P&L for a position.
        
        Args:
            symbol: Stock symbol.
            trade: Trade object.
            
        Returns:
            Current profit/loss.
        """
        def _calculate_pnl():
            quote = self.alpaca_client.get_latest_quote(symbol)
            if not quote:
                raise MarketDataError(f"Could not get quote for P&L calculation: {symbol}")
            
            current_price = quote['bid']
            return (current_price - trade.price) * trade.quantity
        
        return safe_execute(
            _calculate_pnl,
            error_handler=self.error_handler,
            operation=f"P&L calculation for {symbol}",
            on_error=lambda e: 0.0
        )