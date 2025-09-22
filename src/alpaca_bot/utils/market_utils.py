"""Market utilities for the Alpaca trading bot.

This module provides utilities for:
- Market hours detection
- Trading session validation
- Market status checking
"""

import logging
from datetime import datetime, time, timedelta
from typing import Tuple, Optional
import pytz
from ..config.settings import settings


class MarketHours:
    """Market hours utility class."""
    
    def __init__(self):
        """Initialize market hours utility."""
        self.logger = logging.getLogger(__name__)
        self.eastern_tz = pytz.timezone('US/Eastern')
        
    def is_market_open(self, weekend_trading_enabled: bool = False) -> bool:
        """Check if the market is currently open.
        
        Args:
            weekend_trading_enabled (bool): Whether weekend trading is enabled.
        
        Returns:
            bool: True if market is open, False otherwise.
        """
        now_et = datetime.now(self.eastern_tz)
        
        # Check if it's a weekday (Monday=0, Sunday=6)
        if now_et.weekday() >= 5 and not weekend_trading_enabled:  # Saturday or Sunday
            return False
            
        # Get current time
        current_time = now_et.time()
        
        # Get trading hours from settings
        start_hour = getattr(settings, 'trading_start_hour', 9)
        start_minute = getattr(settings, 'trading_start_minute', 30)
        end_hour = getattr(settings, 'trading_end_hour', 16)
        end_minute = getattr(settings, 'trading_end_minute', 0)
        
        # Create time objects for market open/close
        market_open = time(start_hour, start_minute)
        market_close = time(end_hour, end_minute)
        
        # For weekend trading, allow 24/7 trading on weekends
        if weekend_trading_enabled and now_et.weekday() >= 5:
            return True
        
        # Check if current time is within trading hours
        return market_open <= current_time <= market_close
    
    def get_market_status(self, weekend_trading_enabled: bool = False) -> str:
        """Get current market status message.
        
        Args:
            weekend_trading_enabled (bool): Whether weekend trading is enabled.
        
        Returns:
            str: Market status message.
        """
        now_et = datetime.now(self.eastern_tz)
        current_weekday = now_et.weekday()
        
        # Check if it's weekend
        if current_weekday >= 5:
            if weekend_trading_enabled:
                return "Weekend trading is enabled - Market is open"
            else:
                return "Market is closed (Weekend). Opens Monday at 9:30 AM ET."
        
        # Check if market is open
        if self.is_market_open(weekend_trading_enabled):
            return "Market is open"
        
        # Market is closed during weekday
        market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
        
        if now_et < market_open:
            return f"Market opens at 9:30 AM ET (in {self.get_time_until_open()})"
        else:
            return "Market is closed. Opens tomorrow at 9:30 AM ET."
    
    def get_time_until_open(self) -> Optional[str]:
        """Get time until market opens.
        
        Returns:
            Optional[str]: Time until market opens, or None if market is open.
        """
        is_open = self.is_market_open()
        if is_open:
            return None
            
        now_et = datetime.now(self.eastern_tz)
        
        # Get trading hours from settings
        start_hour = getattr(settings, 'trading_start_hour', 9)
        start_minute = getattr(settings, 'trading_start_minute', 30)
        
        # Calculate next market open
        next_open = now_et.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
        
        # If market opening time has passed today, move to next business day
        if now_et.time() > time(start_hour, start_minute) or now_et.weekday() >= 5:
            # Move to next business day
            days_to_add = 1
            if now_et.weekday() == 4:  # Friday
                days_to_add = 3  # Skip to Monday
            elif now_et.weekday() == 5:  # Saturday
                days_to_add = 2  # Skip to Monday
            
            next_open = next_open + timedelta(days=days_to_add)
        
        time_diff = next_open - now_et
        hours, remainder = divmod(time_diff.total_seconds(), 3600)
        minutes, _ = divmod(remainder, 60)
        
        if hours >= 24:
            days = int(hours // 24)
            hours = int(hours % 24)
            return f"{days}d {hours}h {int(minutes)}m"
        else:
            return f"{int(hours)}h {int(minutes)}m"
    
    def get_current_et_time(self) -> datetime:
        """Get current Eastern Time as datetime object.
        
        Returns:
            datetime: Current time in ET timezone.
        """
        return datetime.now(self.eastern_tz)


# Global market hours instance
market_hours = MarketHours()