"""Simple trading strategy implementation for automated trading.

This module implements a simplified strategy that:
1. Uses basic technical indicators (RSI, SMA)
2. Takes positions based on simple conditions
3. Focuses on actually executing trades rather than complex filtering
4. Has three modes: SAFE, SMART, AGGRESSIVE
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum

import pandas as pd
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


class SimpleTradingMode(Enum):
    """Simplified trading mode enumeration."""
    SAFE = "safe"
    SMART = "smart"
    AGGRESSIVE = "aggressive"
    
    @classmethod
    def get_mode_params(cls, mode: 'SimpleTradingMode') -> Dict[str, float]:
        """Get trading parameters for each mode.
        
        Args:
            mode: Trading mode.
            
        Returns:
            Dictionary with mode-specific parameters.
        """
        params = {
            cls.SAFE: {
                'position_size_pct': 0.02,  # 2% of portfolio per trade
                'stop_loss_pct': 0.02,      # 2% stop loss
                'take_profit_pct': 0.04,    # 4% take profit
                'max_daily_trades': 5,
                'rsi_oversold': 30,
                'rsi_overbought': 70,
            },
            cls.SMART: {
                'position_size_pct': 0.03,  # 3% of portfolio per trade
                'stop_loss_pct': 0.015,     # 1.5% stop loss
                'take_profit_pct': 0.03,    # 3% take profit
                'max_daily_trades': 8,
                'rsi_oversold': 35,
                'rsi_overbought': 65,
            },
            cls.AGGRESSIVE: {
                'position_size_pct': 0.05,  # 5% of portfolio per trade
                'stop_loss_pct': 0.01,      # 1% stop loss
                'take_profit_pct': 0.02,    # 2% take profit
                'max_daily_trades': 15,
                'rsi_oversold': 40,
                'rsi_overbought': 60,
            }
        }
        
        return params[mode]


class SimpleStrategy:
    """Simple trading strategy implementation."""
    
    def __init__(self, alpaca_client: AlpacaClient, settings=None):
        """Initialize the simple strategy.
        
        Args:
            alpaca_client: Alpaca API client.
            settings: Strategy settings.
        """
        self.alpaca_client = alpaca_client
        self.settings = settings or globals()['settings']
        self.logger = logging.getLogger(__name__)
        
        # Set trading mode
        trading_mode_str = getattr(self.settings, 'trading_mode', 'smart')
        try:
            if trading_mode_str == 'conservative':
                self.trading_mode = SimpleTradingMode.SMART
            elif trading_mode_str == 'ultra_safe':
                self.trading_mode = SimpleTradingMode.SAFE
            elif trading_mode_str == 'aggressive':
                self.trading_mode = SimpleTradingMode.AGGRESSIVE
            else:
                self.trading_mode = SimpleTradingMode(trading_mode_str)
        except ValueError:
            self.logger.warning(f"Invalid trading mode '{trading_mode_str}', defaulting to smart")
            self.trading_mode = SimpleTradingMode.SMART
        
        # Get mode parameters
        self.mode_params = SimpleTradingMode.get_mode_params(self.trading_mode)
        
        # Strategy parameters
        self.position_size_pct = self.mode_params['position_size_pct']
        self.stop_loss_pct = self.mode_params['stop_loss_pct']
        self.take_profit_pct = self.mode_params['take_profit_pct']
        self.max_daily_trades = self.mode_params['max_daily_trades']
        self.rsi_oversold = self.mode_params['rsi_oversold']
        self.rsi_overbought = self.mode_params['rsi_overbought']
        
        # Daily tracking
        self.daily_trades_count = 0
        self.last_reset_date = datetime.now().date()
        
        # Active positions and orders
        self.active_positions: Dict[str, Trade] = {}
        self.pending_orders: Dict[str, str] = {}
        
        # Callbacks for GUI updates
        self.account_update_callback = None
        self.order_update_callback = None
        
        self.logger.info(f"Simple strategy initialized in {self.trading_mode.value.upper()} mode")
        self.logger.info(f"Parameters: Position size: {self.position_size_pct*100:.1f}%, "
                        f"Stop loss: {self.stop_loss_pct*100:.1f}%, "
                        f"Take profit: {self.take_profit_pct*100:.1f}%, "
                        f"Max daily trades: {self.max_daily_trades}")
    
    def set_callbacks(self, account_callback=None, order_callback=None):
        """Set callback functions for GUI updates."""
        self.account_update_callback = account_callback
        self.order_update_callback = order_callback
    
    def _reset_daily_counters_if_needed(self) -> None:
        """Reset daily counters if it's a new day."""
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            self.daily_trades_count = 0
            self.last_reset_date = current_date
            self.logger.info("Daily counters reset for new trading day")
    
    def analyze_symbol(self, symbol: str) -> Optional[StockData]:
        """Analyze a symbol and return stock data with technical indicators.
        
        Args:
            symbol: Stock symbol to analyze.
            
        Returns:
            StockData object with technical indicators, or None if error.
        """
        try:
            # Get current quote
            quote = self.alpaca_client.get_latest_quote(symbol)
            if not quote:
                self.logger.warning(f"No quote data for {symbol}")
                return None
            
            # Get recent bars for technical analysis
            df = self.alpaca_client.get_bars(symbol, timeframe='1Min', limit=50)
            if df is None or len(df) < 20:
                self.logger.warning(f"Insufficient bar data for {symbol}")
                return None
            
            # Calculate technical indicators
            df['rsi'] = calculate_rsi(df['close'])
            df['sma_20'] = calculate_sma(df['close'], 20)
            df['sma_50'] = calculate_sma(df['close'], 50)
            
            # Get latest values
            latest = df.iloc[-1]
            current_price = float(quote['bid'])
            
            # Create technical indicators object
            technical_indicators = TechnicalIndicators(
                symbol=symbol,
                timestamp=datetime.now(),
                rsi=float(latest['rsi']) if pd.notna(latest['rsi']) else 50.0,
                sma_20=float(latest['sma_20']) if pd.notna(latest['sma_20']) else current_price,
                sma_50=float(latest['sma_50']) if pd.notna(latest['sma_50']) else current_price,
                bollinger_upper=current_price * 1.02,  # Simple approximation
                bollinger_lower=current_price * 0.98,
                bollinger_middle=current_price,
                macd=0.0,
                macd_signal=0.0,
                macd_histogram=0.0
            )
            
            # Create stock data object
            stock_data = StockData(
                symbol=symbol,
                company_name=symbol,  # Use symbol as company name for now
                current_quote=quote,
                technical_indicators=technical_indicators
            )
            
            return stock_data
            
        except Exception as e:
            self.logger.error(f"Error analyzing {symbol}: {e}")
            return None
    
    def generate_signals(self, stock_data: StockData) -> List[Tuple[str, str]]:
        """Generate trading signals based on simple conditions.
        
        Args:
            stock_data: Stock data with technical indicators.
            
        Returns:
            List of (signal_type, reason) tuples.
        """
        signals = []
        symbol = stock_data.symbol
        
        if not stock_data.technical_indicators or not stock_data.current_quote:
            return signals
        
        current_price = float(stock_data.current_quote['bid'])
        rsi = stock_data.technical_indicators.rsi
        sma_20 = stock_data.technical_indicators.sma_20
        sma_50 = stock_data.technical_indicators.sma_50
        
        # Check if we already have a position
        has_position = symbol in self.active_positions
        
        # Reset daily counters if needed
        self._reset_daily_counters_if_needed()
        
        # Check daily trade limit
        if self.daily_trades_count >= self.max_daily_trades:
            self.logger.debug(f"{symbol}: Daily trade limit reached ({self.daily_trades_count}/{self.max_daily_trades})")
            return signals
        
        # BUY SIGNALS (only if no position)
        if not has_position:
            buy_reasons = []
            
            # RSI oversold condition
            if rsi < self.rsi_oversold:
                buy_reasons.append(f"RSI oversold ({rsi:.1f})")
            
            # Price below short-term moving average (potential bounce)
            if current_price < sma_20:
                buy_reasons.append(f"Price below SMA20 (${current_price:.2f} < ${sma_20:.2f})")
            
            # Uptrend condition (SMA20 > SMA50)
            if sma_20 > sma_50:
                buy_reasons.append(f"Uptrend (SMA20 > SMA50)")
            
            # Simple buy condition: need at least 1 reason (much more lenient)
            if len(buy_reasons) >= 1:
                reason = "; ".join(buy_reasons)
                signals.append(("BUY", reason))
                self.logger.info(f"{symbol}: BUY signal generated - {reason}")
        
        # SELL SIGNALS (only if we have a position)
        elif has_position:
            sell_reasons = []
            position_trade = self.active_positions[symbol]
            entry_price = position_trade.price
            
            # Calculate profit/loss percentage
            pnl_pct = (current_price - entry_price) / entry_price
            
            # Take profit condition
            if pnl_pct >= self.take_profit_pct:
                sell_reasons.append(f"Take profit ({pnl_pct*100:.1f}% >= {self.take_profit_pct*100:.1f}%)")
            
            # Stop loss condition
            elif pnl_pct <= -self.stop_loss_pct:
                sell_reasons.append(f"Stop loss ({pnl_pct*100:.1f}% <= -{self.stop_loss_pct*100:.1f}%)")
            
            # RSI overbought condition
            elif rsi > self.rsi_overbought:
                sell_reasons.append(f"RSI overbought ({rsi:.1f})")
            
            # Price above short-term moving average by significant margin
            elif current_price > sma_20 * 1.02:  # 2% above SMA20
                sell_reasons.append(f"Price well above SMA20 (${current_price:.2f} > ${sma_20*1.02:.2f})")
            
            # Sell if any condition is met
            if sell_reasons:
                reason = "; ".join(sell_reasons)
                signals.append(("SELL", reason))
                self.logger.info(f"{symbol}: SELL signal generated - {reason}")
        
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
        """Execute a buy order.
        
        Args:
            symbol: Stock symbol.
            reason: Reason for the trade.
            
        Returns:
            Trade object if successful, None otherwise.
        """
        try:
            # Get account information
            account = self.alpaca_client.get_account()
            if not account:
                raise OrderExecutionError("Could not get account information")
            
            # Calculate position size
            portfolio_value = float(account.portfolio_value)
            position_value = portfolio_value * self.position_size_pct
            
            # Ensure minimum position size
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
            
            # Increment daily trade count
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
        """Execute a sell order.
        
        Args:
            symbol: Stock symbol.
            reason: Reason for the trade.
            
        Returns:
            Trade object if successful, None otherwise.
        """
        try:
            # Check if we have a position
            if symbol not in self.active_positions:
                self.logger.warning(f"No active position for {symbol}")
                return None
            
            position_trade = self.active_positions[symbol]
            quantity = position_trade.quantity
            
            # Get current quote
            quote = self.alpaca_client.get_latest_quote(symbol)
            if not quote:
                raise OrderExecutionError(f"Could not get quote for {symbol}")
            
            current_price = float(quote['bid'])
            
            # Place market sell order
            order = self.alpaca_client.place_order(
                symbol=symbol,
                qty=quantity,
                side='sell',
                order_type='market',
                time_in_force='day'
            )
            
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
            
            # Remove from active positions (will be re-added if partial fill)
            del self.active_positions[symbol]
            
            # Increment daily trade count
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
    
    def update_positions(self) -> None:
        """Update position status and handle filled orders."""
        try:
            # Get current positions from Alpaca
            positions = self.alpaca_client.get_positions()
            alpaca_positions = {pos.symbol: pos for pos in positions}
            
            # Update active positions based on Alpaca positions
            symbols_to_remove = []
            for symbol in self.active_positions:
                if symbol not in alpaca_positions:
                    # Position was closed
                    symbols_to_remove.append(symbol)
                else:
                    # Update quantity if different
                    alpaca_pos = alpaca_positions[symbol]
                    current_qty = float(alpaca_pos.qty)
                    if current_qty != self.active_positions[symbol].quantity:
                        self.active_positions[symbol].quantity = current_qty
            
            # Remove closed positions
            for symbol in symbols_to_remove:
                del self.active_positions[symbol]
                self.logger.info(f"Position closed for {symbol}")
            
            # Check for new positions not in our tracking
            for symbol, alpaca_pos in alpaca_positions.items():
                if symbol not in self.active_positions:
                    # New position (possibly from manual trade)
                    trade = Trade(
                        symbol=symbol,
                        trade_type=TradeType.BUY,
                        quantity=float(alpaca_pos.qty),
                        price=float(alpaca_pos.avg_entry_price),
                        timestamp=datetime.now(),
                        order_id="manual",
                        status=TradeStatus.FILLED,
                        notes="Manual or external trade"
                    )
                    self.active_positions[symbol] = trade
                    self.logger.info(f"New position detected for {symbol}: {trade.quantity:.4f} shares")
            
        except Exception as e:
            self.logger.error(f"Error updating positions: {e}")
    
    def get_strategy_status(self) -> Dict:
        """Get current strategy status.
        
        Returns:
            Dictionary with strategy status information.
        """
        return {
            'trading_mode': self.trading_mode.value,
            'active_positions': len(self.active_positions),
            'pending_orders': len(self.pending_orders),
            'daily_trades': self.daily_trades_count,
            'max_daily_trades': self.max_daily_trades,
            'positions': {symbol: {
                'quantity': trade.quantity,
                'entry_price': trade.price,
                'notes': trade.notes
            } for symbol, trade in self.active_positions.items()},
            'strategy_parameters': {
                'position_size_pct': self.position_size_pct,
                'stop_loss_pct': self.stop_loss_pct,
                'take_profit_pct': self.take_profit_pct,
                'rsi_oversold': self.rsi_oversold,
                'rsi_overbought': self.rsi_overbought
            }
        }