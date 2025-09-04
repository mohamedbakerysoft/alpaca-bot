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
    
    def __init__(self, alpaca_client: AlpacaClient):
        """Initialize the scalping strategy.
        
        Args:
            alpaca_client: Alpaca API client instance.
        """
        self.alpaca_client = alpaca_client
        self.logger = logging.getLogger(__name__)
        self.error_handler = ErrorHandler(self.logger)
        
        # Strategy parameters from settings
        self.support_threshold = settings.support_threshold
        self.resistance_threshold = settings.resistance_threshold
        self.rsi_oversold = getattr(settings, 'rsi_oversold', 30.0)
        self.rsi_overbought = getattr(settings, 'rsi_overbought', 70.0)
        self.position_size = getattr(settings, 'position_size', settings.default_position_size)
        self.stop_loss_pct = settings.stop_loss_percentage
        self.take_profit_pct = getattr(settings, 'take_profit_percentage', 0.02)
        
        # Aggressive mode parameters
        self.aggressive_mode = getattr(settings, 'aggressive_mode', False)
        self._update_aggressive_parameters()
        
        # Active positions and orders
        self.active_positions: Dict[str, Trade] = {}
        self.pending_orders: Dict[str, str] = {}  # symbol -> order_id
        
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
            self.take_profit_pct = 0.015  # Lower take profit (1.5%)
            self.stop_loss_pct = 0.015  # Tighter stop loss (1.5%)
            self.logger.info("Aggressive mode enabled - using higher risk parameters")
        else:
            # Conservative parameters
            self.rsi_oversold = getattr(settings, 'rsi_oversold', 30.0)
            self.rsi_overbought = getattr(settings, 'rsi_overbought', 70.0)
            self.support_threshold = settings.support_threshold
            self.resistance_threshold = settings.resistance_threshold
            self.take_profit_pct = getattr(settings, 'take_profit_percentage', 0.02)
            self.stop_loss_pct = settings.stop_loss_percentage
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
        """Generate trading signals based on strategy rules.
        
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
        
        rsi = stock_data.technical_indicators.rsi
        bb_lower = stock_data.technical_indicators.bollinger_lower
        bb_upper = stock_data.technical_indicators.bollinger_upper
        
        # Find nearest support and resistance levels
        nearest_support = self._find_nearest_support(stock_data, current_price)
        nearest_resistance = self._find_nearest_resistance(stock_data, current_price)
        
        # Debug logging
        rsi_str = f"{rsi:.1f}" if rsi else "N/A"
        bb_lower_str = f"${bb_lower:.2f}" if bb_lower else "N/A"
        support_str = f"${nearest_support.price:.2f}" if nearest_support else "N/A"
        resistance_str = f"${nearest_resistance.price:.2f}" if nearest_resistance else "N/A"
        
        self.logger.info(f"{symbol}: Price=${current_price:.2f}, RSI={rsi_str}, "
                        f"BB_Lower={bb_lower_str}, Support={support_str}, Resistance={resistance_str}")
        
        # Buy signal conditions
        buy_conditions = []
        
        # Condition 1: Price near support level
        if nearest_support:
            distance_to_support = abs(current_price - nearest_support.price) / current_price
            self.logger.debug(f"{symbol}: Distance to support: {distance_to_support:.4f} (threshold: {self.support_threshold})")
            if distance_to_support <= self.support_threshold:
                buy_conditions.append(f"Near support at ${nearest_support.price:.2f}")
        else:
            self.logger.debug(f"{symbol}: No support levels found")
        
        # Condition 2: RSI oversold
        if rsi and rsi <= self.rsi_oversold:
            buy_conditions.append(f"RSI oversold ({rsi:.1f})")
        elif rsi:
            self.logger.debug(f"{symbol}: RSI not oversold: {rsi:.1f} > {self.rsi_oversold}")
        
        # Condition 3: Price near lower Bollinger Band
        if bb_lower and current_price <= bb_lower * 1.01:  # Within 1% of lower band
            buy_conditions.append(f"Near lower Bollinger Band (${bb_lower:.2f})")
        elif bb_lower:
            self.logger.debug(f"{symbol}: Price not near BB lower: ${current_price:.2f} > ${bb_lower * 1.01:.2f}")
        
        # Log conditions found
        self.logger.info(f"{symbol}: Buy conditions met: {len(buy_conditions)}/3 - {buy_conditions}")
        
        # Generate buy signal if conditions met
        if len(buy_conditions) >= 2:  # Require at least 2 conditions
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
            
            # Calculate position size
            account = self.alpaca_client.get_account()
            if not account:
                raise OrderExecutionError("Could not get account information")
            
            buying_power = float(account.buying_power)
            # Use position_size as a fixed dollar amount, not a multiplier
            max_position_value = min(self.position_size, buying_power * 0.95)  # Use 95% of buying power as max
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
        
        # Stop loss condition
        if pnl_pct <= -self.stop_loss_pct:
            return ("SELL", f"Stop loss triggered ({pnl_pct:.2%})")
        
        # Take profit condition
        if pnl_pct >= self.take_profit_pct:
            return ("SELL", f"Take profit triggered ({pnl_pct:.2%})")
        
        # Resistance level condition
        nearest_resistance = self._find_nearest_resistance(stock_data, current_price)
        if nearest_resistance:
            distance_to_resistance = abs(current_price - nearest_resistance.price) / current_price
            if distance_to_resistance <= self.resistance_threshold:
                return ("SELL", f"Near resistance at ${nearest_resistance.price:.2f}")
        
        # RSI overbought condition
        if stock_data.technical_indicators is None:
            return None
        
        rsi = stock_data.technical_indicators.rsi
        if rsi and rsi >= self.rsi_overbought:
            return ("SELL", f"RSI overbought ({rsi:.1f})")
        
        # Upper Bollinger Band condition
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