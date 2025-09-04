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
from ..models.stock import StockData, StockQuote, SupportResistanceLevel
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
        self.support_threshold = settings.SUPPORT_THRESHOLD
        self.resistance_threshold = settings.RESISTANCE_THRESHOLD
        self.rsi_oversold = settings.RSI_OVERSOLD
        self.rsi_overbought = settings.RSI_OVERBOUGHT
        self.position_size = settings.POSITION_SIZE
        self.stop_loss_pct = settings.STOP_LOSS_PCT
        self.take_profit_pct = settings.TAKE_PROFIT_PCT
        
        # Active positions and orders
        self.active_positions: Dict[str, Trade] = {}
        self.pending_orders: Dict[str, str] = {}  # symbol -> order_id
        
        # Price data cache
        self.price_data_cache: Dict[str, StockData] = {}
        self.last_update: Dict[str, datetime] = {}
        
        self.logger.info("Scalping strategy initialized")
    
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
                start=start_time.isoformat(),
                end=end_time.isoformat(),
                limit=lookback_periods
            )
            
            if not bars or len(bars) < 20:
                raise MarketDataError(f"Insufficient data for {symbol}")
            
            # Convert to DataFrame for analysis
            df = pd.DataFrame([
                {
                    'timestamp': bar.timestamp,
                    'open': bar.open,
                    'high': bar.high,
                    'low': bar.low,
                    'close': bar.close,
                    'volume': bar.volume
                }
                for bar in bars
            ])
            
            # Calculate technical indicators
            df['sma_20'] = calculate_sma(df['close'], 20)
            df['rsi'] = calculate_rsi(df['close'])
            
            # Calculate Bollinger Bands
            bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(df['close'])
            df['bb_upper'] = bb_upper
            df['bb_middle'] = bb_middle
            df['bb_lower'] = bb_lower
            
            # Calculate support and resistance levels
            support_levels, resistance_levels = identify_support_resistance_levels(
                df['high'].values, df['low'].values, df['close'].values
            )
            
            # Get current quote
            quote = self.alpaca_client.get_latest_quote(symbol)
            if not quote:
                raise MarketDataError(f"Could not get quote for {symbol}")
            
            current_quote = StockQuote(
                symbol=symbol,
                bid_price=quote.bid_price,
                ask_price=quote.ask_price,
                bid_size=quote.bid_size,
                ask_size=quote.ask_size,
                timestamp=quote.timestamp
            )
            
            # Create stock data object
            stock_data = StockData(
                symbol=symbol,
                current_quote=current_quote,
                support_levels=support_levels,
                resistance_levels=resistance_levels,
                technical_indicators={
                    'rsi': df['rsi'].iloc[-1] if not df['rsi'].isna().iloc[-1] else None,
                    'sma_20': df['sma_20'].iloc[-1] if not df['sma_20'].isna().iloc[-1] else None,
                    'bb_upper': df['bb_upper'].iloc[-1] if not df['bb_upper'].isna().iloc[-1] else None,
                    'bb_middle': df['bb_middle'].iloc[-1] if not df['bb_middle'].isna().iloc[-1] else None,
                    'bb_lower': df['bb_lower'].iloc[-1] if not df['bb_lower'].isna().iloc[-1] else None,
                },
                price_history=df
            )
            
            # Update cache
            self.price_data_cache[symbol] = stock_data
            self.last_update[symbol] = now
            
            return stock_data
        
        return safe_execute(
            _perform_analysis,
            error_handler=self.error_handler,
            operation=f"symbol analysis for {symbol}",
            on_error=lambda e: None
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
        current_price = stock_data.current_quote.ask_price
        
        # Skip if already have position or pending order
        if symbol in self.active_positions or symbol in self.pending_orders:
            return signals
        
        # Get technical indicators
        rsi = stock_data.technical_indicators.get('rsi')
        bb_lower = stock_data.technical_indicators.get('bb_lower')
        bb_upper = stock_data.technical_indicators.get('bb_upper')
        
        # Find nearest support and resistance levels
        nearest_support = self._find_nearest_support(stock_data, current_price)
        nearest_resistance = self._find_nearest_resistance(stock_data, current_price)
        
        # Buy signal conditions
        buy_conditions = []
        
        # Condition 1: Price near support level
        if nearest_support:
            distance_to_support = abs(current_price - nearest_support.price) / current_price
            if distance_to_support <= self.support_threshold:
                buy_conditions.append(f"Near support at ${nearest_support.price:.2f}")
        
        # Condition 2: RSI oversold
        if rsi and rsi <= self.rsi_oversold:
            buy_conditions.append(f"RSI oversold ({rsi:.1f})")
        
        # Condition 3: Price near lower Bollinger Band
        if bb_lower and current_price <= bb_lower * 1.01:  # Within 1% of lower band
            buy_conditions.append(f"Near lower Bollinger Band (${bb_lower:.2f})")
        
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
            error_handler=self.error_handler,
            operation=f"{signal_type} trade execution for {symbol}",
            on_error=_handle_trade_error
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
            max_position_value = buying_power * self.position_size
            quantity = int(max_position_value / quote.ask_price)
            
            if quantity <= 0:
                raise OrderExecutionError(f"Insufficient buying power for {symbol}")
            
            # Place market buy order
            order = self.alpaca_client.place_order(
                symbol=symbol,
                qty=quantity,
                side='buy',
                type='market',
                time_in_force='day'
            )
            
            if not order:
                raise OrderExecutionError(f"Failed to place buy order for {symbol}")
            
            # Create trade object
            trade = Trade(
                symbol=symbol,
                trade_type=TradeType.BUY,
                quantity=quantity,
                entry_price=quote.ask_price,
                timestamp=datetime.now(),
                order_id=order.id,
                status=TradeStatus.PENDING,
                strategy_reason=reason
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
            error_handler=self.error_handler,
            operation=f"buy order placement for {symbol}",
            on_error=lambda e: None
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
                type='market',
                time_in_force='day'
            )
            
            if not order:
                raise OrderExecutionError(f"Failed to place sell order for {symbol}")
            
            # Get current quote for exit price
            quote = self.alpaca_client.get_latest_quote(symbol)
            exit_price = quote.bid_price if quote else position_trade.entry_price
            
            # Create sell trade object
            trade = Trade(
                symbol=symbol,
                trade_type=TradeType.SELL,
                quantity=position_trade.quantity,
                entry_price=position_trade.entry_price,
                exit_price=exit_price,
                timestamp=datetime.now(),
                order_id=order.id,
                status=TradeStatus.PENDING,
                strategy_reason=reason
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
            error_handler=self.error_handler,
            operation=f"sell order placement for {symbol}",
            on_error=lambda e: None
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
        
        current_price = stock_data.current_quote.bid_price
        entry_price = position.entry_price
        
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
        rsi = stock_data.technical_indicators.get('rsi')
        if rsi and rsi >= self.rsi_overbought:
            return ("SELL", f"RSI overbought ({rsi:.1f})")
        
        # Upper Bollinger Band condition
        bb_upper = stock_data.technical_indicators.get('bb_upper')
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
            error_handler=self.error_handler,
            operation="position updates",
            on_error=lambda e: None
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
                    entry_price=fill_price,
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
                    pnl = (fill_price - position.entry_price) * quantity
                    
                    trade_logger.log_position_closed(
                        symbol, quantity, position.entry_price, fill_price, pnl
                    )
                    
                    del self.active_positions[symbol]
        
        safe_execute(
            _process_filled_order,
            error_handler=self.error_handler,
            operation=f"order fill processing for {symbol}",
            on_error=lambda e: None
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
                'entry_price': trade.entry_price,
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
            
            current_price = quote.bid_price
            return (current_price - trade.entry_price) * trade.quantity
        
        return safe_execute(
            _calculate_pnl,
            error_handler=self.error_handler,
            operation=f"P&L calculation for {symbol}",
            on_error=lambda e: 0.0
        )