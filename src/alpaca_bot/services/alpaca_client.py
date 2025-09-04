"""Alpaca API client wrapper with authentication and error handling.

This module provides a secure wrapper around the Alpaca API with comprehensive
error handling, connection management, and trading functionality.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

import alpaca_trade_api as tradeapi
import pandas as pd
from alpaca_trade_api.common import URL
from alpaca_trade_api.entity import Account, Asset, Order, Position
from alpaca_trade_api.rest import APIError, REST

from ..config.settings import settings
from ..utils.error_handler import (
    ErrorHandler,
    APIConnectionError,
    MarketDataError,
    OrderExecutionError,
    retry_on_error,
    circuit_breaker
)


class AlpacaClientError(Exception):
    """Custom exception for Alpaca client errors."""
    pass


class AlpacaClient:
    """Alpaca API client wrapper with enhanced error handling."""

    def __init__(self) -> None:
        """Initialize the Alpaca client with API credentials.
        
        Raises:
            AlpacaClientError: If API credentials are invalid or connection fails.
        """
        self.logger = logging.getLogger(__name__)
        self.error_handler = ErrorHandler(self.logger)
        
        try:
            api_key, secret_key, base_url = settings.get_alpaca_credentials()
            
            self.api = REST(
                key_id=api_key,
                secret_key=secret_key,
                base_url=URL(base_url),
                api_version='v2'
            )
            
            # Test connection
            self._test_connection()
            
            self.logger.info("Alpaca client initialized successfully")
            
        except Exception as e:
            self.error_handler.handle_api_error(e, "client_initialization")
            raise AlpacaClientError(f"Failed to initialize Alpaca client: {e}")
    
    def _test_connection(self) -> None:
        """Test the API connection.
        
        Raises:
            AlpacaClientError: If connection test fails.
        """
        try:
            account = self.api.get_account()
            self.logger.info(f"Connected to Alpaca API. Account status: {account.status}")
            
            if account.status != 'ACTIVE':
                raise AlpacaClientError(f"Account is not active. Status: {account.status}")
                
        except APIError as e:
            self.logger.error(f"API connection test failed: {e}")
            raise AlpacaClientError(f"API connection test failed: {e}")
    
    @retry_on_error(max_retries=3, delay=1.0)
    @circuit_breaker(failure_threshold=5, timeout=300)
    def get_account(self) -> Account:
        """Get account information.
        
        Returns:
            Account: Account information.
            
        Raises:
            AlpacaClientError: If API call fails.
        """
        try:
            if self.error_handler.is_circuit_breaker_open("get_account"):
                raise APIConnectionError("Circuit breaker is open for account operations")
            
            return self.api.get_account()
        except Exception as e:
            self.error_handler.handle_api_error(e, "get_account")
            raise
    
    def get_buying_power(self) -> float:
        """Get available buying power.
        
        Returns:
            float: Available buying power in USD.
            
        Raises:
            AlpacaClientError: If API call fails.
        """
        try:
            account = self.get_account()
            return float(account.buying_power)
        except Exception as e:
            self.logger.error(f"Failed to get buying power: {e}")
            raise AlpacaClientError(f"Failed to get buying power: {e}")
    
    @retry_on_error(max_retries=3, delay=1.0)
    @circuit_breaker(failure_threshold=5, timeout=300)
    def get_positions(self) -> List[Position]:
        """Get all current positions.
        
        Returns:
            List[Position]: List of current positions.
            
        Raises:
            AlpacaClientError: If API call fails.
        """
        try:
            if self.error_handler.is_circuit_breaker_open("get_positions"):
                raise APIConnectionError("Circuit breaker is open for position operations")
            
            return self.api.list_positions()
        except Exception as e:
            self.error_handler.handle_api_error(e, "get_positions")
            raise
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol.
        
        Args:
            symbol: Stock symbol to get position for.
            
        Returns:
            Optional[Position]: Position if exists, None otherwise.
            
        Raises:
            AlpacaClientError: If API call fails.
        """
        try:
            return self.api.get_position(symbol)
        except APIError as e:
            if "position does not exist" in str(e).lower():
                return None
            self.logger.error(f"Failed to get position for {symbol}: {e}")
            raise AlpacaClientError(f"Failed to get position for {symbol}: {e}")
    
    @retry_on_error(max_retries=3, delay=1.0)
    @circuit_breaker(failure_threshold=5, timeout=300)
    def get_orders(self, status: str = "all", limit: int = 50) -> List[Order]:
        """Get orders with optional status filter.
        
        Args:
            status: Order status filter ("open", "closed", "all").
            limit: Maximum number of orders to return.
            
        Returns:
            List[Order]: List of orders.
            
        Raises:
            AlpacaClientError: If API call fails.
        """
        try:
            if self.error_handler.is_circuit_breaker_open("get_orders"):
                raise APIConnectionError("Circuit breaker is open for order operations")
            
            return self.api.list_orders(status=status, limit=limit)
        except Exception as e:
            self.error_handler.handle_api_error(e, "get_orders")
            raise
    
    @retry_on_error(max_retries=2, delay=0.5)  # Fewer retries for orders to avoid duplicates
    def place_order(
        self,
        symbol: str,
        qty: Union[int, float],
        side: str,
        order_type: str = "market",
        time_in_force: str = "day",
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        trail_price: Optional[float] = None,
        trail_percent: Optional[float] = None
    ) -> Order:
        """Place a trading order.
        
        Args:
            symbol: Stock symbol.
            qty: Quantity to trade.
            side: "buy" or "sell".
            order_type: Order type ("market", "limit", "stop", etc.).
            time_in_force: Time in force ("day", "gtc", "ioc", "fok").
            limit_price: Limit price for limit orders.
            stop_price: Stop price for stop orders.
            trail_price: Trail amount for trailing stop orders.
            trail_percent: Trail percent for trailing stop orders.
            
        Returns:
            Order: The placed order.
            
        Raises:
            AlpacaClientError: If order placement fails.
        """
        order_details = {
            'symbol': symbol,
            'qty': qty,
            'side': side,
            'order_type': order_type
        }
        
        try:
            if self.error_handler.is_circuit_breaker_open(f"place_order_{symbol}"):
                raise APIConnectionError(f"Circuit breaker is open for {symbol} orders")
            
            # Validate order parameters
            if side not in ["buy", "sell"]:
                raise ValueError(f"Invalid side: {side}")
            
            if qty <= 0:
                raise ValueError(f"Invalid quantity: {qty}")
            
            # Build order request
            order_data = {
                "symbol": symbol,
                "qty": qty,
                "side": side,
                "type": order_type,
                "time_in_force": time_in_force
            }
            
            if limit_price is not None:
                order_data["limit_price"] = limit_price
            if stop_price is not None:
                order_data["stop_price"] = stop_price
            if trail_price is not None:
                order_data["trail_price"] = trail_price
            if trail_percent is not None:
                order_data["trail_percent"] = trail_percent
            
            # Place order
            order = self.api.submit_order(**order_data)
            
            self.logger.info(
                f"Order placed: {side} {qty} {symbol} at {order_type} "
                f"(Order ID: {order.id})"
            )
            
            return order
            
        except Exception as e:
            self.error_handler.handle_order_error(e, order_details)
            raise
    
    @retry_on_error(max_retries=2, delay=0.5)
    def cancel_order(self, order_id: str) -> None:
        """Cancel an existing order.
        
        Args:
            order_id: ID of the order to cancel.
            
        Raises:
            AlpacaClientError: If order cancellation fails.
        """
        try:
            if self.error_handler.is_circuit_breaker_open("cancel_order"):
                raise APIConnectionError("Circuit breaker is open for order cancellation")
            
            self.api.cancel_order(order_id)
            self.logger.info(f"Order {order_id} cancelled successfully")
        except Exception as e:
            self.error_handler.handle_order_error(e, {'order_id': order_id, 'action': 'cancel'})
            raise
    
    @retry_on_error(max_retries=3, delay=1.0)
    @circuit_breaker(failure_threshold=5, timeout=300)
    def get_bars(
        self,
        symbol: str,
        timeframe: str = "1Min",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """Get historical price bars for a symbol.
        
        Args:
            symbol: Stock symbol.
            timeframe: Bar timeframe ("1Min", "5Min", "15Min", "1Hour", "1Day").
            start: Start datetime for historical data.
            end: End datetime for historical data.
            limit: Maximum number of bars to return.
            
        Returns:
            pd.DataFrame: Historical price data.
            
        Raises:
            AlpacaClientError: If data retrieval fails.
        """
        try:
            if self.error_handler.is_circuit_breaker_open(f"get_bars_{symbol}"):
                raise APIConnectionError(f"Circuit breaker is open for {symbol} market data")
            
            # Set default time range if not provided
            if start is None:
                start = datetime.now() - timedelta(days=1)
            
            if end is None:
                end = datetime.now()
            
            # Ensure start and end are datetime objects, not strings
            if isinstance(start, str):
                start = datetime.fromisoformat(start.replace('Z', '+00:00'))
            if isinstance(end, str):
                end = datetime.fromisoformat(end.replace('Z', '+00:00'))
            
            # Get bars from Alpaca
            # Format datetime to RFC3339 without microseconds for Alpaca API
            start_str = start.strftime('%Y-%m-%dT%H:%M:%SZ')
            end_str = end.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # Use IEX feed for free accounts to avoid SIP data subscription issues
            # IEX provides delayed data (15-minute delay) which is acceptable for development
            bars = self.api.get_bars(
                symbol,
                timeframe,
                start=start_str,
                end=end_str,
                limit=limit,
                feed='iex'  # Use IEX feed instead of SIP to avoid subscription limitations
            )
            
            # Log that we're using delayed data
            self.logger.info(f"Retrieved {symbol} market data using IEX feed (15-minute delayed data)")
            
            # Convert to DataFrame
            data = []
            for bar in bars:
                # Handle different bar formats from IEX feed
                if hasattr(bar, 't'):
                    # Standard Alpaca bar format
                    data.append({
                        'timestamp': bar.t,
                        'open': bar.o,
                        'high': bar.h,
                        'low': bar.l,
                        'close': bar.c,
                        'volume': bar.v,
                    })
                elif hasattr(bar, 'timestamp'):
                    # Alternative bar format
                    data.append({
                        'timestamp': bar.timestamp,
                        'open': bar.open,
                        'high': bar.high,
                        'low': bar.low,
                        'close': bar.close,
                        'volume': bar.volume,
                    })
                else:
                    # If bar is a dict or other format
                    self.logger.warning(f"Unexpected bar format: {type(bar)}, {bar}")
                    if isinstance(bar, dict):
                        data.append({
                            'timestamp': bar.get('t') or bar.get('timestamp'),
                            'open': bar.get('o') or bar.get('open'),
                            'high': bar.get('h') or bar.get('high'),
                            'low': bar.get('l') or bar.get('low'),
                            'close': bar.get('c') or bar.get('close'),
                            'volume': bar.get('v') or bar.get('volume'),
                        })
                    else:
                        self.logger.error(f"Cannot process bar of type {type(bar)}: {bar}")
                        continue
            
            df = pd.DataFrame(data)
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            self.error_handler.handle_market_data_error(e, symbol)
            raise
    
    @retry_on_error(max_retries=3, delay=0.5)
    @circuit_breaker(failure_threshold=5, timeout=300)
    def get_latest_quote(self, symbol: str) -> Dict[str, float]:
        """Get the latest quote for a symbol.
        
        Args:
            symbol: Stock symbol.
            
        Returns:
            Dict[str, float]: Latest bid and ask prices.
            
        Raises:
            AlpacaClientError: If quote retrieval fails.
        """
        try:
            if self.error_handler.is_circuit_breaker_open(f"get_quote_{symbol}"):
                raise APIConnectionError(f"Circuit breaker is open for {symbol} quotes")
            
            # Use IEX feed for free accounts to avoid SIP data subscription issues
            quote = self.api.get_latest_quote(symbol, feed='iex')
            
            # Log that we're using delayed data
            self.logger.info(f"Retrieved {symbol} quote using IEX feed (15-minute delayed data)")
            
            # Handle IEX quote object structure
            # IEX quotes may have different attribute names or structure
            try:
                bid_price = getattr(quote, 'bid_price', getattr(quote, 'bid', 0.0))
                ask_price = getattr(quote, 'ask_price', getattr(quote, 'ask', 0.0))
                bid_size = getattr(quote, 'bid_size', 0)
                ask_size = getattr(quote, 'ask_size', 0)
            except AttributeError:
                # Fallback: use the last trade price as both bid and ask
                trade = self.api.get_latest_trade(symbol, feed='iex')
                bid_price = ask_price = float(trade.price)
                bid_size = ask_size = 0
                self.logger.warning(f"Quote attributes not available for {symbol}, using trade price")
            
            return {
                'bid': float(bid_price),
                'ask': float(ask_price),
                'bid_size': int(bid_size),
                'ask_size': int(ask_size),
            }
        except Exception as e:
            self.error_handler.handle_market_data_error(e, symbol)
            raise
    
    @retry_on_error(max_retries=3, delay=0.5)
    @circuit_breaker(failure_threshold=5, timeout=300)
    def get_latest_trade(self, symbol: str) -> Dict[str, Union[float, int]]:
        """Get the latest trade for a symbol.
        
        Args:
            symbol: Stock symbol.
            
        Returns:
            Dict[str, Union[float, int]]: Latest trade data.
            
        Raises:
            AlpacaClientError: If trade retrieval fails.
        """
        try:
            if self.error_handler.is_circuit_breaker_open(f"get_trade_{symbol}"):
                raise APIConnectionError(f"Circuit breaker is open for {symbol} trade data")
            
            # Use IEX feed for free accounts to avoid SIP data subscription issues
            trade = self.api.get_latest_trade(symbol, feed='iex')
            
            # Log that we're using delayed data
            self.logger.info(f"Retrieved {symbol} trade data using IEX feed (15-minute delayed data)")
            
            return {
                'price': float(trade.price),
                'size': int(trade.size),
                'timestamp': trade.timestamp,
            }
        except Exception as e:
            self.error_handler.handle_market_data_error(e, symbol)
            raise
    
    @retry_on_error(max_retries=3, delay=1.0)
    @circuit_breaker(failure_threshold=5, timeout=300)
    def is_market_open(self) -> bool:
        """Check if the market is currently open.
        
        Returns:
            bool: True if market is open, False otherwise.
            
        Raises:
            AlpacaClientError: If market status check fails.
        """
        try:
            if self.error_handler.is_circuit_breaker_open("market_status"):
                raise APIConnectionError("Circuit breaker is open for market status checks")
            
            clock = self.api.get_clock()
            return clock.is_open
        except Exception as e:
            self.error_handler.handle_api_error(e, "market_status")
            raise
    
    @retry_on_error(max_retries=3, delay=1.0)
    @circuit_breaker(failure_threshold=5, timeout=300)
    def get_tradable_assets(self) -> List[Asset]:
        """Get list of tradable assets.
        
        Returns:
            List[Asset]: List of tradable assets.
            
        Raises:
            AlpacaClientError: If asset retrieval fails.
        """
        try:
            if self.error_handler.is_circuit_breaker_open("get_assets"):
                raise APIConnectionError("Circuit breaker is open for asset operations")
            
            return self.api.list_assets(status='active', asset_class='us_equity')
        except Exception as e:
            self.error_handler.handle_api_error(e, "get_assets")
            raise